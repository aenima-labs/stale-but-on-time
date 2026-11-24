# Control cases on hosted models: stopped and replaced attempts (do not report as results)

**This folder is not a result.** It holds three attempts that the control-case run on hosted models (pack 1.1.0, the ten `asked-carry` cases) does not report. That run is `../e3-kodama-hosted-carry/`.

| | condition | ran (UTC) | trials | what happened |
|---|---|---|---|---|
| attempt 1 | a-tool | 2026-11-16 11:41:10–12:14:10 | 33, no bundle | stopped: OpenAI embedding requests stalled |
| rerun, condition c | c-blocking | 2026-11-16 13:54:41–20:41:49 | 23, no bundle | stopped: the host went to sleep with its lid closed |
| rerun, condition c again | c-blocking | 2026-11-17 08:18:06–12:01:56 | 50, sealed bundle | complete, but two trials lost to the host sleeping; replaced by a full rerun of c on 2026-11-24 |

## Common to all three

- **Build.** Kodama `3101c5b`, the image of the reported hosted run (`sha256:db428e50…`).
- **Models.** gpt-5.6-luna for the reply and the checks, text-embedding-3-small for embeddings, as in `../e3-kodama-hosted/`.
- **Pack.** Ported from the paper at `b96679e` (Kodama `92d9f0f`).

## Attempt 1: a-tool, stopped by an OpenAI embedding stall

- **Stack.** Created fresh on 2026-11-16 at 11:40 UTC.
- **Runner.** `recall/run.py` unchanged since `3101c5b`.
- **Trials finished (33):** five each of carry-hives, carry-steps, carry-headbands, carry-colours, carry-ferry-wait and carry-clock-fast, and three of carry-flat-things.

**Why it stopped:**
1. **The trigger.** From 11:59 UTC, Kodama's requests to OpenAI's embedding endpoint started to run past its 30 s limit. Kodama logged 11 "embed consumer: handler error … context deadline exceeded" on the memorome-page consumer between 11:59 and 12:13.
2. **How the trials slowed.** Before its first turn, each trial waits until all 49 pages of its memorome clone are embedded, for up to 180 s. From about 11:57, trial starts spread from about 30 s apart to more than 2 minutes.
3. **The stop.** The last trial to start began at 12:04:52. The next three ran out their 180 s embedding wait, and the runner's stop rule ended the condition at 12:14:10.

**The queue consumers stayed up.** Kodama logged no "next message error", "restart error" or "resumed" line, and the watchdog only recorded the handler errors. The `3101c5b` fix held. The requests themselves were slow or stalled.

**The stall was transient.** At 12:15 UTC, three embedding requests each from the host and from inside the stack's Docker network answered in 0.3–1 s. OpenAI's side or the network path stalled for about a quarter of an hour; which one is not known.

**Cost:** $0.024 metered (at most $0.048 with the unmetered check calls billed in full), plus about $0.002 for embeddings.

## The rerun's condition c: stopped when the host went to sleep

The control-case run was repeated from the start on a fresh stack, created on 2026-11-16 at 13:12 UTC. Embedding requests from the host and from inside the stack had first answered within a second.
- **a and b completed.** a-tool ran 13:12–13:35 UTC and b-backthought 13:35–13:54, 50 trials each with sealed bundles. They are in `../e3-kodama-hosted-carry/`.
- **c stopped.** c-blocking started at 13:54:41 and finished 23 trials: five each of carry-hives, carry-steps, carry-headbands and carry-colours, and three of carry-ferry-wait.

**Why it stopped:**
1. **The trigger.** At 14:03:35 UTC the host's lid was closed while it ran on battery, and macOS went to sleep ("Clamshell Sleep" in its power log). The runner's `caffeinate` cannot prevent that. The last trial replied at 14:03:36.
2. **During sleep.** macOS woke the machine briefly every 15–20 minutes ("DarkWake"). In those wakes Docker's DNS could not resolve the API host: Kodama logged 758 "embed memorome page: openai embed: … lookup api.openai.com on 127.0.0.11:53: no such host" errors, in bursts at 14:16, 17:06 and 19:40 UTC. The pending trials' memorome pages were dropped after five tries ("dropping after MaxDeliver").
3. **The stop.** The next trials ran out their 180 s embedding wait in wall-clock time, and the stop rule ended the condition at 20:41:49 UTC.
4. **The session running the evaluation** also lost its connection then ("ENOTFOUND"), so nothing was restarted until the next morning.

**The queue consumers stayed up** here too: no "next message error", "restart error" or "resumed" line.

**After waking:**
- On 2026-11-17 at 08:16 UTC the host was on mains power.
- Requests to the embedding and reply models answered in 0.4–2 s from the host and from inside the stack.
- No memorome page was left unembedded.

c, d and e were then run on the same stack, after the usual Kodama restart before each condition. The stack's volumes, image and configuration are the ones a and b ran on.

**Cost:** $0.009 metered (at most $0.026), plus about $0.002 for embeddings.

## The rerun's condition c, second time: complete, then replaced

This c ran to the end (50 trials, bundle `78bb7061…`, sealed and verified). 48 passed, and the 2 others are errors. Both errors came from the test host, not from Kodama.
1. **The sleep.** At 08:40:28 UTC on 2026-11-17 the host's lid was closed and macOS went to sleep. It stayed asleep, apart from brief maintenance wakes, until 12:00:31.
2. **Unaffected trials.** 47 trials had finished between 08:18 and 08:40:20, and all passed.
3. **carry-cat-sleep, trial 3** started at 08:40:39. Its reply call failed in a maintenance wake at 08:57:41 because Docker's DNS could not resolve the API host.
4. **carry-cat-sleep, trial 4** ran out the runner's trial timeout while the host was asleep, before its first turn. It has no spans.
5. **carry-cat-sleep, trial 5** ran after the wake and passed.

**Why it was replaced.** Counted as failures, the two errors would lower blocking's pass rate for reasons outside the system under test. That leans toward the paper's own claim that blocking is not ahead of lag 1. So, at the paper session's request, c was run again in full on the same stack on 2026-11-24 (12:38–12:54 UTC). That run is the c reported in `../e3-kodama-hosted-carry/`: 50 of 50 passed, with no error. The paper says that the condition was run again after two trials were lost to the machine sleeping.

**Files kept:**
- `c-blocking-replaced/`: this c's sealed bundle and `condition.json`;
- `telemetry/c-blocking.replaced.kodama-traces.jsonl`: its 49 trials with spans, scrubbed.

**Cost:** $0.018 metered (at most $0.055), plus about $0.003 for embeddings.

## A product limit seen in both, not changed here

A page whose request fails five times (`MaxDeliver`) is embedded again only when the backfill republishes it, at up to 32 rows a minute. So during a stall or an outage, a trial's 180 s budget runs out quickly. This is the same exposure as in the pilot's first attempt at e (`../e3-kodama-hosted-luna-aborted/`). The product was not changed for it; it is to be raised with Anton separately.

## Files

The runner logs, watchdog logs, Kodama logs and unscrubbed spans are kept outside this repository.

- **`c-blocking-replaced/`.** The replaced c's sealed bundle and `condition.json`.
- **`telemetry/a-tool.kodama-traces.jsonl`** (attempt 1), **`telemetry/c-blocking.rerun-attempt.kodama-traces.jsonl`** (the rerun's first c) and **`telemetry/c-blocking.replaced.kodama-traces.jsonl`** (the replaced c). One line per finished trial with the turn's spans, scrubbed like the reported run. Removed:
  - Kodama's prompts and tool definitions;
  - the agent and tool descriptions;
  - OpenAI's response and item ids;
  - the encrypted reasoning blobs.
