# Failed attempts of condition e in the hosted pilot (do not report as a result)

These are the two failed attempts at `e-backthought-tool` in the gpt-5.6-luna pilot, kept as evidence. They are **not results**. The pilot is in `../e3-kodama-hosted-luna/`, and its condition e comes from a third attempt on 2026-11-15. The reported hosted run is `../e3-kodama-hosted/`, on Kodama `3101c5b`, which fixes the defect below. The first hosted run, on `70dcabb`, is `../e3-kodama-hosted-run1/`. Both attempts used the same Kodama (`70dcabb`), models and configuration as the pilot.

## Attempt 1: 2026-11-14 11:17 to 12:03 UTC, no bundle

- Three trials completed normally.
- From about 11:21 UTC, OpenAI embedding requests took longer than Kodama's 30 s limit. At 11:23 UTC Kodama's embedding consumer lost its NATS heartbeat ("embed consumer: next message error … no heartbeat received"), and it never recovered.
- No memorome page was embedded after that, so each later trial waited out the runner's 180 s for its memorome clone.
- The run was stopped at 12:03 UTC, before it wrote a bundle.
- `telemetry/e-backthought-tool.attempt1.kodama-traces.jsonl` holds the span dumps of the three completed trials. They are scrubbed like the pilot's, and they cost $0.003.

## Attempt 2: 2026-11-14 12:09 to 14:09 UTC, `e-backthought-tool/`

- The attempt started after a backend restart, on the same volumes.
- Twelve embedding requests timed out between 12:09 and 12:15 UTC. Then the consumer lost its heartbeat again.
- All 40 trials failed in setup ("memorome clone … not embedded"), made no model call, and passed 0 of 40.
- The bundle is sealed and verifies. `trials.csv`, `summary.json` and `summary.md` are its analysis: 40 of 40 errors.

## Cause

- **Trigger.** OpenAI embedding requests from the stack stalled past 30 s. The host neither slept nor lost its network, and OpenAI's status page lists no API incident then. The stall itself is unexplained: it was either on the provider side or in Docker's network path.
- **Damage.** It became a lost condition because of a Kodama defect: the embedding consumer loop does not recover after an error. It handles one page at a time, so a hung request blocks the queue for 30 s.
  - **What the logs show.** Repeated "no heartbeat received" after the timeouts.
  - **What a local check shows** (`../e3-kodama-hosted-aborted/nats-consumer-check/`). Kodama's loop logs exactly this when NATS deletes its consumer while no pull request is waiting. Kodama declares its consumers without a durable name, so NATS may delete them.
  - **Most likely cause.** The consumer was very likely deleted here too. The first hosted run's second e attempt logged the same "no heartbeat received", and there its consumer was gone from the NATS store.
  - **Why that is not certain.** The loop also stays stuck after a missed heartbeat when its consumer still exists, and the NATS store was not inspected before the stack was replaced.
  - **Either way,** the loop never recovers.
- **Product unchanged for the pilot and the first hosted run.** Neither part was changed in the product. The first hosted run (`../e3-kodama-hosted-run1/`) guarded against it instead:
  - a fresh backend process before each condition;
  - a watchdog that stops the run when the consumer loses its heartbeat;
  - a runner stop rule after three failed trials in a row.

  In that run the watchdog stopped condition e twice more. Both times NATS had deleted the conversation consumer, which Kodama declares without a durable name. See `../e3-kodama-hosted-aborted/NOTE.md`.
- **Fixed for the reported run.** Kodama `3101c5b` makes every consumer durable, and its loop recovers after an error. All five conditions were rerun on it (`../e3-kodama-hosted/`), and no consumer error occurred.
