"""Render a scored Pi model comparison without exposing model reasoning."""

import argparse
import json
import pathlib
import statistics

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('results', type=pathlib.Path)
args = parser.parse_args()
data = json.loads(args.results.read_text(encoding='utf-8'))
metadata, groups, rows = data['metadata'], data['summary'], data['results']
models = metadata['models']
root = pathlib.Path(__file__).resolve().parents[2]
for row in rows:
    if not row['requires_read']:
        continue
    calls, ends = row.get('tool_calls', []), row.get('tool_results', [])
    path = calls[0].get('arguments', {}).get('path') if len(calls) == 1 else None
    normalized_pass = bool(row.get('exit_code') == 0 and row.get('stop_reason') == 'stop'
                           and row.get('model') == row['requested_model']
                           and row.get('provider') == 'openrouter'
                           and row.get('parsed') == row['expected']
                           and len(calls) == 1 and calls[0].get('name') == 'read'
                           and isinstance(path, str)
                           and (root / path).resolve() == (root / '.gitattributes').resolve()
                           and len(ends) == 1 and ends[0].get('name') == 'read'
                           and not ends[0].get('is_error'))
    row['original_score'] = row['passed']
    row['passed'] = normalized_pass
for model, group in groups.items():
    model_rows = [row for row in rows if row['requested_model'] == model]
    group['passed'] = sum(row['passed'] for row in model_rows)
    group['answer_tasks_passed'] = sum(row['passed'] for row in model_rows if not row['requires_read'])
    group['read_tasks_passed'] = sum(row['passed'] for row in model_rows if row['requires_read'])
metadata['grading_note'] = 'Read paths are resolved to the target file; equivalent absolute and relative paths are accepted. Original raw results remain unchanged.'
assert len(rows) == metadata['repeats_per_case'] * 10 * len(models)
assert all(row.get('model') == row['requested_model'] and row.get('provider') == 'openrouter'
           for row in rows if row.get('stop_reason') == 'stop')
lines = [
    '# GPT-6 Luna versus Flint through Pi', '',
    f"Pi {metadata['pi_version']}; OpenRouter for both models; {metadata['repeats_per_case']} attempts per case; alternating model order.", '',
    'Luna requested high reasoning effort. Flint received the same CLI label but decides independently whether to reason; these are not matched reasoning budgets.', '',
    '| Model | Passed | Answer tasks | Read-tool tasks | Total seconds | Median seconds | Reported total tokens | Reported cost USD |',
    '|---|---:|---:|---:|---:|---:|---:|---:|',
]
for model in models:
    group = groups[model]
    attempts = metadata['repeats_per_case']
    lines.append(f"| {model} | {group['passed']}/{group['runs']} | {group['answer_tasks_passed']}/{9 * attempts} | {group['read_tasks_passed']}/{attempts} | {group['total_wall_seconds']:.3f} | {group['median_wall_seconds']:.3f} | {group['usage']['totalTokens']} | {group['reported_cost_usd']:.6f} |")
lines += ['', '| Case | Luna passed | Luna median seconds | Flint passed | Flint median seconds |',
          '|---|---:|---:|---:|---:|']
for name in dict.fromkeys(row['name'] for row in rows):
    cells = []
    for model in models:
        group = [row for row in rows if row['requested_model'] == model and row['name'] == name]
        cells += [f"{sum(row['passed'] for row in group)}/{len(group)}",
                  f"{statistics.median(row['wall_seconds'] for row in group):.3f}"]
    lines.append('| ' + name + ' | ' + ' | '.join(cells) + ' |')
lines += ['', '## Unsuccessful attempts', '']
failed = [row for row in rows if not row['passed']]
if not failed:
    lines.append('None.')
for row in failed:
    reason = row.get('error')
    if not reason:
        if row['requires_read'] and not row.get('tool_calls'):
            reason = 'Returned an answer without the required read-tool call.'
        else:
            reason = 'Did not meet the exact answer and tool-execution criteria; inspect results.json.'
    lines.append(f"- {row['requested_model']}, trial {row['trial']}, {row['name']}: {reason}")
lines += ['', '## Limits', ''] + ['- ' + note for note in metadata['limitations']]
lines += ['', '- Provider tokenization, caching and counter classification differ; token counts are not direct measures of equivalent work.',
          '- Three attempts per case provide descriptive results, not a statistically established general model ranking.',
          '- Raw thinking text is excluded from the saved results. Original benchmark scores remain unchanged.', '',
          '- The original running scorer required the literal relative path. The scored JSON corrects that bug by accepting equivalent absolute paths; tool calls and file results remain required. Raw results retain the original scores.', '',
          '## Reproduce', '', '```powershell',
          'python benchmarks/flint-20261026/run_models.py --repeats 3 --output benchmarks/luna-vs-flint-20261026/rerun.json',
          'python benchmarks/flint-20261026/report_models.py benchmarks/luna-vs-flint-20261026/rerun.json',
          '```', '', 'The new output name preserves the original results.']
output = args.results.with_suffix('.md')
output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
scored = args.results.with_suffix('.scored.json')
scored.write_text(json.dumps(data, indent=2), encoding='utf-8')
print(output)
print(scored)
