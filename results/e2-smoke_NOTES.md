# e2-smoke: telemetry smoke (not a reported run)

A functional check of the OpenTelemetry instrumentation, the telemetry summary
and the estimate/actual comparison: `gemma4:e4b` through the local Ollama,
conditions `blocking` and `tool`, 2 cases × 5 trials each (20 trials),
2026-11-13 13:04:38–13:12:27 UTC.

```bash
uv run inv e2.run --args="--conditions blocking tool --max-cases 2 --out results/e2-smoke"
```

**Its latencies are not representative and must not be reported.** During the
window, the laptop had 4.7–11 GiB of its 36 GiB free (the Docker Desktop VM held
about 23 GiB), so Ollama could not keep `gemma4:e4b` (9.4 GiB at a 4,096-token
context) and `nomic-embed-text` loaded together: it evicted one to load the
other on almost every call (77 model loads in 8 minutes in the Ollama log). The
spans record `ollama.load_duration_ms` of 10–35 s against 0.3 s of generation
(`ollama.eval_duration_ms`); `telemetry_summary.md` flags every such call. The
stored runs (`results/e2*`) did not have this; their trials took about 0.7 s.
Since then, `e2_run.py` loads both models before a local run and refuses to
start if they are not both resident (`--allow-reloads` overrides).

What the smoke does show: every trial has one trace; token counts come from
Ollama's `prompt_eval_count` and `eval_count`; the bundle-based estimate
(characters / 4) came within 4% of the measured input tokens
(`estimate_vs_actual.md`). All 20 trials passed and both bundles verify.
