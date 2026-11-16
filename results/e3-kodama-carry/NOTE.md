# Experiment 3 control cases on the local model (gemma4:e4b, five trials per case)

**This folder is the control-case run on the local model.** It covers the ten `asked-carry` cases of pack 1.1.0, conditions a–e, five trials per case: 250 trials, one sealed bundle per condition.

In each case, the scripted agent reply quotes part of one note, and the listener then asks for a detail from the rest of that same note. The cases answer finding 1 of the review: all 30 original recall cases need a note other than the one in play.

**The expectation, committed with the cases before any trial:** lag 1 (b) passes about as often as blocking (c).

## What ran

- **Pack.** The paper's pack 1.1.0 (`b96679e`), ported to Kodama with `recall/build_pack.py` (Kodama `92d9f0f`). Only the ten `asked-carry` cases ran.
  - The port changed nothing else: the 40 original cases and the 48 memorome pages are byte-identical.
  - Text mode, lead-in gap at 210 words per minute, same grading as the reported runs.
- **Kodama.** The image of the reported hosted run, Kodama `3101c5b` (`sha256:db428e50…`).
  - It ran with run 2's local configuration (`evals/recall/config/local.yaml` of the Kodama repository), on one local stack (Kodama, Postgres, LiveKit) created fresh on 2026-11-16 at 12:16 UTC.
  - Eval sessions skip the memorizer.
- **Models,** all through the host's Ollama 0.40.13:
  - **Reply:** gemma4:e4b (`c6eb396dbd59`), reasoning off. No temperature is sent, so Ollama's defaults apply: temperature 1.0, top_k 64, top_p 0.95. These are recorded in `condition.json`.
  - **Output checks** (greeting, advice, uncited-claim): gemma4:e4b at temperature 0, reasoning off.
  - **Embeddings:** nomic-embed-text (`0a109f422b47`).

  These are run 2's models and settings (`../e3-kodama/`). Run 2 ran on Kodama `52dbd04`; this run uses `3101c5b`.
- **Runner.** Kodama branch `e3-hosted-run`:
  - `recall/run.py` unchanged since `3101c5b`;
  - `recall/analyze.py` at `005adfb`, which adds the `asked-carry` class to the summary;
  - `recall/telemetry_cost.py` at `02aba55`, which counts the local model's calls at no cost.

  None of these commits is pushed.
- **Order: a, b, c, d, e,** one after another, never in parallel, and never alongside a hosted run.
- **Guards, as in the reported hosted run:**
  - Kodama was restarted before each condition;
  - a watchdog followed Kodama's log for queue-consumer errors;
  - the runner stops after three failed trials in a row.

  None of them fired.
- **Smoke.** Two trials (carry-hives, conditions a and c), 2026-11-16 12:17 UTC. Both passed and sealed. They are not in this folder.

## When (UTC), 2026-11-16

| condition | ran | seconds |
|---|---|---|
| a-tool | 12:17:56–12:24:13 | 378 |
| b-backthought | 12:24:15–12:28:57 | 281 |
| c-blocking | 12:28:59–12:33:40 | 281 |
| d-blocking-backthought | 12:33:42–12:38:30 | 288 |
| e-backthought-tool | 12:38:32–12:44:19 | 347 |

## Results

The figures come from `summary.md`, `summary.json`, `trials.csv` and `telemetry.csv`.
- Intervals are 95% bootstrap intervals over the ten cases, with a case's five trials kept together.
- "Gold in WM" means the case's note was in the reply's working memory.
- Recall wait on the reply path applies to the blocking conditions only.

| condition | passed | errors | templated | recall pass | gold in WM | searched | path ms median / p90 | recall wait on the reply path, ms median / p90 |
|---|---|---|---|---|---|---|---|---|
| a-tool | 46/50 | 0 | 0 | 92% [80, 100] | 0% | 100% | 4566 / 5401 | – |
| b-backthought | 50/50 | 0 | 0 | 100% [100, 100] | 100% | 0% | 2752 / 3330 | – |
| c-blocking | 44/50 | 0 | 2 | 88% [68, 100] | 100% | 0% | 2696 / 3323 | 60 / 72 |
| d-blocking-backthought | 48/50 | 0 | 0 | 96% [88, 100] | 100% | 0% | 2875 / 3397 | 68 / 92 |
| e-backthought-tool | 49/50 | 0 | 1 | 98% [94, 100] | 100% | 80% | 4202 / 4916 | – |

- **The expectation holds.** Lag 1 (b) passed every trial, as often as blocking (c, 88%) or more.
- **Completeness and seals.** Each of the ten cases ran exactly five times in each condition. All five bundles are sealed, and `circumstances verify-bundle` passes for each. Every condition is its first attempt.
- **The prompt each trial used.** Every trial's spans record friend prompt version 1, the shipped role file.

### The trials that failed

- **a-tool (4).**
  - carry-headbands, trials 2, 4 and 5: the reply told a different bindery story (the hymnal, or the apprentice Corwin Hale).
  - carry-ferry-wait, trial 3: the reply said the memories did not mention it.
- **c-blocking (6).**
  - carry-walk-days, all five trials. The listener asks "How long did that take her?" right after the lead-in about the coast-path walk. Three replies answered with the six months of the bindery apprenticeship from another page, and the output gate replaced two with its abstention template. The walk's page was in working memory each time.
  - carry-colours, trial 4: the reply was "I'm Kodama, an AI companion, not a person."
- **d-blocking-backthought (2).** carry-walk-days, trials 1 and 3, with the same six-months answer.
- **e-backthought-tool (1).** carry-cat-sleep, trial 2, replaced by the abstention template.

### Key matches checked by hand, as asked

| condition | carry passes | rest only on "six" inside a longer word | rest only on "clock" |
|---|---|---|---|
| a-tool | 46 | 0 | 0 |
| b-backthought | 50 | 0 | 0 |
| c-blocking | 44 | 0 | 0 |
| d-blocking-backthought | 48 | 0 | 0 |
| e-backthought-tool | 49 | 0 | 0 |

- **"six"** (carry-hives) can also match "sixty", "sixteen" or "sixth".
- **"clock"** (carry-flat-things) also names the anniversary clock of another note. The flat's own note says she took "the ship's clock and the press".
- **Plural matches.** Some passes match a key only as the start of a longer word: "headbands" for "headband" (22 trials), "peppermints" for "peppermint" (1). These are the right answer, so they are not counted against the run.

## Problems

None. There were no errors, no consumer errors or recoveries, and no embedding errors. Kodama logged only four "provenance violation" warnings, which are product behaviour.

## Cost

$0: every model ran on the host's Ollama.
- `cost.json` records the local reply calls: 650 calls, 1.52 million input tokens (1.39 million read from Ollama's prompt cache) and 16,112 output tokens.
- The local output checks leave no model span, so they are not counted.

## Files

- **`<condition>/<bundle>/`.** The sealed Circumstances bundle.
- **`<condition>/condition.json`.** Settings, sampling (with Ollama's defaults), Kodama commit, stop rule, times and seal check.
- **`trials.csv`, `summary.json`, `summary.md`.** From `recall/analyze.py`.
- **`telemetry.csv`, `cost.json`.** From `recall/telemetry_cost.py --embed-model nomic-embed-text`. Per trial: path and recall-wait times, local reply calls and tokens, and cost (zero).
- **`telemetry/<condition>.kodama-traces.jsonl`.** One line per trial with the turn's spans.
  - The agent and tool descriptions were removed.
  - The local model's spans carry no system prompt, check prompt or tool definition, so nothing else needed removing.

  The unscrubbed dumps are kept outside this repository.
