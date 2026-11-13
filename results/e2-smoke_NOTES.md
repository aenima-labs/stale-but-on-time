# e2-smoke: telemetry smoke (not a reported run)

A functional check of the OpenTelemetry instrumentation, the telemetry summary
and the estimate/actual comparison: `gemma4:e4b` through the local Ollama,
conditions `blocking` and `tool`, 2 cases × 5 trials each (20 trials),
2026-11-13 13:04:38–13:12:27 UTC.

```bash
uv run inv e2.run --args="--conditions blocking tool --max-cases 2 --out results/e2-smoke"
```

**Its latencies are not representative and must not be reported.** During the
window, the shared Ollama held `gemma4:e4b` with a 32,768-token context (loaded
by another client on the machine) while the agent asks for 4,096, so Ollama
reloaded the model on most calls: the spans record `ollama.load_duration_ms` of
10–35 s against 0.3 s of generation (`ollama.eval_duration_ms`). The stored
runs (`results/e2*`) did not have this; their trials took about 0.7 s.

What the smoke does show: every trial has one trace; token counts come from
Ollama's `prompt_eval_count` and `eval_count`; the bundle-based estimate
(characters / 4) came within 4% of the measured input tokens
(`estimate_vs_actual.md`). All 20 trials passed and both bundles verify.
