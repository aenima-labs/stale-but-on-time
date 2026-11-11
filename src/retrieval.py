"""Hybrid lexical + dense retriever shared by both experiments.

BM25 (Robertson & Zaragoza, 2009) and cosine similarity over
``nomic-embed-text`` embeddings served by a local Ollama instance are fused
with reciprocal rank fusion (Cormack et al., 2009). Everything is
deterministic given the embedding model.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np

OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
RRF_K = 60
_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class BM25:
    """Okapi BM25 over a fixed list of documents."""

    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.n = len(docs)
        self.k1 = k1
        self.b = b
        self.lengths = np.array([len(d) for d in docs], dtype=np.float64)
        self.avgdl = float(self.lengths.mean()) if self.n else 0.0
        self.postings: dict[str, list[tuple[int, int]]] = {}
        for index, doc in enumerate(docs):
            for term, tf in Counter(doc).items():
                self.postings.setdefault(term, []).append((index, tf))
        self.idf = {
            term: math.log(1.0 + (self.n - len(p) + 0.5) / (len(p) + 0.5))
            for term, p in self.postings.items()
        }

    def scores(self, query: list[str]) -> np.ndarray:
        out = np.zeros(self.n, dtype=np.float64)
        for term in set(query):
            posting = self.postings.get(term)
            if not posting:
                continue
            idf = self.idf[term]
            for index, tf in posting:
                norm = tf + self.k1 * (1 - self.b + self.b * self.lengths[index] / self.avgdl)
                out[index] += idf * tf * (self.k1 + 1) / norm
        return out


def _ranks(scores: np.ndarray) -> np.ndarray:
    """1-based ranks, best first; ties broken by document index (stable)."""
    order = np.argsort(-scores, kind="stable")
    ranks = np.empty(len(scores), dtype=np.int64)
    ranks[order] = np.arange(1, len(scores) + 1)
    return ranks


def rrf_topk(bm25_scores: np.ndarray, dense_scores: np.ndarray, k: int) -> list[int]:
    fused = 1.0 / (RRF_K + _ranks(bm25_scores)) + 1.0 / (RRF_K + _ranks(dense_scores))
    return [int(i) for i in np.argsort(-fused, kind="stable")[:k]]


class Embedder:
    """Disk-cached client for Ollama's /api/embed endpoint."""

    def __init__(self, cache_dir: Path, model: str = EMBED_MODEL) -> None:
        self.model = model
        self.cache_dir = cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.mem: dict[str, np.ndarray] = {}

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def load(self, name: str) -> None:
        path = self.cache_dir / f"{name}.npz"
        if path.exists():
            data = np.load(path)
            self.mem.update({k: data[k] for k in data.files})

    def save(self, name: str, texts: list[str]) -> None:
        np.savez_compressed(
            self.cache_dir / f"{name}.npz",
            **{self._key(t): self.mem[self._key(t)] for t in set(texts)},
        )

    def embed(self, texts: list[str], batch: int = 64) -> np.ndarray:
        missing = [t for t in dict.fromkeys(texts) if self._key(t) not in self.mem]
        for start in range(0, len(missing), batch):
            chunk = missing[start : start + batch]
            request = urllib.request.Request(
                f"{OLLAMA_URL}/api/embed",
                data=json.dumps({"model": self.model, "input": chunk}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=600) as response:
                vectors = json.loads(response.read())["embeddings"]
            for text, vector in zip(chunk, vectors, strict=True):
                v = np.asarray(vector, dtype=np.float32)
                self.mem[self._key(text)] = v / (np.linalg.norm(v) + 1e-12)
        return np.stack([self.mem[self._key(t)] for t in texts])


def as_query(text: str) -> str:
    return "search_query: " + text


def as_document(text: str) -> str:
    return "search_document: " + text
