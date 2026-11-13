#!/bin/bash
# Entrypoint of the Experiment 2 Cloud Run job. The bucket is mounted at /gcs.
# Writes results/<run> to gs://<bucket>/results/<run>/ on exit, success or not.
set -euo pipefail

RUN_NAME="${RUN_NAME:?RUN_NAME is required}"
RUN_ARGS="${RUN_ARGS:-}"
OUT="/gcs/results/$RUN_NAME"
LOCAL="/opt/sbot/results/$RUN_NAME"
mkdir -p "$OUT/status" "$LOCAL/machine"

stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
mark() { echo "$(stamp) ${2:-}" > "$OUT/status/$1"; }

finish() {
  rc=$?
  set +e
  cp /tmp/ollama.log "$LOCAL/machine/ollama.log" 2>/dev/null
  cp -r "$LOCAL/." "$OUT/"
  if [ "$rc" -eq 0 ]; then mark DONE "exit 0"; else mark FAILED "exit $rc"; fi
}
trap finish EXIT
mark STARTED "$RUN_ARGS"

# What the machine was (no names, no addresses).
(nvidia-smi -q || /usr/local/nvidia/bin/nvidia-smi -q) > "$LOCAL/machine/nvidia-smi.txt" 2>&1 || true
lscpu > "$LOCAL/machine/lscpu.txt" 2>&1 || true
free -g > "$LOCAL/machine/memory.txt" 2>&1 || true

# The exact model blobs of the local runs.
mkdir -p /root/.ollama/models
cp -r /gcs/models/. /root/.ollama/models/
mark MODELS_COPIED

OLLAMA_HOST=127.0.0.1:11434 OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_KEEP_ALIVE=24h \
  nohup ollama serve > /tmp/ollama.log 2>&1 &
for _ in $(seq 90); do curl -fs http://127.0.0.1:11434/api/version > "$LOCAL/machine/ollama-version.json" && break; sleep 2; done
ollama list > "$LOCAL/machine/ollama-list.txt"
mark OLLAMA_READY

cd /opt/sbot
# Local models only: the estimate and confirmation were done by the task.
OLLAMA_URL=http://127.0.0.1:11434 uv run --frozen --no-dev inv e2.run --args="--yes --out results/$RUN_NAME $RUN_ARGS"
curl -fs http://127.0.0.1:11434/api/ps > "$LOCAL/machine/ollama-ps.json" || true
