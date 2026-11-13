# Provenance notes for the second-model run (`results/e2-qwen3`)

- Run on 2026-11-11, 14:41–15:01 UTC, `qwen3:8b` (Ollama id `500a1f067a9f`, 8.2B parameters, Q4_K_M), `think: false`, otherwise identical to `results/e2`: same pack, seeds, prompt, retriever, temperature 0.7.
- No other process used the Ollama runner during the run, so latencies are clean.
- Before the full run, four cases (one per class) were run in the `tool`, `blocking` and `hybrid` conditions to check that native tool calls, JSON mode and `think: false` work with this model. Nothing was changed as a result; that probe output was discarded.
- 40 failed replies were read after the run (abstain-class failures in `none`, `blocking` and `tool`; non-abstained misses on asked cases in `none` and `lag1`; unprompted failures in `tool`). The failures are real: unsupported statements, or replies without the target memory.
