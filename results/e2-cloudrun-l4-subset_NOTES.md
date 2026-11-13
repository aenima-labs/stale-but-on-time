# e2-cloudrun-l4-subset: Cloud Run check (not a reported run)

A check that the Cloud Run job works end to end: Experiment 2 with the local
models (`gemma4:e4b`, `nomic-embed-text`) on a Cloud Run job with one NVIDIA L4
(6 vCPU, 24 GiB) in europe-west1, all six conditions, 2 cases × 5 trials each
(60 trials), image `e2-job:cadf25c`, execution `sbot-e2-q9xts`,
2026-11-13 14:56:30–15:11:10 UTC (880 s billed, $0.30; `machine.json`).

```bash
uv run inv gcp.run --run e2-cloudrun-l4-subset --args="--max-cases 2"
```

- Models byte-identical to the stored runs: both manifests' SHA-256 equal the
  local ones (`machine/models.txt`); blobs downloaded by digest from Ollama's
  registry and checked.
- All 60 trials ran; the bundles verify; no Ollama call reloaded a model after
  the first load of each condition (`telemetry_summary.md`).
- Time: ~1 min container and Ollama start, ~8.5 min downloading and checking the
  10 GB of model blobs (first run only; later runs copy them from the bucket),
  ~5 min for the run.
- Too small for any claim (2 cases). On these two cases the median reply path
  on the L4 was within 5–10% of the laptop's stored main run in every condition
  but hybrid (985 vs 1,403 ms, where the model searched less often).

Disclosure: a first execution (`sbot-e2-t4rmm`, 14:47–14:50 UTC, 196 s billed,
$0.07) stopped before any trial, because Ollama's registry tag `gemma4:e4b` now
names different weights (manifest `ccd2e5…`, ~6.6 GB) from those of the stored
runs (`c6eb39…`, 9.6 GB). The job has since fetched blobs by digest. Its status
file `FAILED` was left in the bucket and copied into this folder; it was removed.
