#!/bin/bash
# Entrypoint of the Experiment 2 Cloud Run job. The bucket is mounted at /gcs.
# Writes results/<run> to gs://<bucket>/results/<run>/ on exit, success or not.
set -euo pipefail

RUN_NAME="${RUN_NAME:?RUN_NAME is required}"
RUN_ARGS="${RUN_ARGS:-}"
MODEL_MANIFESTS="${MODEL_MANIFESTS:?MODEL_MANIFESTS is required}"
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

OLLAMA_HOST=127.0.0.1:11434 OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_KEEP_ALIVE=24h \
  nohup ollama serve > /tmp/ollama.log 2>&1 &
for _ in $(seq 90); do curl -fs http://127.0.0.1:11434/api/version > "$LOCAL/machine/ollama-version.json" && break; sleep 2; done
mark OLLAMA_STARTED

# The models, byte-identical to the local runs. MODEL_MANIFESTS lists
# name=sha256-of-manifest as on the machine that started the job (the id
# `ollama list` shows is its first 12 characters). A model is taken from the
# bucket if it is there (every blob's hash checked), else pulled from Ollama's
# registry (which checks every blob's digest) and saved to the bucket for the
# next run. The job stops if a manifest's hash differs.
MODELS=/root/.ollama/models
for entry in ${MODEL_MANIFESTS//,/ }; do
  model="${entry%%=*}"; want="${entry#*=}"
  name="${model%%:*}"; tag="${model#*:}"; [ "$tag" = "$model" ] && tag=latest
  rel="manifests/registry.ollama.ai/library/$name/$tag"
  if [ -f "/gcs/models/$rel" ]; then
    mkdir -p "$MODELS/$(dirname "$rel")" "$MODELS/blobs"
    cp "/gcs/models/$rel" "$MODELS/$rel"
    for digest in $(grep -o 'sha256:[0-9a-f]*' "$MODELS/$rel" | sort -u); do
      blob="sha256-${digest#sha256:}"
      cp "/gcs/models/blobs/$blob" "$MODELS/blobs/$blob"
      [ "$(sha256sum "$MODELS/blobs/$blob" | cut -d' ' -f1)" = "${digest#sha256:}" ] || { echo "blob $blob corrupt"; exit 4; }
    done
    source=bucket
  else
    ollama pull "$model"
    source=registry
  fi
  got="$(sha256sum "$MODELS/$rel" | cut -d' ' -f1)"
  if [ "$got" != "$want" ]; then
    echo "$model: manifest $got, expected $want (the weights differ from the local runs)"
    exit 5
  fi
  echo "$model $got from $source" >> "$LOCAL/machine/models.txt"
  if [ "$source" = registry ]; then
    mkdir -p "/gcs/models/$(dirname "$rel")" /gcs/models/blobs
    for digest in $(grep -o 'sha256:[0-9a-f]*' "$MODELS/$rel" | sort -u); do
      blob="sha256-${digest#sha256:}"
      [ -f "/gcs/models/blobs/$blob" ] || cp "$MODELS/blobs/$blob" "/gcs/models/blobs/$blob"
    done
    cp "$MODELS/$rel" "/gcs/models/$rel"
  fi
done
ollama list > "$LOCAL/machine/ollama-list.txt"
mark MODELS_READY

cd /opt/sbot
# Local models only: the estimate and confirmation were done by the task.
OLLAMA_URL=http://127.0.0.1:11434 uv run --frozen --no-dev inv e2.run --args="--yes --out results/$RUN_NAME $RUN_ARGS"
curl -fs http://127.0.0.1:11434/api/ps > "$LOCAL/machine/ollama-ps.json" || true
