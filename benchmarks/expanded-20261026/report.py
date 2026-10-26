"""Produce a stage-by-stage report for the expanded Pi benchmark."""

import argparse
import json
import pathlib
import statistics

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('results', type=pathlib.Path)
args = parser.parse_args()
document = json.loads(args.results.read_text(encoding='utf-8'))
metadata, records = document['metadata'], document['results']
assert len(records) == metadata['expected_calls']
assert len({(row['suite'], row['task'], row['trial'], row['profile']) for row in records}) == len(records)
assert all(not value['buggy']['passed'] and value['reference']['passed'] for value in document['baseline'].values())
summary = {}
for suite in ['A', 'B', 'C']:
    summary[suite] = {}
    for profile in [item['name'] for item in metadata['profiles']]:
        rows = [row for row in records if row['suite'] == suite and row['profile'] == profile]
        if not rows:
            continue
        summary[suite][profile] = {
            'passed': sum(row['passed'] for row in rows), 'runs': len(rows),
            'read_successes': sum(row.get('read_ok', row['task'] == 'read_tool' and row['passed'] and bool(row.get('tool_calls'))) for row in rows),
            'total_wall_seconds': round(sum(row['wall_seconds'] for row in rows), 3),
            'median_wall_seconds': round(statistics.median(row['wall_seconds'] for row in rows), 3),
            'reported_cost_usd': sum(row.get('reported_cost_usd', 0) for row in rows),
            'reported_tokens': sum(row.get('usage', {}).get('totalTokens', 0) for row in rows),
            'timeouts': sum('exceeded 90 seconds' in row.get('error', '') for row in rows),
        }

lines = ['# Expanded Pi benchmark: repairs, tool calls and Luna effort', '',
         f"Pi {metadata['pi_version']}; OpenRouter for all profiles. {len(records)} scored model calls.", '',
         'Profiles: GPT-6 Luna high, GPT-6 Luna medium, and Flint with autonomous reasoning. The Flint high CLI label is retained only for launch consistency.', '',
         '## A: Executed code repairs', '',
         'Three independent seeded Python defects. The model must read the buggy source, return a complete replacement module as JSON, and pass trusted behavioral checks. The harness applies the returned code to a separate candidate file. Models do not run shell commands or edit the working repository.', '',
         'The frozen verifier checks 37 interval properties/examples, 104 pagination cases, and 19 TTL/LRU scenarios (including 15 randomized sequences of 150 operations each). All buggy baselines fail, and all reference implementations pass.', '']


def table(suite):
    lines.extend(['| Profile | Passed | Total seconds | Median seconds | Pi-reported cost USD |',
                  '|---|---:|---:|---:|---:|'])
    for profile, result in summary[suite].items():
        lines.append(f"| {profile} | {result['passed']}/{result['runs']} | {result['total_wall_seconds']:.3f} | {result['median_wall_seconds']:.3f} | {result['reported_cost_usd']:.6f} |")
    lines.append('')


table('A')
lines += ['| Repair | Luna high | Luna medium | Flint |', '|---|---|---|---|']
for task in dict.fromkeys(row['task'] for row in records if row['suite'] == 'A'):
    values = []
    for profile in ['luna-high', 'luna-medium', 'flint']:
        row = next(row for row in records if row['suite'] == 'A' and row['task'] == task and row['profile'] == profile)
        verification = row.get('verification', {})
        values.append(('Pass' if row['passed'] else 'Fail') + f" ({verification.get('passed_checks', 0)}/{verification.get('checks', 0)} checks)")
    lines.append('| ' + task + ' | ' + ' | '.join(values) + ' |')
lines += ['', '## B: Randomized actual reads', '',
          'Each trial creates an unknown synthetic token in a randomly named JSON file. All profiles receive the same file for that trial, in rotating order, using fresh sessions. Passing requires exactly one successful read of that file and the exact token in the final JSON. Equivalent absolute and relative paths are accepted.', '']
table('B')
lines += ['## C: Luna medium versus high', '',
          'Fresh runs of the original ten fixed tasks, with alternating profile order and standardized context. The original read-tool task still requires a real read. These runs are not pooled with the earlier benchmark because the context-loading policy is different.', '']
table('C')
high, medium = summary['C']['luna-high'], summary['C']['luna-medium']
lines.append(f"Medium/high wall-time ratio for suite C: {medium['total_wall_seconds'] / high['total_wall_seconds']:.3f}. This is a descriptive result from one attempt per task, not a stable latency guarantee.")
lines += ['', '## Unsuccessful scored attempts', '']
failures = [row for row in records if not row['passed']]
if not failures:
    lines.append('None.')
for row in failures:
    reason = row.get('error')
    if not reason:
        if row['suite'] in ['A', 'B'] and not row.get('read_ok'):
            reason = 'Required successful source/file read was not completed.'
        elif row['suite'] == 'A':
            verification = row.get('verification', {})
            reason = verification.get('error') or f"Behavior checks passed: {verification.get('passed_checks', 0)}/{verification.get('checks', 0)}."
        else:
            reason = 'Answer or required tool execution did not match the contract.'
    lines.append(f"- Suite {row['suite']}, {row['profile']}, {row['task']}, trial {row['trial']}: {reason}")
lines += ['', '## Method and limits', '',
          '- These are small isolated tasks with seeded defects, not repairs to a production repository or SWE-bench tasks.',
          '- Only read is exposed to the models for repair/tool tasks. The harness writes candidate modules and executes the independent verifier.',
          '- Context files, skills, extensions, MCP and session persistence are disabled for every scored call. Pi still supplies its normal core prompt and tool definitions.',
          '- Code candidates are checked using an AST/import allowlist and restricted builtins in a separate five-second Python process. This is bounded verification, not a general-purpose OS security sandbox.',
          '- Each model call has a 90-second timeout; unsuccessful calls count as failures without automatic retry.',
          '- The model profiles have different reasoning behavior; there is no matched reasoning budget across Luna and Flint.',
          '- Sampling defaults and provider routing can differ by model. Reported costs are Pi usage estimates, not billing receipts.',
          '- Timing includes CLI startup, network, inference and tool round trips. Repair-verification time is recorded separately.',
          '- A and C have one attempt per task per profile. B has ten trials per profile. These sample sizes do not establish general capability rankings.',
          '- An initial interval-task pilot used ambiguous integer-adjacency wording. Its raw results are retained in pilot-ambiguous-contract.json and excluded from scored results. The scored contract explicitly distinguishes a shared endpoint from adjacent integers. Tests and expected behavior were not relaxed.',
          '- Score and cost tables exclude the pilot and its interrupted in-flight request; they cover the 59 scored calls only.',
          '- No raw model thinking text is saved. Synthetic nonce values are benchmark fixtures, not credentials.', '',
          '## Reproduce', '', '```powershell',
          'python benchmarks/expanded-20261026/run.py --prepare-only',
          'python benchmarks/expanded-20261026/run.py --output benchmarks/expanded-20261026/rerun.json',
          'python benchmarks/expanded-20261026/report.py benchmarks/expanded-20261026/rerun.json',
          '```', '', 'The separate output name preserves the original results. Repairs and fixtures are regenerated under this benchmark directory.']
output = args.results.with_suffix('.md')
output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
args.results.with_suffix('.summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
print(output)
