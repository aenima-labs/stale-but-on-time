# Stopped attempts of condition e in the first hosted run, on Kodama `70dcabb` (do not report as results)

These are the two attempts at `e-backthought-tool` in the first hosted gpt-5.6-luna run, on Kodama `70dcabb` (`../e3-kodama-hosted-run1/`). A Kodama defect stopped both, so that run has no condition e. The defect was then fixed (`3101c5b`), and all five conditions were rerun; that rerun is the reported hosted run, `../e3-kodama-hosted/`.

They are kept as evidence and are **not results**. Neither attempt wrote a bundle, so none of these trials was graded.

Both attempts used the same Kodama (`70dcabb`), runner, models, configuration and stack as conditions a–d of that run. Before each attempt Kodama was restarted, so each began with new consumers.

## The two attempts (2026-11-15, UTC)

| attempt | ran | trials | how it stopped | model calls, metered |
|---|---|---|---|---|
| 1 | 16:42:43–17:21:14 | 76 (15 cases × 5, plus 1) | 17:21:13: "embed consumer: next message error … nats: consumer deleted" on the conversation consumer, then "messages iterator closed" every second | $0.049 |
| 2 | 17:24:46–17:51:46 | 52 (10 cases × 5, plus 2) | 17:51:15 and 17:51:46: "nats: no heartbeat received" on the conversation consumer | $0.038 |

**How each attempt ended:**
- In both, the run's watchdog stopped the runner on the second consumer error.
- In both, the memorome-page consumer kept working.
- In attempt 2, one memorome-page embedding request timed out at 17:30:21. The consumer carried on, and the run continued.

**Unmetered calls.** 152 and 104 check calls are unmetered (see the first hosted run's NOTE.md).

**Traces.** `telemetry/e-backthought-tool.attempt<n>.kodama-traces.jsonl` hold the span dumps of these trials, scrubbed like the hosted runs'.

## Cause

### NATS deleted the consumer, both times

Kodama `70dcabb` declares its JetStream consumers in `internal/queue/jetstream.go` with a name but no durable name.
- The NATS server (v2.14.2, embedded in the Kodama process) therefore treats them as non-durable.
- It deletes such a pull consumer once all three of these hold:
  - no pull request has arrived for about 5 s;
  - none is waiting;
  - no delivered message is still inside its 30 s ack window.
- A durable consumer is never deleted this way.

Evidence that NATS did the deleting:
- After each stop, the conversation consumer's state directory was gone from the NATS store.
- In attempt 2, the store's consumer directory last changed at 17:50:45. The client noticed only 30 s later, through missing heartbeats.
- Nothing else could have deleted it. The embedded server is reachable only from inside the container, and the disk was 31 % full.

### Kodama never recovers

Its consumer loop (`runEmbedConsumer` in `internal/app/pipeline/pipeline.go`) keeps the old iterator and never fetches the consumer again. Conversation embedding then stays off until Kodama restarts.

### Local check

`nats-consumer-check/` holds two small Go programs. They use the same NATS versions, consumer settings and loop as Kodama, run against an embedded server and call no model. Each has its output beside it.
- **`deletion/`** deletes the consumer under the loop:
  - With a pull request waiting, the loop logs "consumer deleted" and then "messages iterator closed" for good. That is attempt 1's log.
  - With no pull request waiting, the loop logs nothing until "no heartbeat received", about 35 s later. That is attempt 2's log and the pilot's.
  - In both cases, the loop handled no further message, even after the consumer was created again.
- **`inactivity/`** keeps the loop idle or blocks its handler for up to 35 s. The server deleted nothing, because it waits out an unacknowledged message.

So a slow embedding request alone does not explain the deletion.

### Not known

What leaves the consumer without a waiting pull request for about 5 s:
- The client sends new pull requests only from inside the loop's `Next()` call.
- The embedded server's own log is switched off (`NoLog`).
- No conversation-embedding request had failed before either deletion.

### Relation to the pilot's failures

The pilot's failed attempts (`../e3-kodama-hosted-luna-aborted/`) stopped with repeated "no heartbeat received" after embedding requests timed out. Attempt 2 shows that this is the symptom of a deleted consumer, so the pilot's consumer was very likely deleted too. Its store was not inspected before that stack was replaced.

### Why only condition e

It now looks specific to e:
- Here, e's two attempts stopped after 76 and 52 trials.
- Conditions a–d ran 960 hosted trials without a stop: 160 in the pilot and 800 in the first hosted run.
- In the pilot, e's third attempt (40 trials) and a 5-trial smoke ran through.

Why e, I can only guess. e is the only condition with both backthought and the tool, so it does the most work per trial: the most model calls, the longest turns, and likely the most conversation rows to embed. Something in that load may leave the conversation consumer's loop without a waiting pull request for a few seconds.

Nothing in the logs shows this directly.

## What was done

- The product was not changed.
- After attempt 1, the partial trace file was moved out of the run folder and e was started again from a fresh Kodama process, with the same guards.
- After attempt 2, no third attempt was started on `70dcabb`, and Kodama was stopped.

## The fix, and the rerun

Anton decided to fix the product and rerun all five conditions.
- **The fix.** Kodama `3101c5b` gives every consumer a durable name. Its consumer loop (`internal/queue/consume.go`) stops its iterator after any error, fetches the consumer again (creating it if it is missing) and goes on. No other product code changed; the reported run's NOTE.md lists the files.
- **Checks before any trial,** with no model calls. Their output is in `nats-consumer-check/fixed-3101c5b/`.
  - The branch's own tests: consumers are durable; an old non-durable consumer becomes durable with its queued message kept; the loop resumes after its consumer is deleted while a pull request is waiting (attempt 1's form); a durable consumer survives a gap in pulls that deletes a non-durable one.
  - A further check deleted the consumer while no pull request was waiting (attempt 2's form). The loop logged "no heartbeat received", then "resumed", and delivered the queued messages. The first message came again, because its ack had gone to the deleted consumer. Kodama skips rows that already have an embedding, so a repeat does no harm.
- **The rerun.** All five conditions are complete, in `../e3-kodama-hosted/`.
  - No consumer error, recovery or recreation happened during any condition.
  - Condition e ran 200 trials without a stop, in 95 minutes.
  - Its first attempt was stopped by a Docker Desktop restart on the host, not by Kodama (`../e3-kodama-hosted-aborted-3101c5b/`).
