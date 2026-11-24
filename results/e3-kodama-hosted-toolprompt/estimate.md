# Estimate before the run (written 2026-11-16, before the first trial)

200 trials: the 40 cases of pack 1.0.0 (unchanged in 1.1.0) × 5 trials per case, one condition (`a2-tool-bringup`: condition a with the bring-up line rendered), gpt-5.6-luna, on the image of the reported hosted run (Kodama `3101c5b`).

The basis is condition a in `../e3-kodama-hosted/cost.json`: $0.00060 per trial metered, $0.00135 at most.

- **Model calls, metered:** about $0.12.
- **Upper bound,** with every unmetered check call billed in full: about $0.27.
- **Embeddings:** about $0.01.
- **Total:** about $0.13, at most about $0.28.
- **Budget.** The cap for hosted Experiment 3 from the pilot's last condition on is $6.00. About $1.21 (at most about $2.90) was spent before these add-on runs. This run and the control-case run in `../e3-kodama-hosted-carry/` together: about $0.27, at most about $0.61.

**Duration.** About 30 s per trial, so about 1.7 hours.
