# Estimate before the run (written 2026-11-16, before the first trial)

250 trials: the ten asked-carry cases of pack 1.1.0 × 5 trials per case × 5 conditions (a–e), gpt-5.6-luna, run one after another, on the image of the reported hosted run (Kodama `3101c5b`).

The basis is the per-trial cost of each condition in `../e3-kodama-hosted/cost.json`.

- **Model calls, metered:** a $0.030, b $0.020, c $0.020, d $0.021, e $0.033 for 50 trials each, so about $0.12.
- **Upper bound,** with every unmetered check call billed in full: about $0.31.
- **Embeddings** (memorome clone per trial plus queries): about $0.02.
- **Total:** about $0.14, at most about $0.33.
- **Budget.** The cap for hosted Experiment 3 from the pilot's last condition on is $6.00. About $1.21 (at most about $2.90) was spent before this run. This run and the prompt check in `../e3-kodama-hosted-toolprompt/` together: about $0.27, at most about $0.61.

**Duration.** About 25–30 s per trial, so about 2 hours, plus a Kodama restart before each condition.
