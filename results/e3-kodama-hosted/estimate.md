# Estimate before the run (written 2026-11-15, before the first trial)

1,000 trials: 40 cases × 5 trials per case × 5 conditions, gpt-5.6-luna, run one after another, on Kodama `3101c5b`. That is `70dcabb` with durable queue consumers that resume after errors.

The basis is the run on `70dcabb`, now in `../e3-kodama-hosted-run1/`: a–d complete, plus 128 trials of e from its two stopped attempts.

- **Model calls, metered.** About $0.00046 per trial in a–d and $0.00068 in e, so about $0.51.
- **Upper bound,** with every unmetered check call billed in full: about $0.0012 per trial, so about $1.20.
- **Embeddings** (memorome clone per trial plus queries): about $0.00007 per trial, so about $0.07.
- **Total:** about $0.58, at most about $1.27.
- **Budget.** The cap for everything from the pilot's last condition on is $6.00. About $0.55 of it was spent before this run (at most about $1.40).

**Duration.** On `70dcabb`, trials took 27–30 s, so about 8 hours, plus a Kodama restart before each condition.
