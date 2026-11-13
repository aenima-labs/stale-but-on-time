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

# The models, byte-identical to the local runs. The task uploads the local
# manifests to gs://<bucket>/models/manifests/ and passes their SHA-256 in
# MODEL_MANIFESTS (name=sha256; `ollama list` shows its first 12 characters).
# Each blob the manifest names is taken from the bucket, or downloaded by its
# digest from Ollama's registry (a tag there may since point at other weights,
# but a digest cannot) and saved to the bucket. Every blob's SHA-256 is checked.
MODELS=/root/.ollama/models
REGISTRY=https://registry.ollama.ai/v2/library
for entry in ${MODEL_MANIFESTS//,/ }; do
  model="${entry%%=*}"; want="${entry#*=}"
  name="${model%%:*}"; tag="${model#*:}"; [ "$tag" = "$model" ] && tag=latest
  rel="manifests/registry.ollama.ai/library/$name/$tag"
  [ -f "/gcs/models/$rel" ] || { echo "$model: no manifest in the bucket"; exit 5; }
  got="$(sha256sum "/gcs/models/$rel" | cut -d' ' -f1)"
  [ "$got" = "$want" ] || { echo "$model: manifest $got in the bucket, expected $want"; exit 5; }
  mkdir -p "$MODELS/$(dirname "$rel")" "$MODELS/blobs" /gcs/models/blobs
  sources=""
  for digest in $(grep -o 'sha256:[0-9a-f]*' "/gcs/models/$rel" | sort -u); do
    blob="sha256-${digest#sha256:}"
    if [ -f "/gcs/models/blobs/$blob" ]; then
      cp "/gcs/models/blobs/$blob" "$MODELS/blobs/$blob"; sources="$sources bucket"
    else
      curl -fsSL --retry 3 -o "$MODELS/blobs/$blob" "$REGISTRY/$name/blobs/$digest"; sources="$sources registry"
    fi
    [ "$(sha256sum "$MODELS/blobs/$blob" | cut -d' ' -f1)" = "${digest#sha256:}" ] || { echo "$model: blob $blob does not match its digest"; exit 4; }
    [ -f "/gcs/models/blobs/$blob" ] || cp "$MODELS/blobs/$blob" "/gcs/models/blobs/$blob"
  done
  cp "/gcs/models/$rel" "$MODELS/$rel"
  echo "$model manifest $got; blobs from:$sources" >> "$LOCAL/machine/models.txt"
done
ollama list > "$LOCAL/machine/ollama-list.txt"
mark MODELS_READY

cd /opt/sbot
# Local models only: the estimate and confirmation were done by the task.
OLLAMA_URL=http://127.0.0.1:11434 uv run --frozen --no-dev inv e2.run --args="--yes --out results/$RUN_NAME $RUN_ARGS"
curl -fs http://127.0.0.1:11434/api/ps > "$LOCAL/machine/ollama-ps.json" || true
