#!/usr/bin/env bash
# Download the large, regenerable data that is not stored in git:
#   - the Experiment 1 embedding cache (data/cache, ~180 MB archive), and
#   - LoCoMo (CC BY-NC 4.0, fetched from its authors, never redistributed here).
# Usage: scripts/fetch_data.sh [--locomo-only | --cache-only]
set -euo pipefail
cd "$(dirname "$0")/.."

REPO="aenima-labs/stale-but-on-time"
TAG="v0.1.0"
CACHE_FILE="e1-embedding-cache.tar.gz"
CACHE_SHA256="b79ef082febb061e3480963ff46da9815fff7b7243578424a7c6e790746ca7aa"
LOCOMO_URL="https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"

mode="${1:-all}"

if [[ "$mode" != "--cache-only" ]]; then
  mkdir -p data/locomo
  if [[ ! -s data/locomo/locomo10.json ]]; then
    echo "Downloading LoCoMo ..."
    curl -fSL -o data/locomo/locomo10.json "$LOCOMO_URL"
  fi
fi

if [[ "$mode" != "--locomo-only" ]]; then
  if [[ -d data/cache ]] && [[ -n "$(ls -A data/cache 2>/dev/null)" ]]; then
    echo "data/cache already present, skipping."
  else
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    echo "Downloading embedding cache ..."
    curl -fSL -o "$tmp/$CACHE_FILE" \
      "https://github.com/$REPO/releases/download/$TAG/$CACHE_FILE"
    echo "$CACHE_SHA256  $tmp/$CACHE_FILE" | shasum -a 256 -c -
    mkdir -p data
    tar -xzf "$tmp/$CACHE_FILE" -C data
    echo "Extracted to data/cache."
  fi
fi
