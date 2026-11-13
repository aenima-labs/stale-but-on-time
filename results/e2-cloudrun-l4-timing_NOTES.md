# e2-cloudrun-l4-timing: timing pass on a cloud GPU

Experiment 2 with the local models on a Cloud Run job with one NVIDIA L4, one
trial per case, for the paper's per-stage timings. Pass rates from one trial
per case are not for reporting.

- Execution `sbot-e2-wd5k4`, image `e2-job:f42f7eb` (built from commit
  `f42f7eb` of this branch), 2026-11-13 17:33:16–17:45:34 UTC, 738 s billed,
  **$0.25** (`machine.json`; estimate $0.39 [$0.31–$0.56], `estimate.md`).
- Machine: Cloud Run job in europe-west1, 1× NVIDIA L4 (24 GB), 6 vCPU, 24 GiB
  (`machine/nvidia-smi.txt`, `lscpu.txt`). Ollama 0.40.13 with the laptop's
  settings (flash attention, q8_0 KV cache).
- Models byte-identical to the stored runs: `gemma4:e4b` manifest `c6eb396d…`,
  `nomic-embed-text` manifest `0a109f42…` (`machine/models.txt`; every blob's
  SHA-256 checked, copied from the job's bucket).
- 240 trials: six conditions × 40 cases × 1 trial (attempt 1). Seeds equal each
  case's attempt-1 seed in the main run `results/e2` (checked for all 240);
  temperature 0.7 and every other agent setting as in the main run.

```bash
uv run inv gcp.run --run e2-cloudrun-l4-timing --args="--trials-per-case 1 --warmup"
```

Clean timings:
- No call loaded a model (`ollama.load_duration_ms` ≤ 1 s on every call; both
  models resident from the preflight on).
- No timed call was slow by the summary's rule (slower than
  max(5 × median, median + 1 s) of its kind): 0 in every condition
  (`telemetry_summary.json`, `slow_calls`).
- Before the timed conditions, every case ran once through the hybrid path,
  unrecorded (40 cases, 134 s), so the GPU's first-use costs (seen in
  `results/e2-cloudrun-l4-subset`: first prefill 36 s, first embeddings 21 s and
  ~3 s) fall outside the timed trials.
- No trial errors; all six bundles verify.

Median timings (ms; reply path from `path.*` metrics in the bundles, recall
from the spans):

| condition | recall on the reply path | before generation | complete reply (p50 / p90) |
|---|---:|---:|---:|
| none | – | 0 | 383 / 572 |
| lag1 | – (off path, 8) | 0 | 434 / 832 |
| prefetch50 | – (off path, 8) | 0 | 452 / 839 |
| blocking | 8 | 8 | 625 / 908 |
| tool | 7 (search) | 416 | 1,085 / 1,304 |
| hybrid | 7 (search, 12 of 40 trials) | 399 | 832 / 1,514 |

Deviations from the main run (disclose if reported):
- Hardware: an NVIDIA L4 in Google's data centre instead of the laptop;
  Ollama and the models are the same.
- One trial per case instead of five: the bundles record 1 trial per case,
  while the pack files inside them say 5 (`--trials-per-case 1` lowers it in
  memory; the pack digest is unchanged).
- The unrecorded warm-up above (the main run had none; on the laptop the
  first-use cost is small).
- The runner preloads both models and refuses to start unless both stay
  resident; the agent code is the main run's with tracing added (the Ollama
  request body is unchanged).
- Analysis (`e2_analyze.py`) is run by the paper session with its current
  grading, not committed here.
