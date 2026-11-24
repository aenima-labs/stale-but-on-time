# Experiment 3 prompt check on the local model: condition a with the bring-up sentence (gemma4:e4b, five trials per case)

**This folder answers finding 4 of the review on the local model.** It holds one eval-only condition, `a2-tool-bringup`, on the 40 original cases with five trials per case: 200 trials, one sealed bundle. The same condition on hosted models is `../e3-kodama-hosted-toolprompt/`.

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
  - `condition.json` records the pin, and every trial's spans record `kodama.prompt.version` 2 for the friend prompt.

No product code changed: the image is the reported hosted run's.

## What ran

- **Pack.** The 40 original cases of pack 1.1.0, unchanged from 1.0.0 (Kodama `92d9f0f`, ported from the paper at `b96679e`).
- **Kodama.** The image of the reported hosted run, `3101c5b` (`sha256:db428e50…`).
  - It ran with run 2's local configuration (`evals/recall/config/local.yaml`).
  - Its stack (Kodama, Postgres, LiveKit) was created fresh on 2026-11-16 at 12:44 UTC. Only this condition ran on it.
- **Models,** through the host's Ollama 0.40.13:
  - **Reply:** gemma4:e4b, reasoning off. Ollama's defaults apply: temperature 1.0, top_k 64, top_p 0.95.
  - **Output checks:** gemma4:e4b at temperature 0.
  - **Embeddings:** nomic-embed-text.
- **Runner.** Kodama branch `e3-hosted-run` (none of it pushed):
  - `recall/run.py` at `cb4dc99`;
  - `recall/analyze.py` at `005adfb`;
  - `recall/telemetry_cost.py` at `02aba55`.
- **Guards.** As in the reported hosted run: a Kodama restart before the condition, the queue-consumer watchdog and the stop rule. None fired.
- **When.** 2026-11-16 12:45:21–13:11:24 UTC (1,563 s). It ran after the control cases on the local model (`../e3-kodama-carry/`), and never alongside a hosted run.

## Results

| | passed | errors | recall pass | asked-continuing | asked-shift | unprompted | abstain (tool) | abstain (in words) | searched on unprompted | path ms median / p90 |
|---|---|---|---|---|---|---|---|---|---|---|
| a2-tool-bringup (this run, `3101c5b`) | 106/200 | 0 | 64% [48, 79] | 90% | 92% | 10% | 20% | 46% | 16% | 4464 / 5265 |
| a-tool, run 2 (`../e3-kodama/`, `52dbd04`) | – | 0 | 63% [48, 78] | 88% | 92% | 10% | 32% | 36% | 14% | 6110 / 7377 |

Intervals are 95% bootstrap intervals over cases. Templated replies: 6% here, 6.5% in run 2.

**On the local model, the sentence did not change the unprompted class.** gemma4:e4b passed 10% of the unprompted trials, as without it, and searched in 16% of them against 14% in run 2. It passed 5 of 50: amb-flood twice, amb-saffron twice, amb-jumper once.

**The baseline is from another build.**
- Run 2's condition a ran on Kodama `52dbd04`, not `3101c5b`. Between them are product changes that touch the local model:
  - `19340b1`: the Ollama adapter asks again when Ollama's parser drops a reply. It fired once in this run.
  - `53f6e2f`: the greeting and advice checks stop once their verdict is decided.
- The reply path is also faster here (4.5 s against 6.1 s median), which may also reflect the host or the Ollama version.
- So the differences in abstention (20% against 32% by tool call, 46% against 36% in words) cannot be put on the sentence. A run of condition a on `3101c5b` with the local model would give a same-build baseline (200 trials, about 25 minutes, no API cost). It was not part of this request.

## Problems

None. There were no errors and no consumer errors or recoveries. Kodama logged 46 "provenance violation" warnings, which are product behaviour, and one Ollama re-ask.

## Cost

$0: every model ran on the host's Ollama. `cost.json` records 610 local reply calls, 1.52 million input tokens (1.37 million from Ollama's prompt cache) and 17,506 output tokens.

## Files

- **`a2-tool-bringup/<bundle>/`.** The sealed Circumstances bundle; `circumstances verify-bundle` passes.
- **`a2-tool-bringup/condition.json`.** Settings document (with `prompts.friend: 2`), `friend_prompt_version`, sampling, Kodama commit, stop rule, times and seal check.
- **`trials.csv`, `summary.json`, `summary.md`.** From `recall/analyze.py`.
- **`telemetry.csv`, `cost.json`.** From `recall/telemetry_cost.py --embed-model nomic-embed-text`.
- **`telemetry/a2-tool-bringup.kodama-traces.jsonl`.** One line per trial with the turn's spans.
  - The agent and tool descriptions were removed.
  - The local model's spans carry no system prompt, check prompt or tool definition.

  The unscrubbed dump is kept outside this repository.
