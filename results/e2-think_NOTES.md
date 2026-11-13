# Provenance notes for the reasoning-mode run (`results/e2-think`)

- Started 2026-11-11, `gemma4:e4b` with `think: true`, `num_predict` 2048, otherwise identical to `results/e2`.
- **Timing contamination, 12:44–13:20 UTC on 2026-11-11.** A second process (Kodama smoke tests, about 75 model calls) shared the same Ollama runner. Requests queued behind each other, and because the two clients used different `num_ctx` settings Ollama reloaded the model when they alternated (7.6–10.7 s load per call). Per-trial latencies of trials that ran in this window are inflated. Pass/fail outcomes are not affected.
- When reporting latency for this run, exclude trials whose trajectory `started_at` falls in that window, or report latency only from conditions that ran outside it.
