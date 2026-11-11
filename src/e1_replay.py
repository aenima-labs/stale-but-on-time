"""Experiment 1: staleness of lagged recall, replayed on LoCoMo.

For every evaluated utterance ``i`` of session ``s`` the memory is all
utterances of sessions ``< s`` of the same conversation. We retrieve the
top-10 memories for queries built from different views of the live
conversation ("ambience") and store the ranked ids. Metrics are computed
later by ``e1_analyze.py`` so that no modelling choice is baked in here.

Conditions, for each ambience window ``w`` (number of utterances):
  L0..L6   window ending ``L`` utterances before the incoming one (L0 = fresh)
  P25..P75 window ending at the incoming utterance, truncated to its first p%
  RAND     fresh window of a random utterance from another session (floor)
  NEXT     the utterance that actually followed (hindsight reference, w=1)
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np

from retrieval import BM25, Embedder, as_document, as_query, rrf_topk, tokenize

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = (1, 3, 5)
MAX_LAG = 6
PREFIXES = (25, 50, 75)
TOPK = 10
SEED = 20261110


def load_sessions(sample: dict) -> list[list[str]]:
    conv = sample["conversation"]
    names = sorted(
        (k for k in conv if k.startswith("session_") and not k.endswith("date_time")),
        key=lambda k: int(k.split("_")[1]),
    )
    return [[turn["text"].strip() for turn in conv[name]] for name in names]


def window(turns: list[str], end: int, w: int) -> str:
    """Utterances ``end-w+1 .. end`` (inclusive), clipped at the session start."""
    return " ".join(turns[max(0, end - w + 1) : end + 1])


def prefix_window(turns: list[str], i: int, w: int, pct: int) -> str:
    words = turns[i].split()
    head = " ".join(words[: max(1, math.ceil(len(words) * pct / 100))])
    return " ".join([*turns[max(0, i - w + 1) : i], head])


def replay(sample: dict, embedder: Embedder, out) -> int:
    conv_id = sample["sample_id"]
    sessions = load_sessions(sample)
    rng = random.Random(f"{SEED}:{conv_id}")
    embedder.load(conv_id)

    # Pass 1: enumerate every query string so embeddings can be batched.
    plan: list[dict] = []
    eligible = [
        (s, i)
        for s in range(1, len(sessions))
        for i in range(MAX_LAG, len(sessions[s]))
    ]
    for s, i in eligible:
        cur = sessions[s]
        queries: dict[str, str] = {}
        for w in WINDOWS:
            for lag in range(MAX_LAG + 1):
                queries[f"w{w}/L{lag}"] = window(cur, i - lag, w)
            for pct in PREFIXES:
                queries[f"w{w}/P{pct}"] = prefix_window(cur, i, w, pct)
            other_s, other_i = rng.choice([e for e in eligible if e[0] != s])
            queries[f"w{w}/RAND"] = window(sessions[other_s], other_i, w)
        if i + 1 < len(cur):
            queries["NEXT"] = cur[i + 1]
        plan.append({"s": s, "i": i, "queries": queries})

    memory_texts = [t for session in sessions for t in session]
    query_texts = sorted({q for item in plan for q in item["queries"].values()})
    doc_inputs = [as_document(t) for t in memory_texts]
    query_inputs = [as_query(t) for t in query_texts]
    doc_vectors = embedder.embed(doc_inputs)
    query_vectors = dict(zip(query_texts, embedder.embed(query_inputs), strict=True))
    embedder.save(conv_id, doc_inputs + query_inputs)

    # Pass 2: retrieve against the memory visible at each session.
    offsets = np.cumsum([0] + [len(session) for session in sessions])
    written = 0
    current_s = -1
    bm25: BM25 | None = None
    cache: dict[str, list[int]] = {}
    for item in plan:
        s, i = item["s"], item["i"]
        if s != current_s:
            n_mem = int(offsets[s])
            bm25 = BM25([tokenize(t) for t in memory_texts[:n_mem]])
            dense = doc_vectors[:n_mem]
            cache = {}
            current_s = s
        assert bm25 is not None
        topk: dict[str, list[int]] = {}
        for name, text in item["queries"].items():
            if text not in cache:
                cache[text] = rrf_topk(
                    bm25.scores(tokenize(text)), dense @ query_vectors[text], TOPK
                )
            topk[name] = cache[text]
        cur = sessions[s]
        fresh1 = query_vectors[cur[i]]
        before3 = query_vectors[window(cur, i - 1, 3)]
        out.write(
            json.dumps(
                {
                    "conv": conv_id,
                    "session": s + 1,
                    "i": i,
                    "n_memory": int(offsets[s]),
                    # word counts of utterances i, i-1, ..., i-MAX_LAG
                    "words": [len(cur[i - d].split()) for d in range(MAX_LAG + 1)],
                    "shift": float(1.0 - fresh1 @ before3),
                    "topk": topk,
                }
            )
            + "\n"
        )
        written += 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="only first N conversations")
    parser.add_argument("--out", default=str(ROOT / "results" / "e1_turns.jsonl"))
    args = parser.parse_args()
    samples = json.loads((ROOT / "data" / "locomo" / "locomo10.json").read_text())
    embedder = Embedder(ROOT / "data" / "cache")
    with open(args.out, "w") as out:
        for sample in samples[: args.limit]:
            started = time.time()
            n = replay(sample, embedder, out)
            embedder.mem.clear()
            print(f"{sample['sample_id']}: {n} turns in {time.time() - started:.0f}s", flush=True)


if __name__ == "__main__":
    main()
