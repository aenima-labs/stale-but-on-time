# Control cases on hosted models: first attempt, stopped by an OpenAI embedding stall (do not report as results)

**This folder is not a result.** It holds the first attempt at the control-case run (pack 1.1.0, the ten `asked-carry` cases) on hosted models. That run is `../e3-kodama-hosted-carry/`. The attempt stopped in its first condition, so it wrote no bundle and none of its trials was graded.

## What ran

- **Build.** Kodama `3101c5b`, the image of the reported hosted run (`sha256:db428e50…`), on a stack created fresh on 2026-11-16 at 11:40 UTC.
- **Runner.** Kodama branch `e3-hosted-run` at `92d9f0f`, with the pack ported from the paper at `b96679e`.
- **Models.** gpt-5.6-luna for the reply and the checks, text-embedding-3-small for embeddings, as in `../e3-kodama-hosted/`.
- **Condition and trials.** a-tool, five trials per case, 2026-11-16 11:41:10–12:14:10 UTC. It finished 33 trials:
  - five each of carry-hives, carry-steps, carry-headbands, carry-colours, carry-ferry-wait and carry-clock-fast;
  - three of carry-flat-things.

  Their spans are in `telemetry/`.

## Why it stopped

1. **The trigger.** From 11:59 UTC, Kodama's requests to OpenAI's embedding endpoint started to run past its 30 s limit. Kodama logged 11 "embed consumer: handler error … context deadline exceeded" on the memorome-page consumer between 11:59 and 12:13.
2. **How the trials slowed.** Before its first turn, each trial waits until all 49 pages of its memorome clone are embedded, for up to 180 s. From about 11:57, trial starts spread from about 30 s apart to more than 2 minutes.
3. **The stop.** The last trial to start began at 12:04:52. The next three ran out their 180 s embedding wait, and the runner's stop rule ended the condition at 12:14:10.

**The queue consumers stayed up.** Kodama logged no "next message error", "restart error" or "resumed" line, and the watchdog only recorded the handler errors. The `3101c5b` fix held. The requests themselves were slow or stalled.

**The stall was transient.** At 12:15 UTC, three embedding requests each from the host and from inside the stack's Docker network answered in 0.3–1 s. OpenAI's side or the network path stalled for about a quarter of an hour; which one is not known.

**A product limit, not changed here.** A page whose request fails five times (`MaxDeliver`) is embedded again only when the backfill republishes it, at up to 32 rows a minute. So during a stall a trial's 180 s budget runs out quickly. This is the same exposure as in the pilot's first attempt at e (`../e3-kodama-hosted-luna-aborted/`).

## What was done

- The attempt was set aside, and its runner log, watchdog log, Kodama log and unscrubbed spans were kept outside this repository.
- The control cases on the local model (`../e3-kodama-carry/`) ran next, on a separate stack.
- Agreed with the paper session: after the local runs, probe the embedding endpoint, then repeat the hosted run from the start on a fresh stack, with the same estimate and stop rule. If the provider stalls again, that run stops and is reported, not retried.
- The product was not changed for the backfill limit above. It is to be raised with Anton separately.

## Cost

33 trials: $0.024 metered (at most $0.048 with the unmetered check calls billed in full), plus about $0.002 for embeddings.

## Files

- **`telemetry/a-tool.kodama-traces.jsonl`.** One line per finished trial with the turn's spans, scrubbed like the reported run. Removed:
  - Kodama's prompts and tool definitions;
  - the agent and tool descriptions;
  - OpenAI's response and item ids;
  - the encrypted reasoning blobs.
