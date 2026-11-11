"""Download the large, regenerable data that is not stored in git.

- The Experiment 1 embedding cache (`data/cache`, ~180 MB archive) from the GitHub release.
- LoCoMo (CC BY-NC 4.0) from its authors; it is never redistributed here.

Run through `uv run inv fetch-data`.
"""

from __future__ import annotations

import hashlib
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPO: str | None = "aenima-labs/stale-but-on-time"  # None: no release to fetch the cache from
TAG = "v0.1.0"
CACHE_FILE = "e1-embedding-cache.tar.gz"
CACHE_SHA256 = "b79ef082febb061e3480963ff46da9815fff7b7243578424a7c6e790746ca7aa"
LOCOMO_URL = "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"


def _download(url: str, target: Path) -> None:
    with urllib.request.urlopen(url) as response, target.open("wb") as out:
        shutil.copyfileobj(response, out)


def fetch_locomo(root: Path = ROOT) -> None:
    target = root / "data" / "locomo" / "locomo10.json"
    if target.exists() and target.stat().st_size > 0:
        print(f"{target.relative_to(root)} already present, skipping.")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    print("Downloading LoCoMo ...")
    _download(LOCOMO_URL, target)


def fetch_cache(root: Path = ROOT) -> None:
    cache = root / "data" / "cache"
    if cache.is_dir() and any(cache.iterdir()):
        print("data/cache already present, skipping.")
        return
    if REPO is None:
        print("No release to fetch the embedding cache from; E1 will regenerate it (~12 min).")
        return
    url = f"https://github.com/{REPO}/releases/download/{TAG}/{CACHE_FILE}"
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / CACHE_FILE
        print("Downloading embedding cache ...")
        _download(url, archive)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != CACHE_SHA256:
            raise SystemExit(f"checksum mismatch for {CACHE_FILE}: {digest}")
        (root / "data").mkdir(exist_ok=True)
        with tarfile.open(archive) as tar:
            tar.extractall(root / "data", filter="data")
    print("Extracted to data/cache.")
