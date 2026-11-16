# Experiment 3 on hosted models: first hosted run, on Kodama `70dcabb`, without condition e (gpt-5.6-luna, five trials per case)

**This folder is the first hosted run, on Kodama `70dcabb`. It is not the run the paper reports. Conditions a–d are complete; it has no condition e.**

- **Design:** 40 cases × 5 trials per case × 5 conditions, as in run 2.
- **a–d:** all 800 trials are here, in one sealed bundle per condition.
- **e:** both attempts were stopped by a Kodama defect, so this folder has no e bundle (see Problems).
- **Afterwards:** Anton decided to fix the product and rerun all five conditions. The fix is Kodama `3101c5b`. The rerun is the hosted run the paper reports, in `../e3-kodama-hosted/`. This folder is kept for disclosure.

Other folders:
- `../e3-kodama-hosted/`: the reported hosted run on `3101c5b`, all five conditions.
- `../e3-kodama-hosted-luna/`: the pilot, one trial per case (200 trials).
- `../e3-kodama-hosted-aborted/`: the two stopped attempts of e from this run.
- `../e3-kodama-hosted-aborted-3101c5b/`: the reported run's first attempt at e, stopped by a Docker Desktop restart.
- `../e3-kodama-hosted-luna-aborted/`: the pilot's failed attempts of e.

## What ran

- **Pack.** `evals/packs/kodama-async-recall`: 40 cases, unchanged since run 2 (`../e3-kodama/`).
  - Text mode, lead-in gap at 210 words per minute, same grading.
  - Five trials per case, the pack's own count, as in run 2.
- **Kodama.** Commit `70dcabb` (branch `e3-telemetry-bridge`), the same Docker image as the pilot.
  - One local stack (Kodama, Postgres, LiveKit) with its own volumes, created fresh on 2026-11-15 at 10:11 UTC.
  - The pilot's third attempt at e and the smoke below ran on that stack just before this run.
  - Eval sessions skip the memorizer (`pipeline.skip_eval_memorizer`).
- **Runner.** Kodama repository, branch `e3-hosted-run` at `944b6a3`: `recall/run.py`, `recall/analyze.py` and `recall/telemetry_cost.py`.
  - Compared with the pilot's runner, `run.py` gains only a stop rule (see Guards).
  - Trials and grading are unchanged.
- **Models.** Kodama's production defaults (`config/gcp.yaml`):
  - reply: gpt-5.6-luna (OpenAI Responses API);
  - output checks (greeting, advice, uncited-claim): gpt-5.6-luna;
  - embeddings: text-embedding-3-small.
- **Request fields sent.** Recorded from the requests themselves (`otel.instruments.openai.http`).
  - Reply: no temperature, reasoning effort or output limit, so OpenAI's defaults apply.
  - Checks: `reasoning_effort: none`, `max_output_tokens: 128`.
- **Order.** The conditions ran one after another, never in parallel.
- **Guards.** These were added after the pilot's failed attempts. The product is unchanged.
  1. **A fresh Kodama process for each condition.** Kodama was restarted before each condition (same volumes), so every condition began with new embedding consumers and HTTP connections.
  2. **A watchdog.** It stopped the runner on the second "embed consumer: next message error" in Kodama's log.
  3. **A stop rule in the runner.** The runner stops after three trials in a row fail or time out (`--stop-after 3`, recorded in `condition.json`).
  4. **No sleep.** The machine was kept awake (`caffeinate`).

  A stopped condition writes no bundle.
- **Smoke.** On the same stack, 2026-11-15 10:28–10:30 UTC: 5 trials of e, all passed, no embedding errors. It is not in this folder.

## Differences from run 2 and from the pilot

- **From run 2.**
  - Models: run 2 ran locally, gemma4:e4b at temperature 1.0 for the reply and the checks, with nomic-embed-text embeddings.
  - Kodama commits after run 2's `52dbd04`: listed in the pilot's NOTE.md.
  - Request capture is on.
  - Trials per case are the same: five.
- **From the pilot.**
  - Five trials per case instead of one.
  - The runner's stop rule and the guards above.
  - A different day: the pilot's a–d ran on 2026-11-14.

## When (UTC), 2026-11-15

| condition | ran | seconds | trials |
|---|---|---|---|
| a-tool | 10:31:18–12:07:25 | 5767 | 200 |
| b-backthought | 12:08:00–13:38:27 | 5427 | 200 |
| c-blocking | 13:38:33–15:09:05 | 5431 | 200 |
| d-blocking-backthought | 15:09:11–16:42:39 | 5608 | 200 |
| e-backthought-tool, attempt 1 | 16:42:43–17:21:14, stopped | – | 76, no bundle |
| e-backthought-tool, attempt 2 | 17:24:46–17:51:46, stopped | – | 52, no bundle |

Trials took 27–29 s each, against 23.7 s in the pilot, so a–d took 6.2 hours. The estimate (`estimate.md`) assumed 6.6 hours for all five conditions.

## Results (a–d)

The figures come from `summary.md`, `trials.csv` and `telemetry.csv`.
- Intervals are 95% bootstrap intervals over cases, with a case's five trials kept together.
- Recall wait on the reply path applies to the blocking conditions only.

| condition | passed | errors | templated | recall pass | pilot | run 2 | path ms median / p90 | recall wait on the reply path, ms median / p90 |
|---|---|---|---|---|---|---|---|---|
| a-tool | 139/200 | 0 | 3 | 65% [48, 81] | 67% | 63% | 9404 / 10753 | – |
| b-backthought | 106/200 | 0 | 12 | 41% [23, 59] | 40% | 29% | 5888 / 6757 | – |
| c-blocking | 189/200 | 0 | 2 | 97% [90, 100] | 97% | 84% | 6148 / 7179 | 368 / 439 |
| d-blocking-backthought | 189/200 | 0 | 1 | 96% [89, 100] | 97% | 85% | 6397 / 7656 | 376 / 452 |

- **Coherence.** One Kodama commit (`70dcabb`), one image, one configuration, one stack and one runner commit (`944b6a3`). Each condition has its own settings document (`settings_id` in `condition.json`).
- **Completeness.** Each of the 40 cases ran exactly five times in each of a–d.
- **Seals.** All four bundles are sealed, and `circumstances verify-bundle` passes for each.
- **Attempts.** Every condition here is its first attempt.
- **Recall wait.** It is higher than in the pilot (295 and 289 ms) and in run 2 (97 ms). Here the query is embedded by OpenAI on the reply path; in run 2 a local model embedded it.

### No reported trial ran while an embedding consumer was down

1. **Every trial started with its memorome clone fully embedded.**
   - All 40 cases set `wait_embedded: true`, so before its first turn each trial waits until every page of its memorome clone has an embedding.
   - If that does not happen within 180 s, the trial fails with an error.
   - a–d have 0 errors in 800 trials.
2. **Kodama's log shows no consumer error inside a–d.** The log was saved in full; it is not in this repository.
   - Inside the time windows of a–d it has no "embed consumer: next message error" line.
   - The watchdog never fired during a–d.
   - Its one embedding error came at 15:09:05.591 UTC. That was 0.5 s after c's last turn, when Kodama was being restarted for d, so the shutdown cancelled the request.
3. **The consumer failures come only from the e attempts.** Each one began inside a stopped attempt, and neither attempt is reported. Kodama was restarted before each condition, so every condition began with new consumers.

### Templated replies

The output gate replaced 18 replies with its abstention template. This is product behaviour, not a run problem.
- **a:** amb-flood, amb-honey-show and amb-swim.
- **b:** 12 replies in 10 cases. abs-car and abs-coat-colour twice each; abs-rosalind-university, amb-passport, honey-prize, lighthouse-pet, regret, shift-dog-name, shift-lighthouse-steps and shift-shop-name once each.
- **c:** abs-chess-opening twice.
- **d:** abs-chess-opening once.

## Problems, and what was done

### 1. Condition e was stopped twice by a Kodama defect

Details are in `../e3-kodama-hosted-aborted/NOTE.md`.

| | ran (UTC) | trials | how it stopped |
|---|---|---|---|
| attempt 1 | 16:42–17:21 | 76 | "nats: consumer deleted" |
| attempt 2 | 17:24–17:51 | 52 | "no heartbeat received", with the conversation consumer already deleted from the NATS store |

In both attempts the watchdog stopped the runner.

**The defect:**
- Kodama `70dcabb` declares its NATS consumers without a durable name, so the NATS server inside Kodama deletes one that goes about 5 s without a pull request.
- Kodama's consumer loop never fetches a deleted consumer again.

**Not known:** what leaves the consumer without a pull request.

**It looks specific to e.** e's two attempts here stopped after 76 and 52 trials. Conditions a–d ran 960 hosted trials, pilot and this run, without a stop.

**What was done:**
- No third attempt was started on `70dcabb`, and the product was not changed during this run.
- Afterwards, Anton decided to fix the product and rerun all five conditions. Kodama `3101c5b` makes every consumer durable, and its consumer loop fetches or recreates the consumer after an error.
- The rerun is `../e3-kodama-hosted/`. Its NOTE.md lists what changed from `70dcabb`.

### 2. Unmetered check calls

The greeting and advice checks stream their answer, and the request capture records no usage for a streamed response.
- That is 1,582 calls: two per trial, minus 18.
- They are counted in `unmetered_calls` and left out of `cost_usd`.
- `cost_usd_upper` bills each one at the largest metered check input of the run (972 tokens) plus 128 output tokens.

### 3. Embedding queue churn

Kodama's backfill republishes up to 32 unembedded rows a minute. It did so in most minutes of every condition, the e attempts included. This is normal for Kodama: it republishes rows waiting to be embedded, and the stream drops duplicates.

## Cost

Prices are in `cost.json`:
- gpt-5.6-luna: $0.20 per million input tokens, $0.02 cached, $1.20 output;
- text-embedding-3-small: $0.02 per million tokens.

The source is https://developers.openai.com/api/docs/pricing, read 2026-11-13.

| | USD |
|---|---|
| a–d model calls, metered | 0.368 |
| a–d model calls, upper bound (unmetered checks billed in full) | 0.918 |
| a–d embeddings, estimate | 0.054 |
| **a–d total** | **0.421 (at most 0.972)** |
| stopped e attempts, model calls, metered (76 + 52 trials) | 0.087 |

The estimate before the run, for all 1,000 trials, was about $0.57 and at most about $1.26 (`estimate.md`). a–d stayed within their share of it.

## Files

- **`<condition>/<bundle>/`.** The sealed Circumstances bundle.
- **`<condition>/condition.json`.** Settings, sampling sent, Kodama commit, stop rule, times and seal check.
- **`trials.csv`, `summary.json`, `summary.md`.** From `recall/analyze.py`.
- **`telemetry.csv`.** Per trial:
  - `path_ms` and `blocking_ms` (the reply path's wait for recall);
  - model calls (reply, check, unmetered);
  - tokens: input, cached, output and reasoning, overall and per provider;
  - `cost_usd` and `cost_usd_upper`.
- **`cost.json`.** Prices, request fields sent, totals per condition and per provider, and the embedding estimate.
- **`estimate.md`.** The cost and time estimate, written before the first trial.
- **`telemetry/<condition>.kodama-traces.jsonl`.** One line per trial with the turn's spans. Before publishing, we removed:
  - Kodama's system prompts, check prompts and tool definitions;
  - the agent and tool descriptions;
  - OpenAI's response and item ids;
  - the encrypted reasoning blobs.

  Conversation messages, outputs, usage, timings and gate verdicts are kept. The unscrubbed dumps are kept outside this repository.
