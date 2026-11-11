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
| `src/figures.py`, `src/make_numbers.py` | Figures, table bodies and number macros for the paper |
| `results/` | Per-utterance retrievals (E1), sealed run bundles (E2), summaries, audit sample |
| `scripts/fetch_data.sh` | Downloads LoCoMo and the optional embedding cache |

## Data

| What | Where | Needed for |
|---|---|---|
| Per-utterance retrievals (E1), sealed run bundles with every trial (E2), summaries, audit sample | in git, `results/` (~17 MB) | Re-running the analysis, figures and the paper. No model needed. |
| Embedding cache for LoCoMo (`data/cache`, ~180 MB archive) | [Release `v0.1.0`](https://github.com/aenima-labs/stale-but-on-time/releases/tag/v0.1.0), fetched by `scripts/fetch_data.sh` | Skipping the ~12 min embedding step of E1. Optional; regenerated if absent. |
| LoCoMo conversations | Downloaded from its authors by `scripts/fetch_data.sh` | E1 replay. CC BY-NC 4.0, not redistributed here. |
| Latest compiled paper | `paper/main.pdf` (also attached to the release) | Reading. |

## Reproduce

Requires `uv`, a local [Ollama](https://ollama.com) with `nomic-embed-text` and
`gemma4:e4b`, and `tectonic`. The [Circumstances](https://github.com/aenima-labs/circumstances)
framework is pinned by commit in `pyproject.toml` and installed by `uv sync`.

Analysis, figures and paper only (no Ollama needed):

```bash
uv sync
uv run python src/e1_analyze.py
PYTHONPATH=src uv run python src/e2_analyze.py
uv run python src/figures.py
uv run python src/make_numbers.py
(cd paper && tectonic main.tex)
```

Everything from scratch:

```bash
scripts/fetch_data.sh                        # LoCoMo, plus the optional embedding cache
uv sync
uv run python src/e1_replay.py            # ~12 min without the cache
uv run python src/e1_analyze.py
uv run python src/build_pack.py
PYTHONPATH=src uv run python src/e2_run.py   # ~18 min, 1,200 trials
PYTHONPATH=src uv run python src/e2_analyze.py
uv run python src/figures.py
uv run python src/make_numbers.py
(cd paper && tectonic main.tex)
```

E2 uses a local `gemma4:e4b`, so a rerun will not reproduce the stored trials
bit for bit; the sealed bundles in `results/e2` are the record the paper reports.
`src/e2_run.py` writes the pack path into each bundle as the relative `pack`, and
`src/scrub_paths.py` does the same for bundles made earlier (it re-seals them and
verifies the seal): `PYTHONPATH=src uv run python src/scrub_paths.py results/e2`.

## Anonymous review copy

TMLR review is double-blind and this repository names the authors, so reviewers
get a separate copy:

```bash
uv run python scripts/make_anon.py     # needs git, uv, tectonic
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
- Submit the paper and archive produced by `scripts/make_anon.py`, not the files in this repository, and do not link this repository from the submission.
