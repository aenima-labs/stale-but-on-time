# Stale but on Time

Paper and experiments: what asynchronous (never-wait) memory recall costs a
real-time conversational agent. Target venue: TMLR.

- Manuscript: `paper/main.tex` → `paper/main.pdf` (TMLR style, preprint option).
  The compiled PDF of the latest draft is committed here and attached to the release.
- Every number, table and data figure in the manuscript is generated from the
  result files; nothing is typed by hand.

## Layout

| Path | What it is |
|---|---|
| `pack-src/tessaly.yaml` | Source of the fictional memorome (48 notes) and the 40 cases |
| `pack/`, `fixtures/` | Generated Circumstances pack (format v4) and memorome fixture |
| `src/retrieval.py` | Hybrid BM25 + embedding retriever with reciprocal rank fusion |
| `src/e1_replay.py`, `src/e1_analyze.py` | Experiment 1: staleness replay on LoCoMo, analysis, timing model |
| `src/subject.py`, `src/e2_run.py`, `src/e2_analyze.py` | Experiment 2: reference agent (six memory conditions), runner, analysis |
| `src/providers.py`, `src/hosted_check.py` | Model providers behind one interface (local Ollama; hosted OpenAI, Gemini on Vertex, Anthropic) and a one-trial connectivity check |
| `src/telemetry.py`, `src/telemetry_summary.py` | OpenTelemetry tracing of every trial; per-condition summary of latency, tokens, calls and cost |
| `pricing/prices.yaml`, `src/pricing.py`, `src/estimate.py` | Dated price table with sources; run estimate, confirmation, estimate-vs-actual |
| `infra/gcp/`, `src/gcp_job.py` | Terraform, image and task for running Experiment 2 as a Cloud Run GPU job |
| `tests/` | Unit tests (`uv run inv e2.test`) |
| `src/e3_analyze.py` | Experiment 3: analysis of the pack run against the product (bundles in `results/e3-kodama`, first run in `results/e3-kodama-run1`) |
| `src/figures.py`, `src/make_numbers.py` | Figures, table bodies and number macros for the paper |
| `results/` | Per-utterance retrievals (E1), sealed run bundles (E2: `e2` main run, `e2-think` reasoning on, `e2-qwen3` second model), summaries, audit sample, provenance notes (`*_NOTES.md`) |
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

Everything from scratch (about 30 minutes: E1 replay ~12 min without the cache, E2 1,200 trials ~18 min):

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

`reproduce` runs the main E2 run only. The two robustness runs of Section 6.4 are
separate, because the first is slow:

```bash
uv run inv e2.run --args="--think --out results/e2-think"
```

```bash
uv run inv e2.run --args="--model qwen3:8b --out results/e2-qwen3"
```

The reasoning run takes about 2.7 hours on a laptop, the second-model run about 20
minutes. `e2.analyze` analyses all three runs (`src/e2_analyze.py --run <name>`).

E2 uses local models, so a rerun will not reproduce the stored trials bit for bit;
the sealed bundles in `results/e2`, `results/e2-think` and `results/e2-qwen3` are the
record the paper reports. Part of the reasoning run shared the GPU with another
process; `results/e2-think_NOTES.md` gives the window, and `src/make_numbers.py`
leaves those trials out of every latency figure.

Experiment 3 runs the same cases against the product itself, which this repository
does not contain. Its sealed bundles and trial tables are in `results/e3-kodama`
(the reported run) and `results/e3-kodama-run1` (the first run, kept for
disclosure); `uv run inv e2.analyze-product` re-analyses them without the product.
`results/e3_audit_sample.csv` is the sample read against the grades.
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
at the pinned commit, and the sealed bundles re-sealed and re-verified. The script
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

- A human should re-read `results/e2_audit_sample.csv` against the grades.
- Confirm two reference details: the 210 words/min figure attributed to Tauroza & Allison (1990), and volume/pages of Robertson & Zaragoza (2009).
- Submit the paper and archive produced by `inv paper.anon`, not the files in this repository, and do not link this repository from the submission.
