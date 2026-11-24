# Experiment 3 prompt check on the local model: same-build baseline of condition a (gemma4:e4b, five trials per case)

**This folder is the baseline for `../e3-kodama-toolprompt/`.** It holds condition a as shipped, `a-tool`, on the 40 original cases with five trials per case: 200 trials, one sealed bundle.
- It ran on the build that `../e3-kodama-toolprompt/` ran on (Kodama `3101c5b`), with the same local configuration and runner.
- The only intended difference between the two folders is the bring-up sentence.
- The earlier baseline for that comparison, run 2's condition a in `../e3-kodama/`, ran on Kodama `52dbd04`.

## What differs from `../e3-kodama-toolprompt/`

- **The friend role file.** This run uses the shipped one, friend prompt version 1 (md5 `d8d0d5a946959fb4f1f239d66d6dbb1e`).
  - The stack was fresh and held no other version.
  - The runner was told `--friend-version 1` and refuses the condition otherwise.
  - `condition.json` and every trial's settings record the pin.
  - `../e3-kodama-toolprompt/` used version 2, which is version 1 plus one sentence after the tool rules:

    > When a remark of the listener touches something the memories may hold, you may search for it and bring that memory up without being asked. Cite the page first.

  - Rendered for condition a, the two versions differ by that sentence only (hunk `78a79,80`); `../e3-kodama-toolprompt/NOTE.md` has the full comparison.
- **Ollama.** The host's Ollama is now 0.40.16; `../e3-kodama-toolprompt/` ran on 0.40.13.
  - The model files are the same: gemma4:e4b `c6eb396dbd59` and nomic-embed-text `0a109f422b47`. These are the digests recorded in `../e3-kodama-carry/`, which ran just before `../e3-kodama-toolprompt/` on 2026-11-16.
  - The sampling Kodama reads from Ollama is also the same: temperature 1.0, top_k 64, top_p 0.95, recorded in `condition.json`.
- **The date.** 2026-11-24 here, 2026-11-16 there.

## What ran

- **Pack.** The 40 original cases of pack 1.1.0, unchanged from 1.0.0 (Kodama `92d9f0f`, ported from the paper at `b96679e`). These are the same 40 `--case` arguments as in `../e3-kodama-toolprompt/`.
- **Kodama.** The image of the reported hosted run, `3101c5b` (`sha256:db428e50…`).
  - It ran with run 2's local configuration (`evals/recall/config/local.yaml`).
  - Its stack (Kodama, Postgres, LiveKit) was created fresh on 2026-11-24 at 12:59 UTC. Only this condition ran on it.
- **Models,** through the host's Ollama 0.40.16:
  - **Reply:** gemma4:e4b, reasoning off. Ollama's defaults apply: temperature 1.0, top_k 64, top_p 0.95.
  - **Output checks:** gemma4:e4b at temperature 0.
  - **Embeddings:** nomic-embed-text.
- **Runner.** Kodama branch `e3-hosted-run` (none of it pushed):
  - `recall/run.py` at `cb4dc99`, `--friend-version 1`;
  - `recall/analyze.py` at `005adfb`;
  - `recall/telemetry_cost.py` at `fca51fc`.
- **Framework.** Circumstances 0.2.0 (`34bf72a`) sealed and verified this bundle. `../e3-kodama-toolprompt/` was sealed with 0.1.0 (`67a63fc`). Between the two, the only code changes are the version string and the command-line program name. Bundles do not record the version.
- **Rebuilt tooling.** An operating-system update between 2026-11-17 and 2026-11-24 cleared the scratch folder. It held two of the tools used here, kept outside this repository: the local stack's compose file and the script that runs a condition with its guards.
  - Both were rebuilt on 2026-11-24 from the versions used for `../e3-kodama-toolprompt/`.
  - The Kodama service's environment is identical to the repository's `evals/recall/docker-compose.yml`. The only new element is a variable that picks the stack's volume set.
  - Kodama's startup lines naming its model providers are identical to those of `../e3-kodama-toolprompt/`.
- **Guards.** As in the reported hosted run: a Kodama restart before the condition, the queue-consumer watchdog and the stop rule. None fired.
- **When.** 2026-11-24 12:59:51–13:26:01 UTC (1,570 s). It ran after the hosted add-on runs of the same day had finished and their stack was stopped. Ollama was checked every 20 seconds during the run, and it had no model loaded other than gemma4:e4b and nomic-embed-text.

## Results

The figures come from `summary.md`, `summary.json` and `trials.csv`.
- Intervals are 95% bootstrap intervals over cases. There were no errors.
- "Searched on unprompted" counts unprompted trials in which the model called memorome_search.

| | passed | recall pass | asked-continuing | asked-shift | unprompted | abstain (tool) | abstain (in words) | searched on unprompted | templated | path ms median / p90 |
|---|---|---|---|---|---|---|---|---|---|---|
| a-tool, this run (`3101c5b`, friend v1) | 109/200 | 65% [49, 80] | 84% | 98% | 14% [0, 28] | 22% [6, 42] | 40% | 22% | 13 | 4458 / 5231 |
| a2-tool-bringup (`../e3-kodama-toolprompt/`, `3101c5b`, friend v2) | 106/200 | 64% [48, 79] | 90% | 92% | 10% [0, 20] | 20% [2, 42] | 46% | 16% | 12 | 4464 / 5265 |
| a-tool, run 2 (`../e3-kodama/`, `52dbd04`) | 111/200 | 63% [48, 78] | 88% | 92% | 10% [4, 16] | 32% [6, 58] | 36% | 14% | 13 | 6110 / 7377 |

**On the same build, the sentence did not raise the unprompted class on the local model.**
- Without the sentence, gemma4:e4b passed 7 of 50 unprompted trials (amb-saffron three times, amb-piano and amb-swim twice each) and searched in 11.
- With it, it passed 5 (amb-flood twice, amb-saffron twice, amb-jumper once) and searched in 8.
- The intervals overlap almost entirely.

**Every unprompted pass in both runs brings a memory up.** Each passing trial either searched or had the gold page in working memory. None rests on a key word in general advice.

**The differences that `../e3-kodama-toolprompt/` could not attribute come from the build, not the sentence.** On the same build, condition a without the sentence:
- abstains by tool call in 22% of trials, against 20% with it and 32% in run 2;
- has a median reply path of 4.5 s, against 4.5 s with it and 6.1 s in run 2.

**Asked recall.** Asked-continuing passed 84% here and 90% with the sentence; asked-shift 98% and 92%. Overall recall pass is 65% against 64%.

## Problems

None. There were no errors, and no consumer errors or recoveries. Kodama logged 42 "provenance violation" warnings, which are product behaviour (46 in `../e3-kodama-toolprompt/`). It also asked Ollama again once after Ollama's parser dropped a reply (once there too).

## Cost

$0: every model ran on the host's Ollama. `cost.json` records 624 local model calls, 1.54 million input tokens (1.38 million from Ollama's prompt cache) and 17,665 output tokens.

## Files

- **`a-tool/<bundle>/`.** The sealed Circumstances bundle; `circumstances verify-bundle` passes.
- **`a-tool/condition.json`.** Contents:
  - the settings document, with `prompts.friend: 1`;
  - `friend_prompt_version`;
  - the sampling, the Kodama commit and the stop rule;
  - the times and the seal check.
- **`trials.csv`, `summary.json`, `summary.md`.** From `recall/analyze.py`.
- **`telemetry.csv`, `cost.json`.** From `recall/telemetry_cost.py --embed-model nomic-embed-text`. The figures are the same whether they are computed from the scrubbed spans or the unscrubbed ones.
- **`telemetry/a-tool.kodama-traces.jsonl`.** One line per trial with the turn's spans.
  - The agent and tool descriptions were removed.
  - The local model's spans carry no system prompt, check prompt or tool definition.

  The unscrubbed dump, the runner log and Kodama's log are kept outside this repository.
