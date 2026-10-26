"""Run isolated repair, randomized read-tool, and Luna effort benchmarks through Pi."""

import argparse
import datetime
import hashlib
import json
import pathlib
import secrets
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

from suite import TASKS

HERE = pathlib.Path(__file__).resolve().parent
PROFILES = [
    {'name': 'luna-high', 'model': 'openai/gpt-6-luna', 'thinking': 'high'},
    {'name': 'luna-medium', 'model': 'openai/gpt-6-luna', 'thinking': 'medium'},
    {'name': 'flint', 'model': 'recursive/flint-v1.0:free', 'thinking': 'high'},
]


def verify(task, candidate):
    start = time.perf_counter()
    try:
        process = subprocess.run([sys.executable, '-I', str(HERE / 'verify.py'), task, str(candidate)],
                                 capture_output=True, text=True, timeout=5)
        result = json.loads(process.stdout)
    except subprocess.TimeoutExpired:
        result = {'passed': False, 'error': 'Verification exceeded five seconds'}
    except ValueError:
        result = {'passed': False, 'error': 'Verification produced no valid result'}
    result['seconds'] = round(time.perf_counter() - start, 3)
    return result


def prepare():
    fixtures = HERE / 'fixtures'
    fixtures.mkdir(exist_ok=True)
    baseline = {}
    for task, specification in TASKS.items():
        buggy = fixtures / (task + '.py')
        reference = fixtures / (task + '.reference.py')
        buggy.write_text(specification['buggy'], encoding='utf-8')
        reference.write_text(specification['reference'], encoding='utf-8')
        baseline[task] = {'buggy': verify(task, buggy), 'reference': verify(task, reference)}
        assert not baseline[task]['buggy']['passed'], 'Defect did not reproduce: ' + task
        assert baseline[task]['reference']['passed'], 'Reference failed verification: ' + task
    (HERE / 'baseline.json').write_text(json.dumps(baseline, indent=2), encoding='utf-8')
    return baseline


def call_pi(profile, prompt, cwd, tools):
    command = [shutil.which('pi.cmd'), '--provider', 'openrouter', '--model', profile['model'],
               '--no-session', '--no-extensions', '--no-mcp', '--no-context-files', '--no-skills',
               '--thinking', profile['thinking'], '--mode', 'json']
    command += ['--tools', 'read'] if tools else ['--no-tools']
    command += [prompt]
    start = time.perf_counter()
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(command, cwd=cwd, stdout=stdout, stderr=stderr)
        try:
            process.wait(timeout=90)
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
            process.wait(timeout=10)
            return {'passed': False, 'error': 'Model call exceeded 90 seconds',
                    'wall_seconds': round(time.perf_counter() - start, 3)}
        stdout.seek(0)
        events = []
        for line in stdout.read().decode('utf-8', errors='replace').splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    messages = [event['message'] for event in events if event.get('type') == 'message_end'
                and event.get('message', {}).get('role') == 'assistant']
    final = messages[-1] if messages else {}
    calls = [part for message in messages for part in message.get('content', []) if part.get('type') == 'toolCall']
    ends = [event for event in events if event.get('type') == 'tool_execution_end']
    answer = ''.join(part.get('text', '') for part in final.get('content', []) if part.get('type') == 'text')
    row = {'exit_code': process.returncode, 'model': final.get('model'), 'provider': final.get('provider'),
           'stop_reason': final.get('stopReason'), 'answer': answer,
           'tool_calls': [{'name': call.get('name'), 'arguments': call.get('arguments')} for call in calls],
           'tool_results': [{'name': event.get('toolName'), 'is_error': event.get('isError'), 'result': event.get('result')} for event in ends],
           'wall_seconds': round(time.perf_counter() - start, 3),
           'usage': {key:sum(message.get('usage', {}).get(key, 0) for message in messages)
                     for key in ['input', 'output', 'cacheRead', 'cacheWrite', 'reasoning', 'totalTokens']},
           'reported_cost_usd': sum(message.get('usage', {}).get('cost', {}).get('total', 0) for message in messages),
           'thinking_characters': sum(len(part.get('thinking', '')) for message in messages for part in message.get('content', []) if part.get('type') == 'thinking')}
    try:
        row['parsed'] = json.loads(answer)
    except ValueError:
        row['error'] = 'Final answer was not strict JSON'
    if final.get('errorMessage'):
        row['error'] = final['errorMessage']
    row['response_ok'] = (process.returncode == 0 and final.get('stopReason') == 'stop'
                          and final.get('model') == profile['model'] and final.get('provider') == 'openrouter')
    return row


def valid_reads(row, cwd, target, exactly_once):
    calls, ends = row.get('tool_calls', []), row.get('tool_results', [])
    if not calls or (exactly_once and len(calls) != 1) or len(calls) != len(ends):
        return False
    for call, end in zip(calls, ends):
        path = call.get('arguments', {}).get('path')
        if (call.get('name') != 'read' or end.get('name') != 'read' or end.get('is_error')
                or not isinstance(path, str) or (cwd / path).resolve() != target.resolve()):
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--tool-trials', type=int, default=10)
    parser.add_argument('--output', type=pathlib.Path, default=HERE / 'results.json')
    args = parser.parse_args()
    if not 1 <= args.tool_trials <= 30:
        parser.error('--tool-trials must be between 1 and 30')
    baseline = prepare()
    if args.prepare_only:
        print(json.dumps({task: {kind: {key: result.get(key) for key in ['passed', 'checks', 'passed_checks']}
                                for kind, result in variants.items()}
                          for task, variants in baseline.items()}, indent=2))
        return
    records = []
    metadata = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'pi_version': subprocess.check_output([shutil.which('pi.cmd'), '--version'], text=True).strip(),
                'provider': 'openrouter', 'profiles': PROFILES, 'tool_trials_per_profile': args.tool_trials,
                'expected_calls': 9 + args.tool_trials * 3 + 20,
                'context_policy': 'No context files, skills, extensions, MCP, or persistent sessions.',
                'reasoning_policy': 'Luna uses requested high or medium; Flint reasons autonomously.',
                'tasks_sha256': hashlib.sha256(json.dumps(TASKS, sort_keys=True).encode()).hexdigest(),
                'verification_policy': 'Trusted Python behavior checks in a separate five-second process with AST/import checks and restricted builtins; no model shell execution.',
                'baseline_sha256': hashlib.sha256(json.dumps(baseline, sort_keys=True).encode()).hexdigest()}

    def save(row):
        records.append(row)
        args.output.write_text(json.dumps({'metadata': metadata, 'baseline': baseline, 'results': records}, indent=2), encoding='utf-8')
        print(json.dumps({key:row.get(key) for key in ['suite', 'task', 'trial', 'profile', 'passed', 'wall_seconds', 'error']}) + f' ({len(records)}/{metadata["expected_calls"]})', flush=True)

    # A: Each model investigates a real buggy module, returns a replacement, and is graded by executable checks.
    for index, (task, specification) in enumerate(TASKS.items()):
        for profile in PROFILES[index:] + PROFILES[:index]:
            cwd = HERE / 'fixtures'
            target = cwd / (task + '.py')
            prompt = (f'Read {target.name} using the read tool before proposing a repair. Read only that file. '
                      'Do not use any other tools. Return the complete corrected Python module in exactly one JSON object with a code string: {"code":"..."}. '
                      'No markdown. The evaluator applies your replacement and runs independent regression tests. '
                      'Use only builtins or collections, math, typing; no IO or dynamic execution. Required contract: ' + specification['contract'])
            row = call_pi(profile, prompt, cwd, True)
            row.update(suite='A', task=task, trial=1, profile=profile['name'], prompt=prompt)
            read_ok = valid_reads(row, cwd, target, False)
            row['read_ok'] = read_ok
            code = row.get('parsed', {}).get('code') if isinstance(row.get('parsed'), dict) else None
            if isinstance(code, str):
                candidate = HERE / 'repairs' / profile['name'] / target.name
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_text(code, encoding='utf-8')
                row['candidate'] = str(candidate.relative_to(HERE))
                row['verification'] = verify(task, candidate)
            row['passed'] = bool(row.get('response_ok') and read_ok and row.get('verification', {}).get('passed'))
            save(row)

    # B: Unknown synthetic values require an actual successful read, with equivalent paths accepted.
    for trial in range(1, args.tool_trials + 1):
        cwd = HERE / 'nonce-fixtures' / str(trial)
        cwd.mkdir(parents=True, exist_ok=True)
        token = secrets.token_hex(12)
        target = cwd / ('probe-' + secrets.token_hex(4) + '.json')
        target.write_text(json.dumps({'token': token}), encoding='utf-8')
        prompt = (f'Call read exactly once to read {target.name} in the current directory. Read no other file. '
                  'Return exactly one JSON object {"token":"the exact token value from that file"}, without markdown. '
                  'Do not infer the value; an actual successful read is required.')
        offset = (trial - 1) % len(PROFILES)
        for profile in PROFILES[offset:] + PROFILES[:offset]:
            row = call_pi(profile, prompt, cwd, True)
            row.update(suite='B', task='randomized_read', trial=trial, profile=profile['name'],
                       prompt=prompt, expected={'token': token}, fixture=str(target.relative_to(HERE)))
            row['read_ok'] = valid_reads(row, cwd, target, True)
            row['passed'] = bool(row.get('response_ok') and row['read_ok'] and row.get('parsed') == row['expected'])
            save(row)

    # C: Original ten tasks, fresh standardized context, with Luna medium/high interleaved.
    previous = json.loads((HERE.parent / 'flint-20261026' / 'results.json').read_text(encoding='utf-8'))
    cwd = HERE / 'effort-fixtures'
    cwd.mkdir(exist_ok=True)
    (cwd / '.gitattributes').write_text('# Auto detect text files and perform LF normalization\n* text=auto\n', encoding='utf-8')
    for index, case in enumerate(previous['results']):
        profiles = PROFILES[:2] if index % 2 == 0 else list(reversed(PROFILES[:2]))
        for profile in profiles:
            requires_read = case['name'] == 'read_tool'
            prompt = 'Reply in English. Return only the requested JSON object in your final answer, without markdown. ' + case['prompt']
            row = call_pi(profile, prompt, cwd, requires_read)
            row.update(suite='C', task=case['name'], trial=1, profile=profile['name'], prompt=prompt, expected=case['expected'])
            tool_ok = valid_reads(row, cwd, cwd / '.gitattributes', True) if requires_read else not row.get('tool_calls')
            row['passed'] = bool(row.get('response_ok') and tool_ok and row.get('parsed') == row['expected'])
            save(row)
    metadata['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    args.output.write_text(json.dumps({'metadata': metadata, 'baseline': baseline, 'results': records}, indent=2), encoding='utf-8')
    print('REPORT ' + str(args.output), flush=True)


if __name__ == '__main__':
    main()
