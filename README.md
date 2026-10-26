# Flint: Verified Testing Knowledge for Another AI Agent

## Interactive web report

The static web report presents the recorded results, interactive timing comparisons, methodology, and downloadable agent notes. Build it without installing dependencies or making model API calls:

```powershell
python scripts/build_site.py --check
python -m http.server 8766 --bind 127.0.0.1 --directory dist
```

Open `http://127.0.0.1:8766/`. Source files live in `site/`; the builder reads scored benchmark records and writes the ignored `dist/` directory. The GitHub Pages workflow deploys that directory when relevant changes are pushed to `main`, or when manually dispatched. Configure the repository's Pages source as GitHub Actions. No local Pi configuration is included in the deployment artifact.

Test date: 2026-10-26. Environment: Windows, Python 3.13, Pi 1.4.0, OpenRouter.

## Model identity

- Exact tested model ID: `recursive/flint-v1.0:free`.
- Developer: Recursive. Open-weight MoE coding model, approximately 39.8B total parameters and 2.5B active per token.
- Context window: 262,144 tokens, shared by prompt and generated output.
- The tested OpenRouter endpoint reports zero input/output token prices. Free access remains subject to rate limits and availability.
- Supports text, reasoning and tool calls. These tests did not evaluate vision.

## Critical reasoning behavior

Recursive's official serving documentation states that Flint decides on each turn whether to reason. It has no reasoning switch or budget; `thinking` / `enable_thinking` chat-template options have no effect.

Consequently:

- Do not assume Pi's `--thinking high` makes Flint reason harder.
- Do not assume Pi's `--thinking off` disables Flint reasoning.
- Our `off` trials still returned thinking content in every case.
- Our high/off experiment compared requested Pi labels, not verified reasoning-on versus reasoning-off conditions.
- We did not capture the actual outgoing request payloads. Do not diagnose a specific Pi or OpenRouter bug from these observations alone.

Official source: https://huggingface.co/RecursiveSI/flint/blob/main/sglang/README.md#chat-format-and-api-usage

## Pi commands verified locally

Temporary session with extensions and built-in MCP disabled:

```powershell
pi --provider openrouter --model recursive/flint-v1.0:free --no-session --no-extensions --no-mcp
```

Standardized read-only benchmark invocation:

```powershell
pi --provider openrouter --model recursive/flint-v1.0:free --no-session --no-extensions --no-mcp --no-context-files --no-skills --tools read --mode json "Your benchmark prompt"
```

- `--no-session`: do not persist the conversation; this is not anonymous provider access.
- `--no-mcp`: disable built-in MCP for this run.
- `--no-extensions`: also prevents third-party MCP extensions from loading through discovery; disables other discovered extensions too.
- `--no-context-files --no-skills`: used only in the expanded benchmark to standardize context.
- `--tools read`: expose only the built-in read tool. Use `--no-tools` for answer-only tasks.

## Observed benchmark results

### Initial custom benchmark

Ten tasks: arithmetic, Python closures, JavaScript microtasks, interval merging, shortest path, SQL LEFT JOIN/NULL semantics, binary-search repair selection, tenant predicates, LRU tracing, and an actual file read.

- Initial Flint run: **10/10**; 63.415 seconds total; median 4.867 seconds; 55,656 reported tokens; reported cost USD 0.
- Fresh interleaved high/off run: **9/10 for each requested setting**. Both skipped the required read-tool call while returning the expected final JSON.
- Three subsequent retries of the unchanged read task: **pass, fail, pass**. The failed trial made zero tool calls.

These results demonstrate that Flint can call read successfully, but may skip an explicit read requirement on some prompts. Correct final text alone does not establish that the requested action occurred.

### GPT-6 Luna versus Flint

Both models used Pi and OpenRouter. Each of the ten tasks ran three times. Luna requested high effort; Flint remained autonomous.

| Metric | GPT-6 Luna | Flint |
|---|---:|---:|
| Total passed | 30/30 | 29/30 |
| Answer tasks | 27/27 | 27/27 |
| Required actual reads | 3/3 | 2/3 |
| Total wall seconds | 185.788 | 247.070 |
| Median wall seconds | 5.804 | 5.164 |
| Pi-reported cost USD | 0.017148 | 0 |

Flint had one 75-second request and one 27.7-second request. Preserve these observations; do not discard slow requests to improve a score. Timing includes startup, network, inference and tool round trips, so it does not isolate model inference speed.

### Expanded tests: code repairs and randomized reads

All profiles used fresh sessions with MCP, extensions, context files and skills disabled.

| Suite | Luna high | Luna medium | Flint |
|---|---:|---:|---:|
| A: executable repairs | 3/3; 28.647s | 3/3; 19.720s | 3/3; 40.473s |
| B: randomized actual reads | 10/10; 57.710s | 10/10; 83.628s | 10/10; 37.202s |
| C: original ten tasks | 10/10; 45.834s | 10/10; 38.987s | Not run |

Times are group totals. There were **59 scored calls, all passing**.

Suite A used isolated seeded defects in interval merging, pagination and TTL/LRU caching. Models read the buggy module and returned a complete replacement as JSON. The harness saved the replacement and executed independent Python checks. Each profile passed all 160 checks: 37 interval checks, 104 pagination checks, and 19 TTL/LRU scenarios, including 15 generated sequences of 150 operations. All buggy baselines failed; reference implementations passed. These were not production-repository edits or autonomous multi-file patch tasks.

Suite B created a randomly named JSON file containing an unknown synthetic token. Passing required exactly one successful read of that file AND the exact token in the final JSON. Flint passed 10/10 in this condition.

Suite C compared Luna settings only. Medium had lower total time, but nearly identical median time: 3.314 seconds versus high's 3.283. Medium was slower in suite B. No universal speed advantage was established.

## Interpretation and limitations

- Flint performed well on these small tasks, including executable code repairs.
- Tool invocation is possible, but earlier explicit-read compliance was inconsistent.
- The randomized-read result does not erase the earlier failures. Both task construction and context policy changed; the cause of the difference is unresolved.
- There is no evidence that Pi's thinking/effort label caused the skipped reads.
- Accept equivalent absolute and relative paths when grading reads. An early scorer incorrectly rejected Luna's valid absolute paths; the comparison report uses corrected scores and retains raw records.
- An interval-task pilot had ambiguous integer-adjacency wording. Its records were retained but excluded. The scored prompt explicitly distinguished shared endpoints from adjacent integers; tests were not relaxed.
- Small samples, different provider infrastructure, sampling defaults, caching and network conditions limit comparisons. Token counts also use different tokenizers.
- These tests are not SWE-bench, a security evaluation, or proof of general coding-agent reliability.
- Raw model thinking text was not saved. Reasoning counts are reported usage counters, not audited measurements of cognitive effort.

## Parameter guidance

Pi 1.4.0 supports request-body defaults through `samplingParams` under a model override in `~/.pi/agent/models.json`; it does not provide built-in CLI flags such as `--temperature`.

The queried Flint endpoint advertised 11 fields: `reasoning`, `include_reasoning`, `max_tokens`, `temperature`, `top_p`, `stop`, `seed`, `tools`, `response_format`, `logprobs`, and `top_logprobs`. Advertised fields are not proof of effective reasoning control.

The practical generation controls are `temperature`, `top_p`, `max_tokens`, `seed`, and `stop`. Flint's documented sampling defaults are temperature 1.0, top-p 0.95 and top-k 20. The queried OpenRouter endpoint did not list top-k support. No parameter-tuning experiment was performed.

## Evidence and reproduction

- Initial benchmark: [results](benchmarks/flint-20261026/results.json).
- High/off comparison: [report](benchmarks/flint-20261026/comparison.md).
- Read retries: [results](benchmarks/flint-20261026/read-tool-retry-20261026-011420.json).
- Luna comparison: [report](benchmarks/luna-vs-flint-20261026/results.md), [corrected scores](benchmarks/luna-vs-flint-20261026/results.scored.json).
- Expanded benchmark: [report](benchmarks/expanded-20261026/results.md), [results](benchmarks/expanded-20261026/results.json), [runner](benchmarks/expanded-20261026/run.py), [behavioral checks](benchmarks/expanded-20261026/suite.py).
- Model card: https://huggingface.co/RecursiveSI/flint
- OpenRouter model: https://openrouter.ai/recursive/flint-v1.0:free
- Pi configuration: https://pi.dev/docs/latest/models-configuration

Reproduce the expanded benchmark from the repository root using the existing configured Pi/OpenRouter account:

```powershell
python benchmarks/expanded-20261026/run.py --prepare-only
python benchmarks/expanded-20261026/run.py --output benchmarks/expanded-20261026/rerun.json
python benchmarks/expanded-20261026/report.py benchmarks/expanded-20261026/rerun.json
```

Do not include credentials or raw private project data in a handoff. Treat these dated observations as evidence about the tested setup, not permanent guarantees about Flint.
