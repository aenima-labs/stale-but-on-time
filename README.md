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
`e2.run`, `e2.analyze`, `e2.scrub-paths`; `paper.figures`, `paper.numbers`, `paper.build`,
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
