# Condition e on Kodama `3101c5b`: first attempt, stopped by a Docker Desktop restart

**This folder is not part of the reported run.** It holds condition e's first attempt in the hosted run on `3101c5b`, which is `70dcabb` with durable queue consumers that resume after an error. That run is `../e3-kodama-hosted/`, the hosted run the paper reports. Condition e was rerun there from the start. The two attempts on `70dcabb` that the queue defect stopped are in `../e3-kodama-hosted-aborted/`.

## What ran

- Condition e-backthought-tool, five trials per case, 2026-11-15 22:37:23–23:44:01 UTC. It ran right after condition a, on the same stack, image (`sha256:db428e50…`) and volumes.
- 138 trials finished: 27 cases × 5 plus 3 trials of `lighthouse-pet`. Their spans are in `telemetry/`. The condition stopped before writing a bundle, so there are no grades.

## Why it stopped

Docker Desktop restarted on the host, and that stopped every container. Kodama had no fault. The evidence is in `docker-restart.txt`.

- **23:43:55.** macOS launched Docker Desktop from its update-install folder (`com.docker.install/in_progress`).
- **23:44:00.** The Docker engine shut down "gracefully" and sent SIGTERM to every container on the host, in all three local stacks; all exited with code 0.
  - Kodama logged "api server shutting down" at 23:44:00.881. Its one embedding request in flight then failed with "context canceled".
  - This stack has no restart policy, so it stayed down. Containers with `restart: unless-stopped` in other stacks came back at 23:44:14.
- **The stop rule.** The trial running at 23:44:00 was waiting for its memorome clone to be embedded. It failed, and the next two failed at once. After three failures in a row the stop rule ended the condition at 23:44:01.
- **Who started it is not known.** The logs do not show whether the restart was started from Docker's menu or by Docker on its own. Docker's "download updates automatically" setting is on.

**Before that, no consumer error.** Kodama's log from the stack's start (20:54 UTC) to the stop has no "next message error", "restart error" or "resumed" line, and the watchdog never fired. On `70dcabb`, condition e stopped after about 38 and 27 minutes. This attempt ran 66 minutes without a consumer error.

## Docker versions before and after the restart

- **The same before and after:** Docker Desktop 4.99.0 (build 245822), engine 29.9.3, VM kernel 7.0.14-linuxkit.
- **How this is known:**
  - The app's backend binary, VM image and kernel in `/Applications/Docker.app` were last modified on 2026-11-09.
  - The boot log of the VM that ran until 23:44 (booted 2026-11-10) shows the same kernel as the VM started at 23:44:13.
  - The engine ships in that VM image. Its start before the restart is not in the surviving logs.
- **What it means for the run.** Condition a and the rerun of e, b, c and d ran on the same Docker versions.

## Cost

Model calls: $0.083 metered, at most $0.186 with the unmetered check calls billed in full. Embeddings for 138 trials: about $0.010.

## Files

- **`telemetry/e-backthought-tool.kodama-traces.jsonl`:** one line per finished trial with the turn's spans, scrubbed like the reported run. Removed:
  - Kodama's prompts and tool definitions;
  - the agent and tool descriptions;
  - OpenAI's response and item ids;
  - the encrypted reasoning blobs.

  The unscrubbed dump is kept outside this repository.
- **`docker-restart.txt`:** excerpts, with the home directory shown as `~`:
  - the macOS log;
  - Docker's VM log;
  - `docker inspect` of every local container;
  - the end of Kodama's log;
  - the version checks.
