# Estimate before the run (written 2026-11-15, before the first trial)

1,000 trials: 40 cases × 5 trials per case × 5 conditions, gpt-5.6-luna, run one after another.

Basis: the pilot in `../e3-kodama-hosted-luna/` (same Kodama commit, models and configuration; one trial per case).

- Model calls, metered: about $0.0005 per trial (pilot a–d: $0.080 for 160 trials) → about $0.50.
- Upper bound with every unmetered check call (the streamed greeting and advice checks) billed in full: about $0.0012 per trial → about $1.19.
- Embeddings (memorome clone per trial plus queries): about $0.00007 per trial → about $0.07.
- Total: about $0.57; at most about $1.26. Cap for everything from the pilot's last condition on: $6.00.

Duration: the pilot took 4,731 s for 200 trials (23.7 s per trial), so about 6.6 hours, plus a backend restart before each condition.
