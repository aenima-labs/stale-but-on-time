# Stale but on Time

Paper and experiments: what asynchronous (never-wait) memory recall costs a
conversational agent. Target venue: TMLR.

- Manuscript: `paper/main.tex` → `paper/main.pdf` (TMLR style, preprint option).
  The compiled PDF of the latest draft is committed here and attached to the release.
- Every measured result in the manuscript (numbers, tables, data figures) is generated
  from the result files by `src/make_numbers.py` and `src/figures.py`. Descriptions of
  the set-up are typed: model sizes, counts of cases and notes, the number of replies
  that were read against their grades, and the assumed speaking rates.

## Layout

| Path | What it is |
|---|---|
| `pack-src/tessaly.yaml` | Source of the fictional memorome (48 notes) and the 50 cases: five classes of ten. The control class `asked-carry` (answer in the note already in play) was added in pack 1.1.0 on 16 November, after an independent review, and committed before any trial ran on it |
| `pack/`, `fixtures/` | Generated Circumstances pack (format v4) and memorome fixture |
| `src/retrieval.py` | Hybrid BM25 + embedding retriever with reciprocal rank fusion |
| `src/e1_replay.py`, `src/e1_analyze.py` | Experiment 1: staleness replay on LoCoMo, analysis, timing model |
| `src/subject.py`, `src/e2_run.py`, `src/e2_analyze.py` | Experiment 2: reference agent (six memory conditions), runner, analysis |
| `src/providers.py`, `src/hosted_check.py` | Model providers behind one interface (local Ollama; hosted OpenAI, Gemini on Vertex, Anthropic) and a one-trial connectivity check |
| `src/telemetry.py`, `src/telemetry_summary.py` | OpenTelemetry tracing of every trial; per-condition summary of latency, tokens, calls and cost |
| `pricing/prices.yaml`, `src/pricing.py`, `src/estimate.py` | Dated price table with sources; run estimate, confirmation, estimate-vs-actual |
| `infra/gcp/`, `src/gcp_job.py` | Terraform, image and task for running Experiment 2 as a Cloud Run GPU job |
| `tests/` | Unit tests (`uv run inv e2.test`) |
| `src/e3_analyze.py` | Experiment 3: analysis of the pack run against the product (bundles in `results/e3-kodama`, first run in `results/e3-kodama-run1`, run on hosted models in `results/e3-kodama-hosted`) |
| `src/figures.py`, `src/make_numbers.py` | Figures, table bodies and number macros for the paper |
| `results/` | Per-utterance retrievals (E1), sealed run bundles (E2: `e2` main run on the 50 cases, `e2-run1` first run on the 40 original cases, `e2-think` reasoning on, `e2-qwen3` second model, `e2-anthropic` hosted model; the last three on the 40 original cases), summaries, samples for a human audit, provenance notes (`*_NOTES.md`) |
| `tasks/`, `src/fetch_data.py` | [Invoke](https://www.pyinvoke.org) tasks for every step; data download |

"Memorome", in file names, code and result events, is the term of Xiao et al. (2026),
[Memory is Not Search](https://www.engramme.com/index/memory-is-not-search), Section 2,
for the whole collection of one person's memories. Here it is the store of 48 notes.

## Data

| What | Where | Needed for |
|---|---|---|
| Per-utterance retrievals (E1), sealed run bundles with every trial (E2), summaries, audit sample | in git, `results/` (~17 MB) | Re-running the analysis, figures and the paper. No model needed. |
| Embedding cache for LoCoMo (`data/cache`, ~180 MB archive) | [Release `v0.1.0`](https://github.com/aenima-labs/stale-but-on-time/releases/tag/v0.1.0), fetched by `inv data.fetch` | Skipping the ~12 min embedding step of E1. Optional; regenerated if absent. |
| LoCoMo conversations | Downloaded from its authors by `inv data.fetch` | E1 replay. CC BY-NC 4.0, not redistributed here. |
| Latest compiled paper | `paper/main.pdf` (also attached to the release) | Reading. |

## Reproduce

Requires `uv`, a local [Ollama](https://ollama.com) with `nomic-embed-text`,
`gemma4:e4b` and (for the second-model run) `qwen3:8b`, and `tectonic`. The [Circumstances](https://github.com/aenima-labs/circumstances)
framework is pinned by commit in `pyproject.toml` and installed by `uv sync`.

Every step is an [Invoke](https://www.pyinvoke.org) task; `uv run inv --list` shows them all.

Analysis, figures and paper only (no Ollama needed):

```bash
uv sync
uv run inv analyze
```

Everything from scratch (about 35 minutes: E1 replay ~12 min without the cache, E2 1,500 trials ~22 min):

```bash
uv sync
uv run inv reproduce
```

Tasks are grouped by experiment: `data.fetch`; `e1.replay`, `e1.analyze`; `e2.build-pack`,
`e2.run`, `e2.estimate`, `e2.summary`, `e2.analyze`, `e2.scrub-paths`, `e2.test`;
`gcp.estimate`, `gcp.plan`, `gcp.run`, `gcp.destroy`; `paper.figures`, `paper.numbers`, `paper.build`,
`paper.anon`. `reproduce` runs them in that order, and each can be run alone.
Extra options go through `--args`, for example
`uv run inv e2.run --args="--think --out results/e2-think"`.

`reproduce` runs the main E2 run only. The three further runs of Section 6.3 are
separate, because the first is slow and the third costs money:

```bash
uv run inv e2.run --args="--think --out results/e2-think"
```

```bash
uv run inv e2.run --args="--model qwen3:8b --out results/e2-qwen3"
```

```bash
uv run inv e2.run --args="--provider anthropic --embed-provider openai --out results/e2-anthropic"
```

The reasoning run takes about 2.7 hours on a laptop, the second-model run about 20
minutes, and the hosted run about 50 minutes and 3.5 US dollars (it prints an estimate
and asks before it starts; `results/e2-anthropic_NOTES.md` lists how it differs from
the local runs). `e2.analyze` analyses all four runs and the cloud timing pass
(`src/e2_analyze.py --run <name>`). `results/e2-cloudrun-l4-timing` is that pass: one
trial per case on a Cloud Run job with an NVIDIA L4, used only for the timings of
Section 8 (`results/e2-cloudrun-l4-timing_NOTES.md`).

The analysis applies two corrections to the sealed grades, to every run alike: a key
must begin a word (the key "Mori" had matched inside "memories"), and a reply that
left out the JSON reply format is read as text, so that a refusal in words counts as
an abstention. `<run>_trials.csv` keeps the sealed grade as `passed_sealed` and marks
each changed trial as `regraded`; only the hosted run has any.

The first correction also applies to Experiment 3. The product's evaluation matched
keys anywhere in the reply, so `src/e3_analyze.py` requires a key to begin a word in
every run against the product. Only the lag-1 condition of the runs on hosted models
changes (4 trials in the reported run, 6 in the first hosted run, 1 in the pilot);
`results/e3_regraded.csv` lists them. The `trials.csv`, `summary.*` and `NOTE.md`
files inside the `results/e3-kodama*` folders were written by the product's evaluation
code and keep the sealed grades, so they show 39% to 41% for that condition where the
paper reports 37%.

A rerun will not reproduce the stored trials bit for bit; the sealed bundles in
`results/e2`, `results/e2-run1`, `results/e2-think`, `results/e2-qwen3` and
`results/e2-anthropic` are the record the paper reports. `results/e2` is the main run
(16 November, pack 1.1.0, 50 cases). `results/e2-run1` is the first full run of the
same setting (10 November, pack 1.0.0, 40 cases, other seeds); the paper gives its
results in the appendix as a repeat. Part of the reasoning run shared the GPU with another
process; `results/e2-think_NOTES.md` gives the window, and `src/make_numbers.py`
leaves those trials out of every latency figure.

Experiment 3 runs the same cases against the product itself, which this repository
does not contain. Its sealed bundles and trial tables are in `results/e3-kodama`
(the reported run on a local model), `results/e3-kodama-run1` (the first run,
kept for disclosure) and `results/e3-kodama-hosted` (the run on the product's
hosted models, with a trace of every trial under `telemetry/` and the cost in
`cost.json`); `uv run inv e2.analyze-product` re-analyses them without the product.
`results/e3_audit_sample.csv` is the sample of the local run read against the grades.

The hosted run has a history, told in the `NOTE.md` of each folder:

| Folder | What it holds |
|---|---|
| `results/e3-kodama-hosted-luna` | The pilot, one trial per case |
| `results/e3-kodama-hosted-luna-aborted` | The pilot's two failed attempts at its last condition |
| `results/e3-kodama-hosted-run1` | The first full run: four conditions, 800 trials |
| `results/e3-kodama-hosted-aborted` | That run's two stopped attempts at the last condition, the analysis of the defect in the product that stopped them, and local checks of the fix |
| `results/e3-kodama-hosted` | The reported run, all five conditions on the fixed product |
| `results/e3-kodama-hosted-aborted-3101c5b` | An attempt of the reported run that ended when Docker restarted on the host |

Later runs, added after a review of a draft (pack 1.1.0), on the product version of
the hosted run:

| Folder | What it holds |
|---|---|
| `results/e3-kodama-carry` | The ten control cases in all five conditions, local model |
| `results/e3-kodama-toolprompt` | The sixth condition (search tool plus one sentence), local model |
| `results/e3-kodama-toolprompt-baseline` | The search tool as shipped on the same product version, local model, for comparison with the sixth condition |
| `results/e3-kodama-hosted-carry` | The ten control cases in all five conditions, hosted models; the conditions ran on three days |
| `results/e3-kodama-hosted-carry-aborted` | Three attempts of that run that are not reported: one stopped by stalled embedding requests, two affected by the host going to sleep |
| `results/e3-kodama-hosted-toolprompt` | The sixth condition, hosted models |
| `results/e3-kodama-hosted-toolprompt-aborted` | Its first attempt, stopped after nine trials by a network failure |

Exploratory runs against the product, kept for the record and **not reported in
the paper**: spoken trials with one trial per case (`results/e3-kodama-voice`,
`results/e3-kodama-voice-dtx`, and `results/e3-kodama-voice-aborted`, a run
stopped for the reason in its `NOTE.md`), and two development runs on shortening
the wait before the first audio (`results/e4-kodama-clauses`,
`results/e4-kodama-checks`). Their numbers have not been audited. The `.wav`
files are synthetic speech of the fictional cases.
`src/e2_run.py` writes the pack path into each bundle as the relative `pack`, and
`src/scrub_paths.py` does the same for bundles made earlier (it re-seals them and
verifies the seal): `uv run inv e2.scrub-paths --dirs=results/e2`.

## Telemetry, estimates and other hardware

Runs made since the telemetry was added carry, beside the sealed bundles (whose
format is unchanged):

| File in `results/<run>/` | What it is |
|---|---|
| `telemetry/<condition>.spans.jsonl` | One OpenTelemetry span per line; one trace per trial |
| `telemetry_summary.{json,md}` | Per condition: latency median and p90 per span kind, tokens in and out, model calls and cost per trial and per run |
| `estimate.{json,md}` | The estimate printed before the run |
| `actual.json`, `estimate_vs_actual.md` | What the run used, beside the estimate |
| `machine.json`, `machine/` | Cloud Run runs only: execution, billed seconds, cost, GPU and CPU description, Ollama log |

Spans follow the OpenTelemetry GenAI semantic conventions where they exist
(`gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`,
`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`,
`gen_ai.usage.cache_read.input_tokens`, `gen_ai.response.finish_reasons`); the
experiment's own attributes are under `e2.*` (condition, call purpose, recall
placement, path timings) and `circumstances.*` (run, trial, case, attempt,
seed). Local runs get exact token counts from Ollama (`prompt_eval_count`,
`eval_count`) and its own timings (`ollama.*_ms`). No prompt, reply, key or host
name is recorded. Set `OTEL_EXPORTER_OTLP_ENDPOINT` to also send the spans to a
collector. The agent does not stream (as in the stored runs), so there is no
time to first token; for Ollama, `ollama.load_duration_ms` +
`ollama.prompt_eval_duration_ms` is the server-side time before generation.

Every run first prints an estimate (trials, model calls, tokens, spend with a
range, duration; for a GCP machine, start-up, run and teardown time and the
worst case at its hard lifetime). A run that spends money waits for a yes;
local runs do not wait.

```bash
uv run inv e2.estimate --args="--provider openai --embed-provider openai"   # estimate only
uv run inv e2.run --args="--provider openai --embed-provider openai --out results/e2-openai"
uv run inv e2.summary --run e2-openai
```

`--yes` skips the question, `--estimate-only` stops after the estimate,
`--profile <run>` chooses the run whose telemetry (or, without telemetry, whose
bundles, with tokens counted as characters / 4) the estimate scales, and
`--max-cases N` runs N cases spread over the pack (pilots). Prices are in
`pricing/prices.yaml`, each with its source and the date it was read.

**Hosted providers** (`--provider openai|vertex|anthropic`, `--embed-provider
openai`) keep the prompt, retriever, cases, seeds and grading. Differences
(checked against the APIs on 2026-11-13):

| | temperature 0.7 | seed | JSON mode | reasoning off |
|---|---|---|---|---|
| OpenAI `gpt-5.6-*`, Responses API (default, as Kodama) | sent (refused once reasoning is on) | not accepted | yes | yes (`effort: none`) |
| OpenAI `gpt-5.6-*`, `--openai-api chat` | sent | sent (Beta, best effort) | yes | yes |
| Anthropic Claude 5.x (`sonnet-5`, `haiku-5-5`, `opus-5-5`) | refused, not sent | not accepted | no (prompt only) | yes |
| Anthropic `claude-sonnet-4-6`, `claude-haiku-4-5` | sent | not accepted | no (prompt only) | yes |
| Vertex `gemini-3.8-flash` | ignored by the model | sent | yes | no (lowest level: `low`) |

`--embed-provider openai` changes the dense half of the retriever
(`text-embedding-3-small`, as Kodama's hosted instances). Keys come from `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` (or
Kodama's `KODAMA_MODELS__*` names), or from Kodama's `config/secrets.yaml` with
`--kodama-secrets`; Vertex uses Application Default Credentials. Check a
provider with one trial (no bundle, a fraction of a cent):

```bash
uv run python src/hosted_check.py --provider openai --embed-provider openai --kodama-secrets ../kodama/config/secrets.yaml
```

**On a GPU in GCP**: `uv run inv gcp.run --run <name>` runs Experiment 2 as a
Cloud Run job with an NVIDIA L4 (built from the current commit, with the exact
local model files) and copies the results back; see `infra/gcp/README.md`.

`results/e2-smoke` is the telemetry smoke (20 trials); its latencies are not
representative (`results/e2-smoke_NOTES.md`).

## Anonymous review copy

TMLR review is double-blind and this repository names the authors, so reviewers
get a separate copy:

```bash
uv run inv paper.anon     # needs git, uv, tectonic
```

It writes `dist/stale-but-on-time-anon.pdf` (the paper built in double-blind mode),
`dist/stale-but-on-time-anon.zip` (the supplementary archive, ~4 MB) and the
unpacked tree in `dist/anon/`. The copy has no git history, an anonymous
`paper/identity.tex`, names and URLs replaced, the Circumstances framework vendored
at the pinned commit and renamed (its name leads to this organisation), and the sealed
bundles re-sealed and verified again with the renamed copy. The script
fails if any identifying string is left in any file or in the PDF. It was checked by
running the full analysis, figures, numbers and paper build inside the copy; the
numbers are identical. The product name in the quoted system prompt appears as
`[PRODUCT NAME]`.

Identity lives in one file, `paper/identity.tex` (author block, product and
framework names, the `\ifanon` switch). To build the de-anonymised preprint, use the
repository as it is; for the camera-ready version, change `[preprint]` to `[accepted]`
in `paper/main.tex`.

## Licence

Code, pack and results: Apache-2.0 (`LICENSE`). The TMLR style files in
`paper/` carry their own licence. LoCoMo is CC BY-NC 4.0 and is not included.

## Before submission

- A human should read `results/e2-run1_audit_sample.csv` and `results/e3_audit_sample.csv` against the grades and fill in the verdict columns. So far only AI assistants have read them, and the paper says so.
- Submit the paper and archive produced by `inv paper.anon`, not the files in this repository, and do not link this repository from the submission.
