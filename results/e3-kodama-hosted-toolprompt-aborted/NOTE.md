# Prompt check on hosted models: first attempt, lost to a network outage on the host (do not report as results)

**This folder is not a result.** It holds the first attempt at `a2-tool-bringup` on hosted models: condition a plus one sentence telling the model it may search for and bring up a memory unasked. The run is `../e3-kodama-hosted-toolprompt/`, and its NOTE.md describes the condition. This attempt wrote no bundle, so none of its trials was graded.

## What ran

- **Build.** Kodama `3101c5b`, the image of the reported hosted run (`sha256:db428e50…`).
- **Stack.** Created fresh on 2026-11-17 at 12:53 UTC. The variant role file was stored as friend version 2 (md5 `41d140c599914a341300a9151096ff46`) before the first settings, so every settings document there pinned it.
- **Models.** gpt-5.6-luna for the reply and the checks, text-embedding-3-small for embeddings.
- **Runner.** Kodama `cb4dc99`, `--friend-version 2`.
- **Start.** Requests to the embedding endpoint (from the host and from inside the stack) and to the reply model had answered in 0–3 s just before.
- **Trials.** It started at 12:54:02 UTC and finished 9 trials, all on 2026-11-17: 8 between 12:54 and 13:23, and 1 at 19:35. They were five of abs-ansel-country, three of abs-car and one of abs-chess-opening.
- **The sentence was sent.** All 9 trials' instructions, as sent to OpenAI, contain it.

## Why it stopped

1. **The outage.** From 13:23 UTC the stack could no longer resolve the API host. Kodama logged 5,304 embedding errors "lookup api.openai.com on 127.0.0.11:53: no such host" from then until 22:22 UTC. The trials waiting for their memorome clone to be embedded could not start, and one more trial ran at 19:35.
2. **What else was going on.** The same day, the host was asleep with its lid closed from 08:40 to 12:00 UTC (`../e3-kodama-hosted-carry/NOTE.md`). The power log now starts on 2026-11-21, so it no longer shows whether this outage was another sleep or a network loss.
3. **The end of the run.** The runner's exit was not recorded. The scratch folder with its logs was cleared before the next run, when the operating system was updated. Kodama's own log survived and is kept outside this repository.

**The queue consumers stayed up.** Kodama logged no "next message error", "restart error" or "resumed" line. The `3101c5b` fix held.

## What was done

- The attempt was set aside here.
- `a2-tool-bringup` was run again from the start on a new fresh stack, on 2026-11-24.

## Cost

9 trials: $0.007 metered (at most $0.014), plus about $0.001 for embeddings.

## Files

- **`telemetry/a2-tool-bringup.kodama-traces.jsonl`.** One line per finished trial with the turn's spans, scrubbed like the reported run. Removed:
  - Kodama's prompts and tool definitions;
  - the agent and tool descriptions;
  - OpenAI's response and item ids;
  - the encrypted reasoning blobs.
