# Expanded Pi benchmark: repairs, tool calls and Luna effort

Pi 1.4.0; OpenRouter for all profiles. 59 scored model calls.

Profiles: GPT-6 Luna high, GPT-6 Luna medium, and Flint with autonomous reasoning. The Flint high CLI label is retained only for launch consistency.

## A: Executed code repairs

Three independent seeded Python defects. The model must read the buggy source, return a complete replacement module as JSON, and pass trusted behavioral checks. The harness applies the returned code to a separate candidate file. Models do not run shell commands or edit the working repository.

The frozen verifier checks 37 interval properties/examples, 104 pagination cases, and 19 TTL/LRU scenarios (including 15 randomized sequences of 150 operations each). All buggy baselines fail, and all reference implementations pass.

| Profile | Passed | Total seconds | Median seconds | Pi-reported cost USD |
|---|---:|---:|---:|---:|
| luna-high | 3/3 | 28.647 | 7.777 | 0.001305 |
| luna-medium | 3/3 | 19.720 | 6.392 | 0.001200 |
| flint | 3/3 | 40.473 | 18.437 | 0.000000 |

| Repair | Luna high | Luna medium | Flint |
|---|---|---|---|
| merge_intervals | Pass (37/37 checks) | Pass (37/37 checks) | Pass (37/37 checks) |
| pagination | Pass (104/104 checks) | Pass (104/104 checks) | Pass (104/104 checks) |
| ttl_lru | Pass (19/19 checks) | Pass (19/19 checks) | Pass (19/19 checks) |

## B: Randomized actual reads

Each trial creates an unknown synthetic token in a randomly named JSON file. All profiles receive the same file for that trial, in rotating order, using fresh sessions. Passing requires exactly one successful read of that file and the exact token in the final JSON. Equivalent absolute and relative paths are accepted.

| Profile | Passed | Total seconds | Median seconds | Pi-reported cost USD |
|---|---:|---:|---:|---:|
| luna-high | 10/10 | 57.710 | 3.903 | 0.001875 |
| luna-medium | 10/10 | 83.628 | 5.719 | 0.001826 |
| flint | 10/10 | 37.202 | 3.434 | 0.000000 |

## C: Luna medium versus high

Fresh runs of the original ten fixed tasks, with alternating profile order and standardized context. The original read-tool task still requires a real read. These runs are not pooled with the earlier benchmark because the context-loading policy is different.

| Profile | Passed | Total seconds | Median seconds | Pi-reported cost USD |
|---|---:|---:|---:|---:|
| luna-high | 10/10 | 45.834 | 3.283 | 0.001008 |
| luna-medium | 10/10 | 38.987 | 3.314 | 0.000978 |

Medium/high wall-time ratio for suite C: 0.851. This is a descriptive result from one attempt per task, not a stable latency guarantee.

## Unsuccessful scored attempts

None.

## Method and limits

- These are small isolated tasks with seeded defects, not repairs to a production repository or SWE-bench tasks.
- Only read is exposed to the models for repair/tool tasks. The harness writes candidate modules and executes the independent verifier.
- Context files, skills, extensions, MCP and session persistence are disabled for every scored call. Pi still supplies its normal core prompt and tool definitions.
- Code candidates are checked using an AST/import allowlist and restricted builtins in a separate five-second Python process. This is bounded verification, not a general-purpose OS security sandbox.
- Each model call has a 90-second timeout; unsuccessful calls count as failures without automatic retry.
- The model profiles have different reasoning behavior; there is no matched reasoning budget across Luna and Flint.
- Sampling defaults and provider routing can differ by model. Reported costs are Pi usage estimates, not billing receipts.
- Timing includes CLI startup, network, inference and tool round trips. Repair-verification time is recorded separately.
- A and C have one attempt per task per profile. B has ten trials per profile. These sample sizes do not establish general capability rankings.
- An initial interval-task pilot used ambiguous integer-adjacency wording. Its raw results are retained in pilot-ambiguous-contract.json and excluded from scored results. The scored contract explicitly distinguishes a shared endpoint from adjacent integers. Tests and expected behavior were not relaxed.
- Score and cost tables exclude the pilot and its interrupted in-flight request; they cover the 59 scored calls only.
- No raw model thinking text is saved. Synthetic nonce values are benchmark fixtures, not credentials.

## Reproduce

```powershell
python benchmarks/expanded-20261026/run.py --prepare-only
python benchmarks/expanded-20261026/run.py --output benchmarks/expanded-20261026/rerun.json
python benchmarks/expanded-20261026/report.py benchmarks/expanded-20261026/rerun.json
```

The separate output name preserves the original results. Repairs and fixtures are regenerated under this benchmark directory.
