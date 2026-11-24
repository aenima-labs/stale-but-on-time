# Experiment 3 prompt check on hosted models: condition a with the bring-up sentence (gpt-5.6-luna, five trials per case)

**This folder answers finding 4 of the review on hosted models.** It holds one eval-only condition, `a2-tool-bringup`, on the 40 original cases with five trials per case: 200 trials, one sealed bundle. The same condition on the local model is `../e3-kodama-toolprompt/`.

A first attempt, on 2026-11-17, was lost after 9 trials to a network outage on the host. It is set aside, not reported, in `../e3-kodama-hosted-toolprompt-aborted/`. This run started again from the start on a new fresh stack.

## The prompt difference it tests

Kodama's friend role file (`backend/internal/prompts/friend.md`, the same at `52dbd04` and `3101c5b`) is a template. The instructions it renders were compared in two ways:
- with the instructions actually sent in the reported hosted run (case `honey-prize`, trial 1, unscrubbed spans);
- with Kodama's own template code rendering the same file.

Both agree byte for byte.

- **b, c and d get identical instructions.** They render the branch for a model without the memorome tools. That branch includes, unconditionally: "When a remark of the listener touches something a recalled page states, you may bring that memory up without being asked. Cite the page first."
- **a and c differ throughout, not by one line.**
  - c has no documentation of memorome_search, memorome_read and memorome_list, and says "You have no search tool in this conversation".
  - c's rules on abstention, on what the person knew or thought, and on glosses point at the recalled pages instead of a search.
  - c adds "Late in a session, a rephrased biographical question still needs a recalled page and cite", and the bring-up line.
- **a and e both have the search tool, and differ by exactly three paragraphs** that `{{if .Recall}}` adds to e:
  1. "The block may have a section headed RECALLED MEMORIES. …", which says what that block is;
  2. "A page under RECALLED MEMORIES is already retrieved. If it states the fact, call cite with its path and speak; …";
  3. the bring-up line.

  a has no recalled block, so the first two have nothing to refer to there. Only the bring-up line is a real confound between a and the other conditions.

**Condition a2-tool-bringup is condition a plus one sentence, worded for the search tool.** The verbatim bring-up line refers to "a recalled page", which a does not have:

> When a remark of the listener touches something the memories may hold, you may search for it and bring that memory up without being asked. Cite the page first.

It is placed where the recall conditions have the bring-up line, after the tool rules. Nothing else changes.
- **How it is applied.** The sentence is added to the friend role file as the `{{else}}` of the existing `{{if .Recall}}`, by Kodama's `recall/friend_bringup.py` (commit `cb4dc99`).
- **How it was checked.** Both versions were rendered with Kodama's template code before any trial.
  - For condition a, the only difference is this hunk:

    ```
    78a79,80
    > When a remark of the listener touches something the memories may hold, you may search for it and bring that memory up without being asked. Cite the page first.
    >
    ```

    It sits after "Late in a session, a rephrased biographical question still needs memorome_search and cite." and before "# Conversation Flow".
  - For conditions c and e, the variant renders byte-identical to the shipped file.
- **How it reaches the model.** Kodama keeps role files as catalog prompt versions, and a presence's settings document pins one.
  - The variant was stored as friend version 2 (md5 `41d140c599914a341300a9151096ff46`; version 1, the shipped file, has md5 `d8d0d5a946959fb4f1f239d66d6dbb1e`). It was stored on a fresh stack before the first settings existed, so every settings document there pins it.
  - The runner refuses the condition unless the settings document pins the version it is given (`--friend-version 2`).
  - `condition.json` records the pin.
- **What reached the model in this run.** The instructions as sent to OpenAI were checked in the unscrubbed spans of all 199 trials that have spans.
  - Every trial's instructions contain the sentence.
  - All 643 spans that name the friend prompt record version 2, and none records version 1.

No product code changed: the image is the reported hosted run's.

## What ran

- **Pack.** The 40 original cases of pack 1.1.0, unchanged from 1.0.0 (Kodama `92d9f0f`, ported from the paper at `b96679e`).
- **Kodama.** The image of the reported hosted run, `3101c5b` (`sha256:db428e50…`, checked again before this run), with that run's configuration. Eval sessions skip the memorizer.
  - Its stack (Kodama, Postgres, LiveKit) was created fresh on 2026-11-24 at 11:11 UTC. Only this condition ran on it.
- **Models.** The reported hosted run's:
  - **Reply:** gpt-5.6-luna, with no temperature, reasoning effort or output limit sent.
  - **Output checks:** gpt-5.6-luna, `reasoning_effort: none`, `max_output_tokens: 128`.
  - **Embeddings:** text-embedding-3-small.
- **Model check.** Before the run, OpenAI's responses named the model `gpt-5.6-luna`, service tier `default`, with no snapshot suffix or fingerprint. That is the name the spans of the hosted runs on 2026-11-15, 16 and 17 record. All 840 response spans of this run record `gen_ai.response.model` `gpt-5.6-luna`. The embedding endpoint answered as text-embedding-3-small, 1,536 dimensions.
- **Runner.** Kodama branch `e3-hosted-run` (none of it pushed):
  - `recall/run.py` at `cb4dc99`, `--friend-version 2`;
  - `recall/analyze.py` at `005adfb`;
  - `recall/telemetry_cost.py` at `fca51fc`, which lists a trial without spans in `cost.json`.
- **Framework.** Circumstances 0.2.0 (`34bf72a`). It sealed and verified this bundle. The earlier runs were sealed with 0.1.0 (`67a63fc`). Between the two, the only code changes are the version string and the command-line program name. Bundles do not record the version.
- **Rebuilt tooling.** An operating-system update between 2026-11-17 and 2026-11-24 cleared the scratch folder. That folder held three tools, kept outside this repository: the stack's compose file, the script that runs a condition with its guards, and the trace scrubber.
  - All three were rebuilt on 2026-11-24 from the versions used for every hosted run on `3101c5b`, with the same services, settings, mounts and guards.
  - The only new element is a variable that picks the stack's volume set.
  - The rebuilt scrubber reproduces three of the scrubbed trace files already in this repository byte for byte.
- **Guards, as in the reported hosted run:**
  - Kodama was restarted before the condition;
  - a watchdog followed Kodama's log for queue-consumer errors;
  - the runner stops after three failed trials in a row.

  The watchdog recorded embedding errors (below) but no consumer error. The stop rule did not fire.
- **Probes.** Just before the run, requests to the embedding endpoint from inside the stack answered in 0–2 s. From the host, the embedding endpoint answered in 0.3 s and the reply model in 2.0 s. The host was on mains power.
- **When.** 2026-11-24 11:11:54–12:30:23 UTC (4,708 s). It ran on its own: no other condition ran at the same time, hosted or local.

## Results

The figures come from `summary.md`, `summary.json` and `trials.csv`.
- Intervals are 95% bootstrap intervals over cases. Errors count as failures.
- The baseline is condition a of the reported hosted run, on the same build and models.
- "Searched on unprompted" counts unprompted trials in which the model called memorome_search.

| | passed | errors | recall pass | asked-continuing | asked-shift | unprompted | abstain (tool) | abstain (in words) | searched on unprompted | path ms median / p90 |
|---|---|---|---|---|---|---|---|---|---|---|
| a2-tool-bringup (this run) | 144/200 | 2 | 68% [52, 83] | 96% | 100% | 8% [0, 20] | 84% | 86% | 2% (1 of 50) | 9098 / 10580 |
| a-tool, reported run (`../e3-kodama-hosted/`, `3101c5b`) | 134/200 | 0 | 65% [47, 81] | 94% | 100% | 0% [0, 0] | 74% | 82% | 0% | 9076 / 10394 |

Templated replies: none here, 2 in the reported run's a. Over all 200 trials, the model searched in 74% here and 75% in the reported a.

**On hosted models, the sentence moved the unprompted class by at most one trial in 50.** As graded, gpt-5.6-luna passed 4 of 50 unprompted trials (8%), against none without the sentence. Read by hand:
- **One pass brings a memory up.** In amb-honey-show trial 1, the model searched, cited the page and said that Tessaly's heather honey won second prize at the Dunmere fair. That is the only unprompted trial with a search.
- **The other three do not.** They are amb-passport trials 2, 3 and 5.
  - Each reply is general advice: check bags and drawers, then contact the passport office or the consulate.
  - None of them searched, cited a page or mentioned Tessaly.
  - They pass because "consulate" is one of the case's keys.

  In the reported run, the passes of this case (c and d, five each) all tell Tessaly's own story of losing her passport.

So 1 of 50 unprompted trials (2%) rests on bringing a memory up. The other three passes rest on a key word in general advice. The grading was not changed: these figures are reported as the evaluator gives them.

**Abstention and asked recall moved up a little, within the intervals.**
- Abstention by tool call is 84% here (42 of 50), against 74% in the reported a.
- Without the two errors below it is 42 of 48 (88%). Both errors are in abs-rosalind-first-word. That case passed its first three trials here and none of its five in the reported a.
- Asked-continuing passed 48 of 50 against 47 of 50.

## Problems: two trials lost to a Wi-Fi outage on the host

Both errors are in the last two trials of abs-rosalind-first-word. Neither comes from Kodama.
1. **The outage.**
   - At 11:26:48.6 UTC the host's Wi-Fi link went down: the system log has "LINK_OFF".
   - Re-association attempts failed until the link came back at 11:28:37.1.
   - The host was awake and on mains power throughout. The power log shows no sleep between 10:12 UTC and the end of the run.
2. **Trial 4** started at 11:26:20. Its reply call failed at 11:28:24, with "dial tcp: lookup api.openai.com on 127.0.0.11:53: no such host". It is recorded as an error.
3. **Trial 5** started at 11:28:24, while lookups still failed.
   - The embedding requests for the 49 pages of its memorome clone each failed five times within a second. Kodama then dropped those pages ("dropping after MaxDeliver", 49 drops at 11:28:24–25).
   - The backfill republished them from 11:28:51, at 32 a minute, but the trial ran out the runner's 180 s limit at 11:31:25 before its first turn.
   - It has no spans: `telemetry.csv` has 199 rows, and `cost.json` lists the trial under `trials_without_spans`.
4. **After the outage,** the next trial started at 11:31:25, and the remaining 160 trials ran without an error.

**The queue consumers stayed up.** Kodama logged 196 embedding handler errors in those seconds. There was no "next message error", "restart error" or "resumed" line. The `3101c5b` fix held.

**Effect on the figures.** Both lost trials belong to the abstain class.
- Recall pass, asked recall and the unprompted class are not affected.
- Abstention counts them as failures: 84%, or 88% without them.

The run was not repeated for them. A full rerun of this condition would take about 80 minutes and cost about $0.14, at most about $0.27.

**The product limit seen before.** A page whose request fails five times is embedded again only when the backfill republishes it. The same exposure appears in `../e3-kodama-hosted-carry-aborted/`. The product was not changed for it.

## Cost

Prices are in `cost.json`, as in `../e3-kodama-hosted/`:
- gpt-5.6-luna: $0.20 per million input tokens, $0.02 cached, $1.20 output;
- text-embedding-3-small: $0.02 per million tokens.

| | USD, metered | USD, at most |
|---|---|---|
| model calls (1,240) | 0.122 | 0.259 |
| embeddings, estimate | 0.013 | 0.013 |
| **total** | **0.136** | **0.272** |

- **Against the estimate.** `estimate.md` said about $0.13, at most about $0.28.
- **The first attempt** in `../e3-kodama-hosted-toolprompt-aborted/` adds $0.008, at most $0.015.
- **Unmetered calls.** 400 check calls stream their answer and record no usage. They are left out of `cost_usd`. `cost_usd_upper` bills each one at the largest metered check input of the run (931 tokens) plus 128 output tokens.

## Files

- **`a2-tool-bringup/<bundle>/`.** The sealed Circumstances bundle; `circumstances verify-bundle` passes.
- **`a2-tool-bringup/condition.json`.** Contents:
  - the settings document, with `prompts.friend: 2`;
  - `friend_prompt_version`;
  - the sampling sent, the Kodama commit and the stop rule;
  - the times and the seal check.
- **`trials.csv`, `summary.json`, `summary.md`.** From `recall/analyze.py`.
- **`telemetry.csv`, `cost.json`.** From `recall/telemetry_cost.py`, as in `../e3-kodama-hosted/`. The cost is the same whether it is computed from the scrubbed spans or the unscrubbed ones.
- **`estimate.md`.** The estimate, written before the first attempt.
- **`telemetry/a2-tool-bringup.kodama-traces.jsonl`.** One line per trial with spans, scrubbed like the reported run. Removed:
  - Kodama's prompts and tool definitions;
  - the agent and tool descriptions;
  - OpenAI's response and item ids;
  - the encrypted reasoning blobs.

  The unscrubbed dump, the runner and watchdog logs and Kodama's log are kept outside this repository.
