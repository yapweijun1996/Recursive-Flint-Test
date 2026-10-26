"""Compare two models through Pi using the existing fixed benchmark cases."""

import argparse
import ast
import datetime
import hashlib
import json
import pathlib
import shutil
import statistics
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repeats', type=int, default=3)
parser.add_argument('--output', type=pathlib.Path, required=True)
args = parser.parse_args()
if not 1 <= args.repeats <= 10:
    parser.error('--repeats must be between 1 and 10')

root = pathlib.Path(__file__).resolve().parents[2]
source = pathlib.Path(__file__).with_name('run.py')
tree = ast.parse(source.read_text(encoding='utf-8-sig'))
cases = next(ast.literal_eval(node.value) for node in tree.body
             if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == 'cases'
                     for target in node.targets))
models = ['openai/gpt-6-luna', 'recursive/flint-v1.0:free']
pi = shutil.which('pi.cmd')
if not pi:
    raise SystemExit('pi.cmd is not available')
version = subprocess.check_output([pi, '--version'], text=True).strip()
records = []
metadata = {
    'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'pi_version': version,
    'provider': 'openrouter',
    'models': models,
    'requested_thinking': 'high',
    'repeats_per_case': args.repeats,
    'case_source': str(source.relative_to(root)),
    'cases_sha256': hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest(),
    'read_fixture_sha256': hashlib.sha256((root / '.gitattributes').read_bytes()).hexdigest(),
    'limitations': [
        'Small fixed custom benchmark, not SWE-bench or a general coding ranking.',
        'Nine answer tasks and one real read-tool task; no patches generated or executed.',
        'Independent nonpersistent Pi sessions; extensions and built-in MCP disabled.',
        'Same provider platform, not necessarily the same upstream infrastructure.',
        'Requested high for both; Flint decides when to reason and has no effort control.',
        'Existing Pi settings and project context retained; provider sampling defaults retained.',
        'Wall time includes startup, network, inference and all tool turns.',
        'Token counters and costs are reported by Pi; counters are not cross-tokenizer equivalents.',
        'No automatic retries; unsuccessful responses count as failures.',
    ],
}
args.output.parent.mkdir(parents=True, exist_ok=True)


def save():
    groups = {}
    for model in models:
        rows = [row for row in records if row['requested_model'] == model]
        if not rows:
            continue
        groups[model] = {
            'runs': len(rows),
            'passed': sum(row['passed'] for row in rows),
            'answer_tasks_passed': sum(row['passed'] for row in rows if not row['requires_read']),
            'read_tasks_passed': sum(row['passed'] for row in rows if row['requires_read']),
            'total_wall_seconds': round(sum(row['wall_seconds'] for row in rows), 3),
            'median_wall_seconds': round(statistics.median(row['wall_seconds'] for row in rows), 3),
            'usage': {key: sum(row.get('usage', {}).get(key, 0) for row in rows)
                      for key in ['input', 'output', 'cacheRead', 'cacheWrite', 'reasoning', 'totalTokens']},
            'reported_cost_usd': sum(row.get('reported_cost_usd', 0) for row in rows),
        }
    document = {'metadata': metadata, 'summary': groups, 'results': records}
    args.output.write_text(json.dumps(document, indent=2), encoding='utf-8')
    return groups


for trial in range(1, args.repeats + 1):
    for index, (name, prompt, expected, requires_read) in enumerate(cases):
        order = models if (index + trial) % 2 else list(reversed(models))
        for model in order:
            command = [pi, '--provider', 'openrouter', '--model', model,
                       '--no-session', '--no-extensions', '--no-mcp',
                       '--thinking', 'high', '--mode', 'json']
            command += ['--tools', 'read'] if requires_read else ['--no-tools']
            command += ['Reply in English. Return only the requested JSON object in your final answer, without markdown. ' + prompt]
            row = {'trial': trial, 'name': name, 'requested_model': model,
                   'prompt': prompt, 'expected': expected,
                   'requires_read': requires_read, 'passed': False}
            start = time.perf_counter()
            try:
                process = subprocess.run(command, cwd=root, capture_output=True,
                                         text=True, encoding='utf-8', errors='replace', timeout=90)
                events = []
                for line in process.stdout.splitlines():
                    try:
                        events.append(json.loads(line))
                    except ValueError:
                        pass
                messages = [event['message'] for event in events
                            if event.get('type') == 'message_end'
                            and event.get('message', {}).get('role') == 'assistant']
                final = messages[-1] if messages else {}
                calls = [part for message in messages for part in message.get('content', [])
                         if part.get('type') == 'toolCall']
                ends = [event for event in events if event.get('type') == 'tool_execution_end']
                answer = ''.join(part.get('text', '') for part in final.get('content', [])
                                 if part.get('type') == 'text')
                row.update(exit_code=process.returncode, model=final.get('model'),
                           provider=final.get('provider'), stop_reason=final.get('stopReason'),
                           answer=answer,
                           tool_calls=[{'name':call.get('name'), 'arguments':call.get('arguments')}
                                       for call in calls],
                           tool_results=[{'name':event.get('toolName'), 'is_error':event.get('isError'),
                                          'result':event.get('result')} for event in ends])
                try:
                    row['parsed'] = json.loads(answer)
                except ValueError:
                    row['error'] = 'Final answer was not strict JSON'
                row['passed'] = (process.returncode == 0 and final.get('stopReason') == 'stop'
                                 and final.get('model') == model and final.get('provider') == 'openrouter'
                                 and row.get('parsed') == expected)
                if requires_read:
                    row['passed'] = (row['passed'] and len(calls) == 1
                                     and calls[0].get('name') == 'read'
                                     and isinstance(calls[0].get('arguments', {}).get('path'), str)
                                     and (root / calls[0]['arguments']['path']).resolve() == (root / '.gitattributes').resolve()
                                     and len(ends) == 1 and not ends[0].get('isError'))
                else:
                    row['passed'] = row['passed'] and not calls
                row['usage'] = {key:sum(message.get('usage', {}).get(key, 0) for message in messages)
                                for key in ['input', 'output', 'cacheRead', 'cacheWrite', 'reasoning', 'totalTokens']}
                row['reported_cost_usd'] = sum(message.get('usage', {}).get('cost', {}).get('total', 0)
                                               for message in messages)
                row['thinking_characters'] = sum(len(part.get('thinking', '')) for message in messages
                                                 for part in message.get('content', [])
                                                 if part.get('type') == 'thinking')
                if final.get('errorMessage'):
                    row['error'] = final['errorMessage']
                if not messages:
                    row['error'] = 'No assistant message returned'
            except subprocess.TimeoutExpired:
                row['error'] = '90 second timeout'
            row['wall_seconds'] = round(time.perf_counter() - start, 3)
            records.append(row)
            save()
            print(json.dumps({key:row.get(key) for key in
                              ['trial', 'name', 'requested_model', 'passed', 'wall_seconds', 'error']}), flush=True)

metadata['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
print('SUMMARY ' + json.dumps(save()), flush=True)
print('REPORT ' + str(args.output.resolve()), flush=True)
