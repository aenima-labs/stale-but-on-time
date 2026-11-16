# Experiment 3 on hosted models: reported run (gpt-5.6-luna, five trials per case, Kodama `3101c5b`)

**This folder is the hosted run the paper reports. All five conditions are complete: 1,000 trials, one sealed bundle per condition.**

It runs on Kodama `3101c5b`, which is `70dcabb` with a fix to its queue consumers. The first hosted run, on `70dcabb`, lost condition e twice to a defect in those consumers. Anton then decided to fix the product and rerun all five conditions ("Fix and rerun all"). This is that rerun.

Other folders:
- `../e3-kodama-hosted-run1/`: the first hosted run, on `70dcabb`, conditions a–d only.
- `../e3-kodama-hosted-aborted/`: that run's two stopped attempts at e, with the analysis of the defect and the local checks of the fix.
- `../e3-kodama-hosted-aborted-3101c5b/`: this run's first attempt at e, stopped when Docker Desktop restarted on the host (Problems 1).
- `../e3-kodama-hosted-luna/`: the pilot, one trial per case.
- `../e3-kodama-hosted-luna-aborted/`: the pilot's failed attempts at e.

## What ran

- **Pack.** `evals/packs/kodama-async-recall`: 40 cases, unchanged since run 2 (`../e3-kodama/`).
  - Text mode, lead-in gap at 210 words per minute, same grading.
  - Five trials per case.
- **Kodama.** Commit `3101c5b` on branch `e3-hosted-run` of the Kodama repository. The branch is not merged into Kodama's main branch.
  - Built into one local Docker image, `sha256:db428e50…`, used for every condition.
  - Eval sessions skip the memorizer (`pipeline.skip_eval_memorizer`).
- **Runner.** `recall/run.py`, `recall/analyze.py` and `recall/telemetry_cost.py` at `3101c5b`. They are the same files as the first hosted run's runner at `944b6a3`.
- **Models.** Kodama's production defaults (`config/gcp.yaml`), as in the first hosted run and the pilot:
  - reply: gpt-5.6-luna (OpenAI Responses API);
  - output checks (greeting, advice, uncited-claim): gpt-5.6-luna;
  - embeddings: text-embedding-3-small.
- **Request fields sent.** Recorded from the requests themselves (`otel.instruments.openai.http`).
  - Reply: no temperature, reasoning effort or output limit, so OpenAI's defaults apply.
  - Checks: `reasoning_effort: none`, `max_output_tokens: 128`.
- **Order: a, e, b, c, d.** The conditions ran one after another, never in parallel.
  - a had already started when the order was set.
  - e ran right after it, on its own, because e is the condition the defect had stopped. A failure of the fix would then show early, before b–d were spent.
- **Guards:**
  1. **A fresh Kodama process for each condition.** Kodama was restarted before each condition (same volumes).
  2. **A watchdog.** It followed Kodama's log and recorded every consumer error, "resumed" and embedding handler error with its time. It would have stopped the runner on a second consumer error with no "resumed" in between. It never fired.
  3. **A stop rule in the runner.** The runner stops after three trials in a row fail or time out (`--stop-after 3`, recorded in `condition.json`).
  4. **No sleep.** The machine was kept awake (`caffeinate`).

  A stopped condition writes no bundle.
- **Smoke.** On the first stack below, 2026-11-15 20:54:39–20:57:44 UTC: condition e, one trial per case (40 trials), 0 errors, bundle sealed. It is not in this folder.
- **Stacks.** Each stack is one local set of Kodama, Postgres and LiveKit containers.
  - **Stack 1:** volumes created fresh on 2026-11-15 at 20:54 UTC. The smoke, a, and the first attempt at e ran on it.
  - **Stack 2:** after Docker Desktop restarted, the stack was created again at 23:52 UTC on new, empty volumes, with the same images. e, b, c and d ran on it.
- **Docker.** Docker Desktop 4.99.0 (build 245822), engine 29.9.3, for every condition. The restart did not change either version (`../e3-kodama-hosted-aborted-3101c5b/NOTE.md`).

## What changed from `70dcabb`

`git diff 70dcabb 3101c5b`: 11 files, 940 lines added and 161 removed. Nothing else changed: onboarding, data, infrastructure, configuration and the Dockerfile are the same.

**The fix (commit `3101c5b`):**

| file | change |
|---|---|
| `backend/internal/queue/jetstream.go` | Every consumer gets a durable name, so NATS no longer deletes it after about 5 s without a pull request. `Ensure` creates or updates the streams and consumers. |
| `backend/internal/queue/consume.go` (new) | A consumer loop that, after any error, stops its iterator, fetches the consumer again (creating it if it is missing) and goes on pulling. It logs "<label>: next message error" and "<label>: resumed". |
| `backend/internal/queue/consume_test.go` (new) | Tests against an embedded NATS server. Consumers are durable. An old non-durable consumer becomes durable with its queued message kept. The loop resumes after its consumer is deleted. A durable consumer survives a gap in pulls that deletes a non-durable one. |
| `backend/internal/app/pipeline/pipeline.go` | The embedding and memorizer consumer loops use the new loop. |
| `backend/internal/app/pipeline/media_analyze.go` | The media-analysis consumer loop uses the new loop. |
| `backend/cmd/pipeline-worker/main.go` | The standalone pipeline worker's copies of the embedding and memorizer loops use the new loop. |

**The runner (commits `e961976`, `38d3f36`, `944b6a3`).** These are the first hosted run's runner, unchanged here.

| file | change |
|---|---|
| `evals/recall/run.py` | `--trials` sets the trials per case; the stop rule is wired in. |
| `evals/recall/stop_rule.py` (new) | Stops a run after three trials in a row fail or time out. |
| `evals/recall/analyze.py` | Skips the `telemetry/` folder. |
| `evals/recall/telemetry_cost.py` (new) | Per-trial calls, tokens and cost from each trial's spans. |
| `evals/tests/test_stop_rule.py` (new) | Tests of the stop rule. |

**The reply path is unchanged.** These files are not on the turn's path. The turn, its recall (blocking, backthought, tool), the model calls, the output checks and the gate are the same code as in `70dcabb`. The fix changes only how the background queue consumers are declared and how their loops recover. Those consumers embed memorome pages and conversation rows, run the memorizer, and analyse media.

**Checks of the fix before any trial:**
- The tests above pass (`go test -tags sqlite_fts5 -short -race ./...`).
- A further local check with no API calls deleted the consumer while no pull request was waiting. That is the second form of the defect, "no heartbeat received". The loop resumed and delivered the queued messages.

Their output is in `../e3-kodama-hosted-aborted/nats-consumer-check/fixed-3101c5b/`.

## When (UTC)

| condition | ran | seconds | s per trial | stack |
|---|---|---|---|---|
| a-tool | 2026-11-15 20:58:15–22:37:07 | 5932 | 29.7 | 1 |
| e-backthought-tool, first attempt | 2026-11-15 22:37:23–23:44:01, stopped | – | – | 1 |
| e-backthought-tool | 2026-11-15 23:52:40 – 2026-11-16 01:28:13 | 5733 | 28.7 | 2 |
| b-backthought | 2026-11-16 01:28:41–02:44:28 | 4547 | 22.7 | 2 |
| c-blocking | 2026-11-16 02:44:31–04:03:35 | 4744 | 23.7 | 2 |
| d-blocking-backthought | 2026-11-16 04:03:39–05:20:58 | 4639 | 23.2 | 2 |

The five reported conditions took 7.1 hours, against about 8 hours in `estimate.md`.

## Results

The figures come from `summary.md`, `summary.json`, `trials.csv` and `telemetry.csv`.
- Intervals are 95% bootstrap intervals over cases, with a case's five trials kept together.
- Recall wait on the reply path applies to the blocking conditions only.
- "First run" is `../e3-kodama-hosted-run1/` on `70dcabb`.

| condition | passed | errors | templated | recall pass | first run | pilot | run 2 | path ms median / p90 | recall wait on the reply path, ms median / p90 |
|---|---|---|---|---|---|---|---|---|---|
| a-tool | 134/200 | 0 | 2 | 65% [47, 81] | 65% | 67% | 63% | 9076 / 10394 | – |
| b-backthought | 104/200 | 1 | 12 | 39% [23, 57] | 41% | 40% | 29% | 5625 / 7066 | – |
| c-blocking | 187/200 | 1 | 3 | 95% [88, 100] | 97% | 97% | 84% | 6106 / 7065 | 292 / 352 |
| d-blocking-backthought | 190/200 | 0 | 4 | 97% [90, 100] | 96% | 97% | 85% | 6052 / 7034 | 299 / 355 |
| e-backthought-tool | 172/200 | 0 | 2 | 89% [77, 99] | – | 90% | 67% | 8932 / 10150 | – |

- **Coherence.**
  - One Kodama commit (`3101c5b`), one image, one configuration and one runner.
  - Each condition has its own settings document (`settings_id` in `condition.json`).
  - a ran on stack 1; e, b, c and d ran on stack 2. The two stacks share the image and configuration. Each began on empty volumes, and Kodama was restarted before every condition on either stack.
- **Completeness.** Each of the 40 cases ran exactly five times in each of the five conditions.
- **Seals.** All five bundles are sealed, and `circumstances verify-bundle` passes for each.
- **Attempts.**
  - a, b, c and d are their first attempts.
  - e is its second attempt. The first stopped when Docker Desktop restarted (Problems 1) and is not reported.
- **Recall wait.** The recall wait on the reply path is close to the pilot's (295 and 289 ms) and lower than the first run's (368 and 376 ms). The query is embedded by OpenAI on the reply path, so the wait follows OpenAI's embedding latency on the day.
- **Recall pass against the first run.** a–d are within a few points of the first run, well inside the intervals.

### Queue consumers: every creation, and the trials near one

Kodama logs "jetstream streams and consumers ready" each time it creates or updates its consumers. It does that only at start-up. The full logs of both stacks were saved; they are not in this repository.

| time (UTC) | stack | when |
|---|---|---|
| 2026-11-15 20:54:22 | 1 | stack created (new volumes): consumers created |
| 2026-11-15 20:54:38 | 1 | restart before the smoke |
| 2026-11-15 20:58:12 | 1 | restart before a (first trial 20:58:15) |
| 2026-11-15 22:37:22 | 1 | restart before e's first attempt (a ended 22:37:07) |
| 2026-11-15 23:52:12 | 2 | stack created (new volumes): consumers created |
| 2026-11-15 23:52:37 | 2 | restart before e (first trial 23:52:40) |
| 2026-11-16 01:28:38 | 2 | restart before b (e ended 01:28:13; b's first trial 01:28:41) |
| 2026-11-16 02:44:28 | 2 | restart before c (b ended 02:44:28; c's first trial 02:44:31) |
| 2026-11-16 04:03:35 | 2 | restart before d (c ended 04:03:35; d's first trial 04:03:39) |

- **No consumer was recreated during a condition.** Neither log has a "next message error", "restart error" or "resumed" line. The script restarted Kodama only after the previous condition's runner had exited, so each creation came between conditions.
- **No trial overlapped a creation or a recovery.**
- **Embedding errors.** Neither stack logged one during a reported condition. The only one is at 23:44:00.882, in the stopped first attempt at e, when Docker stopped the container.
- **Every reported trial started with its memorome fully embedded.** All 40 cases set `wait_embedded: true`, so a trial waits until every page of its memorome clone has an embedding. A trial that waits more than 180 s fails in setup. No trial here failed in setup; the two errors are in the turn (Problems 2).

### Templated replies

The output gate replaced 23 replies with its abstention template. This is product behaviour, not a run problem.
- **a:** amb-flood twice.
- **b:** 12 replies in 9 cases. abs-ansel-country, abs-coat-colour and shift-dog-name twice each; abs-school-name, marbling-travel, regret, shift-honey-prize, shift-lighthouse-steps and shift-teacher once each.
- **c:** abs-chess-opening three times.
- **d:** abs-chess-opening three times, abs-rosalind-university once.
- **e:** abs-school-name and amb-passport once each.

## Problems, and what was done

### 1. e's first attempt was stopped by a Docker Desktop restart

- **What happened.** At 23:43:55 UTC macOS launched Docker Desktop from its update-install folder. At 23:44:00 Docker stopped every container on the host, in all local stacks.
- **How e stopped.** The trial then waiting for its embeddings failed, the next two failed at once, and the stop rule ended the attempt after 138 finished trials. It wrote no bundle.
- **Kodama had no fault.** It logged no consumer error in the 66 minutes before the restart. On `70dcabb`, e had stopped after about 38 and 27 minutes.
- **What was done.**
  - The attempt was set aside in `../e3-kodama-hosted-aborted-3101c5b/`, with the evidence.
  - The stack was created again on new volumes with the same images, and e was rerun from the start, then b, c and d.
  - Docker was not restarted again during the run.

### 2. Two trials ended in an error

- **b-backthought, case `regret`, trial 4,** 2026-11-16 02:24 UTC.
- **c-blocking, case `flat-cat`, trial 2,** 03:31 UTC.

In both, the output gate's uncited-claim check called OpenAI and the call ran past its deadline ("openai: call failed: context deadline exceeded"). The gate then failed closed and the turn ended with no reply. This is how the product behaves when the provider stalls; the pilot had one such error in b. Both stay in the data as errors.

### 3. Unmetered check calls

- **What they are.** The greeting and advice checks stream their answer, and the request capture records no usage for a streamed response. That is 1,977 calls: two per trial, minus the 23 templated turns.
- **How they are counted.** They are in `unmetered_calls` and left out of `cost_usd`.
- **Upper bound.** `cost_usd_upper` bills each one at the largest metered check input of the run (1,110 tokens) plus 128 output tokens.

### 4. Embedding queue churn

- **What happens.** Kodama's backfill republishes up to 32 unembedded rows a minute. Stack 1 logged 128 such republishes and stack 2 logged 195.
- **Why it is harmless.** This is normal for Kodama: rows waiting to be embedded are published again, and the stream drops duplicates.

## Cost

Prices are in `cost.json`:
- gpt-5.6-luna: $0.20 per million input tokens, $0.02 cached, $1.20 output;
- text-embedding-3-small: $0.02 per million tokens.

The source is https://developers.openai.com/api/docs/pricing, read 2026-11-13.

| | metered | upper bound (unmetered checks billed in full) |
|---|---|---|
| a-tool | 0.120 | 0.270 |
| e-backthought-tool | 0.132 | 0.281 |
| b-backthought | 0.079 | 0.225 |
| c-blocking | 0.081 | 0.230 |
| d-blocking-backthought | 0.086 | 0.235 |
| **model calls, five conditions** | **0.497** | **1.240** |
| embeddings, estimate | 0.067 | 0.067 |
| **total** | **0.565** | **1.307** |
| e's first attempt, not reported (138 trials, embeddings included) | 0.093 | 0.196 |

Figures are in USD.

- **Against the estimate.** `estimate.md` was written before the first trial: about $0.58, at most about $1.27. The run cost $0.565, and its upper bound came to $1.31.
- **Against the cap.** The cap for everything from the pilot's last condition on is $6.00.
  - Before this run: about $0.55, at most about $1.40.
  - This run, with e's stopped first attempt: about $0.66, at most about $1.50.
  - Total: about $1.21, at most about $2.90.

## Files

- **`<condition>/<bundle>/`.** The sealed Circumstances bundle.
- **`<condition>/condition.json`.** Settings, sampling sent, Kodama commit, stop rule, times and seal check.
- **`trials.csv`, `summary.json`, `summary.md`.** From `recall/analyze.py`.
- **`telemetry.csv`.** Per trial:
  - `path_ms` and `blocking_ms` (the reply path's wait for recall);
  - model calls (reply, check, unmetered);
  - tokens: input, cached, output and reasoning, overall and per provider;
  - `cost_usd` and `cost_usd_upper`.
- **`cost.json`.** Prices, request fields sent, totals per condition and per provider, and the embedding estimate. It comes out the same from the unscrubbed and the scrubbed spans.
- **`estimate.md`.** The cost and time estimate, written before the first trial.
- **`telemetry/<condition>.kodama-traces.jsonl`.** One line per trial with the turn's spans. Before publishing, we removed:
  - Kodama's system prompts, check prompts and tool definitions;
  - the agent and tool descriptions;
  - OpenAI's response and item ids;
  - the encrypted reasoning blobs.

  Conversation messages, outputs, usage, timings and gate verdicts are kept. The unscrubbed dumps are kept outside this repository.
