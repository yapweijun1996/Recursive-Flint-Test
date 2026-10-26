# Flint via Pi: custom benchmark

Date: 2026-10-26. Pi 1.4.0, OpenRouter recursive/flint-v1.0:free, thinking high.

10/10 cases passed. Total measured wall time: 63.415 seconds; median per case: 4.867 seconds. Reported total tokens: 55,656; reported API cost: USD 0.

Cases cover arithmetic, Python closures, JavaScript microtasks, interval merging, shortest paths, SQL LEFT JOIN/NULL semantics, binary-search patch selection, tenant predicates, LRU behavior, and one actual read-tool call. Nine cases compare strict parsed JSON to fixed expected values. The tool case also verifies one successful read of .gitattributes.

Each case uses a fresh nonpersistent session, disables extensions and built-in MCP, and permits no tools except read for the tool case. Existing Pi configuration and project context remain loaded. No repository code was modified or executed by the model.

This is a small custom benchmark with one attempt per case, not SWE-bench or a general coding capability score. Most tasks are basic or intermediate; the patch task selects an answer rather than generating a patch. Wall time includes CLI startup, network, inference, and any tool round trip. Token totals sum provider-reported usage across all turns; reasoning is not added again to totalTokens. No throughput or first-token latency is inferred.

Run from this repository on Windows with the same configured Pi/OpenRouter account:

```powershell
python benchmarks/flint-20261026/run.py
```

The runner derives the repository path from its location and writes results-high.json beside the script by default. Use --thinking off for results-off.json, --compare for an interleaved comparison.json, or --output to choose a destination. Each case has a 90-second timeout. Detailed prompts, expected values, final answers, tool calls, timings, and usage are recorded. Raw model reasoning is not saved. The original results.json remains unchanged.

## High versus off comparison

Run `python benchmarks/flint-20261026/run.py --compare`. Both settings are tested for each case, alternating which setting runs first. This preserves the original prompts and expected values.

The fresh comparison scored 9/10 for each setting. Both failed the read-tool requirement by returning the expected answer without calling read. The initial baseline's successful tool call therefore did not repeat consistently.

High took 57.158 seconds total (median 5.811), with 47,903 reported total tokens. Off took 59.464 seconds total (median 5.004), with 48,355 reported total tokens. Both reported USD 0. Off returned thinking content in all ten cases, so these results compare requested CLI settings and do not establish reasoning-disabled behavior. Single trials do not establish a reliable performance difference.

See comparison.json for raw scored results and comparison.md for the per-case table.

### Official reasoning behavior clarification

Recursive's official serving documentation states that Flint decides each turn whether to reason and has no reasoning switch or budget. The thinking and enable_thinking chat-template options have no effect. Therefore, this experiment compares requested Pi CLI labels; it is not an enabled-versus-disabled reasoning experiment and does not establish a benefit from selecting high. Original measurements remain unchanged. Source: https://huggingface.co/RecursiveSI/flint/blob/main/sglang/README.md#chat-format-and-api-usage (checked 2026-10-26).

### Read-tool retries

Three fresh retries of the unchanged read-tool case passed, failed, and passed (2/3). Trials 1 and 3 each called read exactly once and received the file successfully. Trial 2 returned the expected JSON without a tool call. All three reported USD 0. This supports the observed inconsistency; it does not change the original benchmark scores or estimate a reliable long-run success rate. Details and the exact command are in read-tool-retry-20261026-011420.json. The high CLI label was retained only for launch consistency.
