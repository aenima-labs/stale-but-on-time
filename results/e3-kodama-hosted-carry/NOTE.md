# Experiment 3 control cases on hosted models (gpt-5.6-luna, five trials per case)

**This folder is the control-case run on hosted models.** It covers the ten `asked-carry` cases of pack 1.1.0, conditions a–e, five trials per case: 250 trials, one sealed bundle per condition.

In each case, the scripted agent reply quotes part of one note, and the listener then asks for a detail from the rest of that same note. The cases answer finding 1 of the review: all 30 original recall cases need a note other than the one in play.

**The expectation, committed with the cases before any trial:** lag 1 (b) passes about as often as blocking (c). The same cases on the local model are in `../e3-kodama-carry/`.

**The conditions ran on three days:** a and b on 2026-11-16, d and e on 2026-11-17, and c on 2026-11-24. All five ran on the same stack, image and configuration.

Three attempts are set aside, not reported, in `../e3-kodama-hosted-carry-aborted/`:
- a first attempt at a, stopped by an OpenAI embedding stall;
- a first attempt at c, stopped when the host went to sleep;
- a complete c from 2026-11-17 that lost two trials to the host sleeping. It is replaced by the c reported here.

## What ran

- **Pack.** The paper's pack 1.1.0 (`b96679e`), ported to Kodama with `recall/build_pack.py` (Kodama `92d9f0f`). Only the ten `asked-carry` cases ran.
  - The 40 original cases and the 48 memorome pages are byte-identical after the port.
  - Text mode, lead-in gap at 210 words per minute, same grading as the reported runs.
- **Kodama.** The image of the reported hosted run, `3101c5b` (`sha256:db428e50…`, checked again on 2026-11-24), with its configuration. Eval sessions skip the memorizer.
  - One local stack (Kodama, Postgres, LiveKit), created fresh on 2026-11-16 at 13:12 UTC.
  - All five conditions ran on it. It held only friend prompt version 1, the shipped role file. That was checked again on 2026-11-24, and every trial's settings and spans record that version.
  - Between 2026-11-17 and 2026-11-24 the stack was stopped and its volumes kept. On 2026-11-24 it was started again from the same volumes and image.
- **Models.** The reported hosted run's:
  - **Reply:** gpt-5.6-luna, with no temperature, reasoning effort or output limit sent.
  - **Output checks:** gpt-5.6-luna, `reasoning_effort: none`, `max_output_tokens: 128`.
  - **Embeddings:** text-embedding-3-small.
- **Model check.** On 2026-11-24, before c, OpenAI's responses named the model `gpt-5.6-luna`, service tier `default`, with no snapshot suffix or fingerprint. That is the name the spans of 2026-11-15, 16 and 17 record. All 150 response spans of c record `gen_ai.response.model` `gpt-5.6-luna`. The embedding endpoint answered as text-embedding-3-small, 1,536 dimensions.
- **Runner.** Kodama branch `e3-hosted-run` (none of it pushed):
  - `recall/run.py` at `cb4dc99`. It records the pinned friend version in `condition.json`; trials are otherwise run as at `3101c5b`.
  - `recall/analyze.py` at `005adfb`, which adds the `asked-carry` class to the summary.
  - `recall/telemetry_cost.py` at `fca51fc`, which lists any trial without spans in `cost.json`.
- **Framework.** a, b, d and e were sealed with Circumstances 0.1.0 (`67a63fc`), c with 0.2.0 (`34bf72a`).
  - Between the two, the only code changes are the version string and the command-line program name. Bundles do not record the version.
  - All five bundles verify with 0.2.0.
- **Rebuilt tooling.** An operating-system update between 2026-11-17 and 2026-11-24 cleared the scratch folder. That folder held three tools, kept outside this repository: the stack's compose file, the script that runs a condition with its guards, and the trace scrubber.
  - All three were rebuilt on 2026-11-24 from the versions used for a, b, d and e, with the same services, settings, mounts and guards.
  - The only new element is a variable that picks the stack's volume set.
  - The rebuilt scrubber reproduces three of the scrubbed trace files already in this repository byte for byte. All five trace files here were scrubbed with it on 2026-11-24.
- **Order: a, b, c, d, e by design.** They ran one after another, never in parallel and never alongside another run. Because of the replacement, the c reported here ran last, a week after d and e.
- **Guards, as in the reported hosted run:**
  - Kodama was restarted before each condition;
  - a watchdog followed Kodama's log for queue-consumer errors;
  - the runner stops after three failed trials in a row.

  The watchdog recorded embedding errors during d (below) but never a consumer error. The stop rule did not fire in these five conditions.
- **Probes.** Requests to the embedding endpoint (from the host and from inside the stack) and to the reply model were sent at three points:
  - before the run started (2026-11-16 13:11): answered in 0.3–3 s;
  - before d (2026-11-17 08:16): answered in 0.3–3 s;
  - before c (2026-11-24 12:37): answered in 0–1.4 s, with the host on mains power.

## When (UTC)

| condition | ran | seconds |
|---|---|---|
| a-tool | 2026-11-16 13:12:24–13:35:10 | 1365 |
| b-backthought | 2026-11-16 13:35:15–13:54:39 | 1165 |
| d-blocking-backthought | 2026-11-17 12:02:00–12:26:24 | 1464 |
| e-backthought-tool | 2026-11-17 12:26:28–12:51:59 | 1531 |
| c-blocking | 2026-11-24 12:38:21–12:54:02 | 940 |

**Why c ran on 2026-11-24.**
1. **The first attempt** (2026-11-16 13:54–20:41) was stopped when the host went to sleep with its lid closed, and Docker's DNS failed in its brief wakes.
2. **The second c** (2026-11-17 08:18–12:01) ran to the end, but two trials were lost while the host slept.
   - Counted as failures, they would lower blocking's pass rate for reasons outside the system under test.
   - So c was run again in full. Both earlier attempts are in `../e3-kodama-hosted-carry-aborted/`.
3. **The c reported here** lost no trial. Kodama logged no error of any kind while it ran.

## Results

The figures come from `summary.md`, `summary.json`, `trials.csv` and `telemetry.csv`.
- Intervals are 95% bootstrap intervals over the ten cases, with a case's five trials kept together; errors count as failures.
- Recall wait on the reply path applies to the blocking conditions only.

| condition | passed | errors | templated | recall pass | gold in WM | searched | path ms median / p90 | recall wait on the reply path, ms median / p90 |
|---|---|---|---|---|---|---|---|---|
| a-tool | 50/50 | 0 | 0 | 100% [100, 100] | 0% | 100% | 10453 / 12176 | – |
| b-backthought | 49/50 | 0 | 0 | 98% [94, 100] | 98% | 0% | 6302 / 7158 | – |
| c-blocking | 50/50 | 0 | 0 | 100% [100, 100] | 100% | 0% | 5651 / 7338 | 213 / 307 |
| d-blocking-backthought | 50/50 | 0 | 0 | 100% [100, 100] | 100% | 0% | 6412 / 8603 | 278 / 549 |
| e-backthought-tool | 50/50 | 0 | 0 | 100% [100, 100] | 98% | 2% | 6400 / 8020 | – |

- **The expectation holds.** Lag 1 (b) passed 98%, blocking (c) 100%.
- **The replaced c agrees.** The c of 2026-11-17 passed 48 of 50. All 47 trials it finished before the host slept passed, and so did the one after the wake.
- **Completeness and seals.** Each of the ten cases ran exactly five times in each condition. All five bundles are sealed, and `circumstances verify-bundle` passes for each.
- **The one failure:** b, carry-cat-sleep, trial 5. The reply was "I'm not sure. I don't have anything about where Vellum liked to sleep."
- **Searching.** In e the model searched in 1 trial of 50; the recalled pages carried the answer.
- **c's reply path is shorter than d's.** The medians are 5.7 s against 6.4 s, and the recall waits 213 ms against 278 ms. c ran a week later on the same stack, so time of day and the API's load may account for part of it.

### Embedding errors that cost no trial

- **During d,** Kodama logged four embedding-request errors on the memorome-page consumer at 12:15 and 12:19 UTC ("decode response: context deadline exceeded" and a request error).
- **Why no trial failed.** Those pages were embedded on a later delivery, and every trial waits until its memorome clone is fully embedded before its first turn.
- **During a, b, c and e,** Kodama logged no embedding error. The one exception is a conversation-embedding request cancelled at 13:35:10 on 2026-11-16, when Kodama was restarted between a and b as planned.

### Key matches checked by hand, as asked

| condition | carry passes | rest only on "six" inside a longer word | rest only on "clock" |
|---|---|---|---|
| a-tool | 50 | 0 | 0 |
| b-backthought | 49 | 0 | 0 |
| c-blocking | 50 | 0 | 0 |
| d-blocking-backthought | 50 | 0 | 0 |
| e-backthought-tool | 50 | 0 | 0 |

- **"six"** (carry-hives) can also match "sixty", "sixteen" or "sixth".
- **"clock"** (carry-flat-things) also names the anniversary clock of another note. The flat's own note says she took "the ship's clock and the press".
- **Plural matches.** The only passes that match a key just as the start of a longer word are "headbands" for "headband" (carry-headbands, all five trials in each condition), which is the right answer.

## Cost

Prices are in `cost.json`, as in `../e3-kodama-hosted/`:
- gpt-5.6-luna: $0.20 per million input tokens, $0.02 cached, $1.20 output;
- text-embedding-3-small: $0.02 per million tokens.

| | USD, metered | USD, at most |
|---|---|---|
| a-tool | 0.035 | 0.071 |
| b-backthought | 0.019 | 0.055 |
| c-blocking | 0.019 | 0.055 |
| d-blocking-backthought | 0.019 | 0.055 |
| e-backthought-tool | 0.020 | 0.056 |
| model calls | 0.111 | 0.292 |
| embeddings, estimate | 0.017 | 0.017 |
| **total** | **0.128** | **0.309** |

- **Rounding.** Rows are rounded separately; the totals come from the unrounded figures.
- **Against the estimate.** `estimate.md` said about $0.14, at most about $0.33.
- **The set-aside attempts.** The three in `../e3-kodama-hosted-carry-aborted/` add $0.057 (at most $0.136), embeddings included.
- **Unmetered calls.** 500 check calls stream their answer and record no usage. They are left out of `cost_usd`. `cost_usd_upper` bills each one at the largest metered check input of the run (1,037 tokens) plus 128 output tokens.

## Files

- **`<condition>/<bundle>/`.** The sealed Circumstances bundle.
- **`<condition>/condition.json`.** Contents:
  - the settings, with `prompts.friend: 1`;
  - `friend_prompt_version`;
  - the sampling sent, the Kodama commit and the stop rule;
  - the times and the seal check.
- **`trials.csv`, `summary.json`, `summary.md`.** From `recall/analyze.py`.
- **`telemetry.csv`, `cost.json`.** From `recall/telemetry_cost.py`, as in `../e3-kodama-hosted/`. The cost is the same whether it is computed from the scrubbed spans or the unscrubbed ones.
- **`estimate.md`.** The estimate, written before the first trial.
- **`telemetry/<condition>.kodama-traces.jsonl`.** One line per trial with spans, scrubbed like the reported run. Removed:
  - Kodama's prompts and tool definitions;
  - the agent and tool descriptions;
  - OpenAI's response and item ids;
  - the encrypted reasoning blobs.

  The unscrubbed dumps, the runner and watchdog logs and Kodama's logs are kept outside this repository.
