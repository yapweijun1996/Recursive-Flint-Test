# GPT-6 Luna versus Flint through Pi

Pi 1.4.0; OpenRouter for both models; 3 attempts per case; alternating model order.

Luna requested high reasoning effort. Flint received the same CLI label but decides independently whether to reason; these are not matched reasoning budgets.

| Model | Passed | Answer tasks | Read-tool tasks | Total seconds | Median seconds | Reported total tokens | Reported cost USD |
|---|---:|---:|---:|---:|---:|---:|---:|
| openai/gpt-6-luna | 30/30 | 27/27 | 3/3 | 185.788 | 5.804 | 148520 | 0.017148 |
| recursive/flint-v1.0:free | 29/30 | 27/27 | 2/3 | 247.070 | 5.164 | 169716 | 0.000000 |

| Case | Luna passed | Luna median seconds | Flint passed | Flint median seconds |
|---|---:|---:|---:|---:|
| arithmetic | 3/3 | 4.606 | 3/3 | 2.239 |
| python_closures | 3/3 | 4.127 | 3/3 | 7.319 |
| javascript_microtasks | 3/3 | 6.562 | 3/3 | 6.520 |
| interval_merge | 3/3 | 5.906 | 3/3 | 4.267 |
| shortest_path | 3/3 | 5.902 | 3/3 | 4.246 |
| sql_left_join_null | 3/3 | 6.623 | 3/3 | 9.714 |
| binary_search_repair | 3/3 | 7.488 | 3/3 | 8.072 |
| tenant_predicate | 3/3 | 9.385 | 3/3 | 5.097 |
| lru_trace | 3/3 | 8.811 | 3/3 | 5.080 |
| read_tool | 3/3 | 3.467 | 2/3 | 5.230 |

## Unsuccessful attempts

- recursive/flint-v1.0:free, trial 1, read_tool: Returned an answer without the required read-tool call.

## Limits

- Small fixed custom benchmark, not SWE-bench or a general coding ranking.
- Nine answer tasks and one real read-tool task; no patches generated or executed.
- Independent nonpersistent Pi sessions; extensions and built-in MCP disabled.
- Same provider platform, not necessarily the same upstream infrastructure.
- Requested high for both; Flint decides when to reason and has no effort control.
- Existing Pi settings and project context retained; provider sampling defaults retained.
- Wall time includes startup, network, inference and all tool turns.
- Token counters and costs are reported by Pi; counters are not cross-tokenizer equivalents.
- No automatic retries; unsuccessful responses count as failures.

- Provider tokenization, caching and counter classification differ; token counts are not direct measures of equivalent work.
- Three attempts per case provide descriptive results, not a statistically established general model ranking.
- Raw thinking text is excluded from the saved results. Original benchmark scores remain unchanged.

- The original running scorer required the literal relative path. The scored JSON corrects that bug by accepting equivalent absolute paths; tool calls and file results remain required. Raw results retain the original scores.

## Reproduce

```powershell
python benchmarks/flint-20261026/run_models.py --repeats 3 --output benchmarks/luna-vs-flint-20261026/rerun.json
python benchmarks/flint-20261026/report_models.py benchmarks/luna-vs-flint-20261026/rerun.json
```

The new output name preserves the original results.
