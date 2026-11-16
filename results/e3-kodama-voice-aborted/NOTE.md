# Aborted voice run (do not report as a result)

Spoken trials on Kodama `52dbd04`, 2026-11-11:
- a-tool: 20:09:15–20:30:14 UTC
- d-blocking-backthought: 20:30:14–20:49:51 UTC

Each condition is 40 cases × 1 trial. The run was stopped at 20:52 UTC, during b-backthought, which left no bundle. Both bundles are sealed and verify.

**Why it was stopped.** When a voice session ends, Kodama publishes a memorizer job (`maybePublishMaintainJob` in `harness/voice_session.go`). That job makes long model calls on the same local Ollama: one took about 2 minutes, with prompts of about 5.4k tokens and over 400 generated tokens. Text sessions skip this job (`if vs.textMode { return }`). In text run 2 there were 0 such jobs; in this run there were 86.

Ollama serves one request at a time, so the next trials waited behind the memorizer.
- Ollama chat latency during the voice run: median 1.3 s, p90 8.0 s, max 52 s, 54 HTTP 500s (8-second client timeouts).
- During the text run: median ~1.0 s, p90 ~1.5 s, no errors.
- In the trials this caused:
  - addressing-classifier timeouts ("Could not tell if this was addressed to Kodama"), about 8 s of extra delay each;
  - failed turns (`agent.error`): 2 in a, 6 in d;
  - end of speech to reply audio: median 12–14 s, p90 33–42 s.

So these numbers measure interference from earlier trials' background work, not the recall conditions. Whisper itself was fine: word error rate 3.3% on the final utterances.

**To run voice cleanly, one of these is needed (not done, pending a decision):**
- skip the memorizer job for eval sessions, as text mode already does (a Kodama change);
- or have the voice runner wait between trials until the memorizer is idle.

## f992ca3-d-blocking-backthought (also not a result)

The memorizer was then skipped for eval sessions (Kodama `f992ca3`, `pipeline.skip_eval_memorizer`). On that commit, a, b and c ran cleanly (2026-11-11 23:31 to 2026-11-12 00:04 UTC) and are in `e3-kodama-voice/`. The d attempt in this folder (2026-11-12 00:21–00:55 UTC) is not usable, and 10 of its 40 trials ended in `error`:
- 22 empty, orphaned memorome pages, left by the 52dbd04 run above, failed embedding forever and broke Kodama's embedding queue. Each trial's setup then waited the full 180 s for embeddings. The rows were deleted, after a database backup.
- From 00:35 UTC a Blender render from another project shared the GPU and memory, which slowed the local model.

d was rerun in full on `f992ca3` once the GPU was idle (01:48–01:59 UTC). That run is the one in `e3-kodama-voice/`.
