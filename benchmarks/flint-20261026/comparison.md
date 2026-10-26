# Flint via Pi: high versus off

One fresh trial per case per requested setting, interleaved with alternating order. Pi 1.4.0; recursive/flint-v1.0:free. Original benchmark prompts, expected answers, context loading, MCP restrictions and tool policy were preserved.

| Requested setting | Passed | Total seconds | Median seconds | Input tokens | Output tokens | Reported reasoning tokens | Total tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| high | 9/10 | 57.158 | 5.811 | 41595 | 6308 | 5259 | 47903 |
| off | 9/10 | 59.464 | 5.004 | 41595 | 6760 | 5976 | 48355 |

Both settings reported USD 0. Token fields are provider-reported counters; reasoning is not added to totalTokens again.

| Case | High result | High seconds | Off result | Off seconds |
|---|---|---:|---|---:|
| arithmetic | Pass | 1.827 | Pass | 2.304 |
| python_closures | Pass | 6.428 | Pass | 16.088 |
| javascript_microtasks | Pass | 3.100 | Pass | 3.323 |
| interval_merge | Pass | 3.745 | Pass | 3.822 |
| shortest_path | Pass | 6.108 | Pass | 3.123 |
| sql_left_join_null | Pass | 13.205 | Pass | 9.268 |
| binary_search_repair | Pass | 6.662 | Pass | 6.186 |
| tenant_predicate | Pass | 5.514 | Pass | 6.741 |
| lru_trace | Pass | 9.025 | Pass | 7.020 |
| read_tool | Fail | 1.544 | Fail | 1.589 |

## Interpretation

- Both read-tool failures returned the expected JSON but made zero tool calls. They fail the required behavior despite the correct final value. The original high baseline had passed this requirement.
- Every off case still returned nonempty thinking content. The requested off setting did not establish a no-reasoning condition.
- Off total wall time was 4.0% higher, while its median was lower. With one trial per case and network/startup time included, no reliable speed advantage is established.
- Official clarification, checked 2026-10-26: Recursive states that Flint decides each turn whether to reason, has no reasoning switch or budget, and ignores thinking / enable_thinking chat-template options. This is a comparison of requested Pi labels, not a valid enabled-versus-disabled reasoning comparison. It does not establish a benefit from selecting high. See [official serving documentation](https://huggingface.co/RecursiveSI/flint/blob/main/sglang/README.md#chat-format-and-api-usage). This documentation explains the observed continued reasoning; the exact hosted request path was not captured.
- This benchmark does not evaluate generated patches, repository-scale work, or executed program correctness. No general model ranking follows from these results.

## Reproduce

```powershell
python benchmarks/flint-20261026/run.py --compare --output benchmarks/flint-20261026/comparison-rerun.json
```

This output path preserves the recorded comparison. Raw model reasoning was not stored.
