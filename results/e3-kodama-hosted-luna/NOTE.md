# Experiment 3 on hosted models: pilot (gpt-5.6-luna, one trial per case)

**This folder is the pilot, not the reported run.** It has 200 trials: one per case in each of the five conditions. The hosted run the paper reports is `../e3-kodama-hosted/`: five trials per case, all five conditions. It uses the same models and configuration, a runner with a stop rule added, and Kodama `3101c5b`. That commit is this pilot's `70dcabb` plus a fix for the queue-consumer defect described under Problems.

Other hosted runs and attempts:
- the first hosted run, on `70dcabb`, five trials per case, conditions a–d only: `../e3-kodama-hosted-run1/`;
- its two stopped attempts at e: `../e3-kodama-hosted-aborted/`;
- the reported run's first attempt at e, stopped by a Docker Desktop restart: `../e3-kodama-hosted-aborted-3101c5b/`;
- the pilot's failed attempts at e: `../e3-kodama-hosted-luna-aborted/`.

## What ran

- **Pack.** `evals/packs/kodama-async-recall`: 40 cases, unchanged since run 2 (`../e3-kodama/`). Text mode, lead-in gap at 210 words per minute, same grading.
- **Kodama.** Commit `70dcabb` (branch `e3-telemetry-bridge`), built into a local Docker image. One local stack (Kodama, Postgres, LiveKit) with its own volumes. Eval sessions skip the memorizer (`pipeline.skip_eval_memorizer`).
- **Runner** (Kodama repository, branch `e3-hosted-run`):
  - `recall/run.py` and `recall/analyze.py` at `e961976`;
  - `recall/telemetry_cost.py` at `944b6a3`.
- **Models.** These are Kodama's production deployment defaults (`config/gcp.yaml`):
  - reply: gpt-5.6-luna (OpenAI Responses API);
  - output checks (greeting, advice, uncited-claim): gpt-5.6-luna;
  - embeddings: text-embedding-3-small.

  The demo presences use claude-sonnet-5 for the reply, and so did Experiment 2's hosted run. No Sonnet run of Experiment 3 was made.
- **Request fields sent.** These were recorded from the requests themselves (`otel.instruments.openai.http`).
  - Reply: no temperature, no reasoning effort and no output limit, so OpenAI's defaults apply. Kodama's config notes that luna's default reasoning effort is medium.
  - Checks: `reasoning_effort: none`, `max_output_tokens: 128`, no temperature (luna rejects the parameter).
- **Trials per case.** One trial per case in each condition, set with `--trials 1` on the cases in memory. The pack files stored in the bundles still say `trials: 5`; `condition.json` records `trials_per_case: 1`.

## Differences from run 2

- **Models.** Run 2 ran locally: gemma4:e4b at temperature 1.0 (Ollama's default) for the reply and the checks, with nomic-embed-text embeddings.
- **Trials.** One trial per case instead of five.
- **Kodama commits after run 2's `52dbd04`, included in `70dcabb`:**
  - `f992ca3`: eval presences can skip the memorizer. Text sessions never ran it anyway.
  - `a31e446`: voice analysis metrics.
  - `9ef5851`, `3a90b05`: speaking a reply clause by clause. Voice only; `speech.clauses` is off here.
  - `53f6e2f`: the greeting and advice checks stream their answer and stop as soon as their verdict is decided. The decisions are the same; the calls end earlier.
  - `19340b1`: Ollama retry; not used here.
  - `b2938ba`: temperature records.
  - `7059196`: documentation.
  - `70dcabb`: text turns get their trace id, and each trial's spans are saved.
- **Request capture.** `otel.instruments.openai.http` is on.

## When (UTC)

| condition | ran | seconds |
|---|---|---|
| a-tool | 2026-11-14 10:15:03–10:30:46 | 943 |
| b-backthought | 2026-11-14 10:31:09–10:46:10 | 901 |
| c-blocking | 2026-11-14 10:46:11–11:01:21 | 910 |
| d-blocking-backthought | 2026-11-14 11:01:22–11:17:46 | 983 |
| e-backthought-tool | 2026-11-15 10:11:08–10:27:42 (third attempt; see Problems) | 994 |

A 5-trial smoke (2026-11-14 10:11–10:13) set the cost estimate. It is not in this folder.

## Results

From `summary.md`, `trials.csv` and `telemetry.csv`. Recall pass has a 95% interval. The reply path's recall wait applies to the blocking conditions only.

| condition | passed | errors | templated | recall pass | run 2 recall pass | path ms median / p90 | recall wait on the reply path, ms median / p90 |
|---|---|---|---|---|---|---|---|
| a-tool | 28/40 | 0 | 0 | 67% [50, 83] | 63% | 9414 / 11082 | – |
| b-backthought | 21/40 | 1 | 1 | 40% [23, 57] | 29% | 5765 / 6449 | – |
| c-blocking | 38/40 | 0 | 0 | 97% [90, 100] | 84% | 6141 / 7046 | 295 / 355 |
| d-blocking-backthought | 38/40 | 0 | 1 | 97% [90, 100] | 85% | 6310 / 8989 | 289 / 337 |
| e-backthought-tool | 36/40 | 0 | 0 | 90% [77, 100] | 67% | 9082 / 11172 | – |

- Run 2's recall wait on the reply path was 97 ms. Here the query is embedded by OpenAI, not by a local model.
- All five bundles are sealed and verify. Every trial has its spans in `telemetry/`.

## Problems, and what was done

1. **Condition e failed twice before the delivered attempt.** Kodama embeds every page of a trial's memorome clone through a background queue (49 pages, one OpenAI request each), and the runner waits up to 180 s for that before the trial starts.
   - **Attempt 1** (2026-11-14 11:17 UTC). After 3 trials, OpenAI embedding requests started to take longer than Kodama's 30 s limit. While its handler waited, Kodama's embedding consumer lost its NATS heartbeat ("embed consumer: next message error … no heartbeat received", from 11:23 UTC). It never recovers from that: no page was embedded again, and every later trial waited out its 180 s. The run was stopped at 12:03 UTC, before it wrote a bundle, and the backend was restarted.
   - **Attempt 2** (12:09–14:09 UTC). Twelve embedding requests timed out between 12:09 and 12:15 UTC. The consumer then lost its heartbeat again, and all 40 trials failed in setup with no model call.
   - **Attempt 3** (2026-11-15) ran on a freshly created stack (new volumes) with the same image and configuration. It finished with no embedding errors, and it is the one in this folder.
   - **Cause.** The host neither slept nor lost its network (power and system logs). OpenAI's status page lists no API incident for that time. Plain requests from the container to the API returned at once afterwards. So the stalls were on the provider side or in the Docker network path, and their exact cause is not known.
   - **Defect.** That one stall made the whole condition unusable is a Kodama defect: the embedding consumer loop does not recover after an error. Its "no heartbeat received" is what the loop logs when NATS deletes its non-durable consumer while no pull request is waiting, so the consumer was very likely deleted here too: the first hosted run's second e attempt logged the same message with its consumer gone from the NATS store (see `../e3-kodama-hosted-aborted/NOTE.md`). It was not changed for the pilot, which stays at `70dcabb`. The first hosted run (`../e3-kodama-hosted-run1/`) guarded against it instead and hit a second form of the defect. Kodama declares its consumers without a durable name, so NATS deleted the conversation consumer after it went about 5 s without a pull request, and Kodama never fetched it again. The defect was then fixed in Kodama `3101c5b`, and the reported run (`../e3-kodama-hosted/`) ran all five conditions on it with no consumer error.
2. **One trial in b ended in an error** (case `regret`, 2026-11-14 10:42 UTC). The greeting check got its HTTP 200 from OpenAI after 1.3 s, but the streamed answer did not arrive within the check's 8 s limit. The output gate then failed closed, and the turn ended with no reply (`RuntimeError: context deadline exceeded`). This is how the product behaves when a provider stalls. It stays in the data as an error.
3. **Two replies were templated by the output gate**, both in case `abs-coat-colour`, in b and d. The gate replaced the reply with its abstention template, and both trials passed. This is product behaviour, not a run problem.
4. **Check calls without usage.** The greeting and advice checks stream their answer, and the request capture records no usage for a streamed response. Since `53f6e2f` they may also stop reading once the verdict is decided. These 398 calls (two per trial, minus 2) are listed as `unmetered_calls`. `cost_usd` leaves them out. `cost_usd_upper` bills each one at the largest metered check input of the run (1,092 tokens) plus 128 output tokens. Their request texts are at most about 390 tokens, so that bound is generous.
5. **Smaller items:**
   - `analyze.py` first failed on the new `telemetry/` folder and was fixed to skip it (`e961976`).
   - Copying the OpenAI key into the stack needed Anton's approval in the session.

## Cost

Prices are in `cost.json`: gpt-5.6-luna costs $0.20 per million input tokens, $0.02 cached and $1.20 output; text-embedding-3-small costs $0.02. The source is https://developers.openai.com/api/docs/pricing, read 2026-11-13.

| | USD |
|---|---|
| model calls, metered | 0.109 |
| model calls, upper bound (unmetered checks billed in full) | 0.257 |
| embeddings, estimate (memorome clone per trial plus queries) | 0.014 |
| **total** | **0.123 (at most 0.271)** |

The failed e attempts cost almost nothing more:
- attempt 1 completed 3 trials, $0.003 metered;
- attempt 2 made no model calls;
- the 5-trial smoke cost about $0.004.

## Files

- **`<condition>/<bundle>/`.** The sealed Circumstances bundle; `circumstances verify-bundle` passes for all five.
- **`<condition>/condition.json`.** Settings, sampling sent, Kodama commit, times and seal check.
- **`trials.csv`, `summary.json`, `summary.md`.** From `recall/analyze.py`.
- **`telemetry.csv`.** Per trial:
  - `path_ms` and `blocking_ms` (the reply path's wait for recall);
  - model calls (reply, check, unmetered);
  - tokens: input, cached, output and reasoning, overall and per provider;
  - `cost_usd` and `cost_usd_upper`.
- **`cost.json`.** Prices, request fields sent, totals per condition and per provider, and the embedding estimate.
- **`telemetry/<condition>.kodama-traces.jsonl`.** One line per trial with the turn's spans. Kodama's product text was removed before publishing:
  - the system prompts, check prompts and tool definitions (`instructions`, `tools`);
  - the agent and tool descriptions.

  Also removed: OpenAI's response and item ids, and the encrypted reasoning blobs. Conversation messages, outputs, usage, timings and gate verdicts are kept. The unscrubbed dumps are kept outside this repository.
