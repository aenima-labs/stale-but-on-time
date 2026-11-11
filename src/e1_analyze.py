"""Experiment 1 analysis: staleness curve, topic-shift strata, timing model.

Reads ``results/e1_turns.jsonl`` and writes ``results/e1_summary.json``.
All confidence intervals are 95% percentile intervals from a cluster
bootstrap that resamples whole conversations (10 clusters).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = (1, 3, 5)
LAGS = (1, 2, 3, 4, 5, 6)
PREFIXES = (25, 50, 75)
BOOT = 2000
SEED = 20261110
COSTS = np.round(np.logspace(np.log10(0.1), np.log10(60), 41), 3)  # seconds
RATES = {"150wpm": 2.5, "210wpm": 3.5}  # words per second


def overlap(a: list[int], b: list[int], k: int) -> float:
    return len(set(a[:k]) & set(b[:k])) / k


def boot_ci(values: np.ndarray, clusters: np.ndarray, rng: np.random.Generator) -> list[float]:
    """Mean and cluster-bootstrap CI. ``values`` may be 1-D or (n, m)."""
    ids = np.unique(clusters)
    sums = np.stack([values[clusters == c].sum(axis=0) for c in ids])
    counts = np.array([(clusters == c).sum() for c in ids], dtype=float)
    draws = rng.integers(0, len(ids), size=(BOOT, len(ids)))
    means = sums[draws].sum(axis=1) / counts[draws].sum(axis=1).reshape(BOOT, *([1] * (sums.ndim - 1)))
    lo, hi = np.percentile(means, [2.5, 97.5], axis=0)
    return [values.mean(axis=0).tolist(), lo.tolist(), hi.tolist()]


def main() -> None:
    rows = [json.loads(line) for line in open(ROOT / "results" / "e1_turns.jsonl")]
    rng = np.random.default_rng(SEED)
    conv = np.array([r["conv"] for r in rows])
    out: dict = {
        "n_turns": len(rows),
        "n_conversations": int(len(np.unique(conv))),
        "n_sessions": len({(r["conv"], r["session"]) for r in rows}),
        "memory_size": {
            "median": float(np.median([r["n_memory"] for r in rows])),
            "min": int(min(r["n_memory"] for r in rows)),
            "max": int(max(r["n_memory"] for r in rows)),
        },
        "words_per_utterance": {
            "mean": float(np.mean([r["words"][0] for r in rows])),
            "median": float(np.median([r["words"][0] for r in rows])),
        },
    }

    # 1. Agreement with fresh retrieval, per window, condition and k.
    conditions = [f"L{lag}" for lag in LAGS] + [f"P{p}" for p in PREFIXES] + ["RAND"]
    agree: dict = {}
    per_turn: dict[tuple[int, str], np.ndarray] = {}
    for k in (5, 10):
        for w in WINDOWS:
            for cond in conditions:
                v = np.array(
                    [overlap(r["topk"][f"w{w}/{cond}"], r["topk"][f"w{w}/L0"], k) for r in rows]
                )
                agree[f"k{k}/w{w}/{cond}"] = boot_ci(v, conv, rng)
                if k == 5:
                    per_turn[(w, cond)] = v
    out["agreement"] = agree

    # Top-1 retention: is the fresh top-1 memory anywhere in the lagged top-5?
    out["top1_retained"] = {
        f"w3/{cond}": boot_ci(
            np.array([float(r["topk"]["w3/L0"][0] in r["topk"][f"w3/{cond}"][:5]) for r in rows]),
            conv,
            rng,
        )
        for cond in conditions
    }

    # 2. Topic-shift strata (w=3): quartiles of 1 - cos(utterance, preceding window).
    shift = np.array([r["shift"] for r in rows])
    edges = np.quantile(shift, [0.25, 0.5, 0.75])
    quartile = np.digitize(shift, edges)
    out["shift_quartile_edges"] = edges.tolist()
    out["by_shift"] = {
        cond: [
            boot_ci(per_turn[(3, cond)][quartile == q], conv[quartile == q], rng)
            for q in range(4)
        ]
        for cond in ("L1", "L2", "L3", "P50", "P75", "RAND")
    }

    # 3. Hindsight reference: memories retrieved by the utterance that actually
    #    followed. How much of that set does each condition's top-5 contain?
    has_next = np.array(["NEXT" in r["topk"] for r in rows])
    sub = [r for r in rows if "NEXT" in r["topk"]]
    out["hindsight"] = {
        "n_turns": len(sub),
        **{
            cond: boot_ci(
                np.array([overlap(r["topk"][f"w3/{cond}"], r["topk"]["NEXT"], 5) for r in sub]),
                conv[has_next],
                rng,
            )
            for cond in ["L0", *conditions]
        },
    }

    # 4. Timing model. words[d] is the length of utterance i-d; utterance i is
    #    the listener's, i-1 the agent's previous reply, and so on. A recall job
    #    costs c seconds. Reply text exists when the agent starts speaking, so a
    #    job launched from utterance i-1 has d(i-1)+d(i) seconds before the
    #    listener stops; one launched from i-3 has d(i-3)+...+d(i); etc. A job
    #    launched on a streaming partial at fraction p has (1-p)*d(i).
    words = np.array([r["words"] for r in rows], dtype=float)  # (n, 7)
    w3 = {cond: per_turn[(3, cond)] for cond in conditions}
    timing: dict = {"cost_s": COSTS.tolist()}
    for label, rate in RATES.items():
        dur = words / rate
        slack = {
            "L1": dur[:, :2].sum(axis=1),
            "L3": dur[:, :4].sum(axis=1),
            "L5": dur[:, :6].sum(axis=1),
            "P25": 0.75 * dur[:, 0],
            "P50": 0.50 * dur[:, 0],
            "P75": 0.25 * dur[:, 0],
        }
        policies = {
            "turn": ["L1", "L3", "L5"],
            "stream": ["P75", "P50", "P25", "L1", "L3", "L5"],  # freshest first
        }
        for policy, order in policies.items():
            curve = np.zeros((len(rows), len(COSTS)))
            lag_used = np.full((len(rows), len(COSTS)), np.nan)
            for j, c in enumerate(COSTS):
                chosen = np.zeros(len(rows))
                done = np.zeros(len(rows), dtype=bool)
                for cond in order:
                    ready = (slack[cond] >= c) & ~done
                    chosen[ready] = w3[cond][ready]
                    done |= ready
                curve[:, j] = chosen
                lag_used[:, j] = done
            timing[f"{label}/{policy}"] = boot_ci(curve, conv, rng)
            timing[f"{label}/{policy}/empty_fraction"] = (1 - lag_used.mean(axis=0)).tolist()
        timing[f"{label}/utterance_s_median"] = float(np.median(dur[:, 0]))
        timing[f"{label}/L1_slack_s_median"] = float(np.median(slack["L1"]))
    out["timing"] = timing

    (ROOT / "results" / "e1_summary.json").write_text(json.dumps(out, indent=1))

    def show(key: str, triple: list) -> None:
        print(f"  {key:14s} {triple[0]:.3f} [{triple[1]:.3f}, {triple[2]:.3f}]")

    print(out["n_turns"], "turns,", out["n_sessions"], "sessions; memory", out["memory_size"])
    for w in WINDOWS:
        print(f"overlap@5 with fresh retrieval, w={w}")
        for cond in conditions:
            show(cond, agree[f"k5/w{w}/{cond}"])
    print("top-1 retained in top-5 (w=3)")
    for cond in ("L1", "L2", "L3", "P50", "P75", "RAND"):
        show(cond, out["top1_retained"][f"w3/{cond}"])
    print("by shift quartile (w=3), Q1 (continuing) .. Q4 (abrupt)")
    for cond, quartiles in out["by_shift"].items():
        print(f"  {cond:5s}", " ".join(f"{q[0]:.3f}" for q in quartiles))
    print("hindsight overlap@5 with memories retrieved by the next utterance (w=3)")
    for cond in ("L0", "L1", "L2", "L3", "P50", "P75", "RAND"):
        show(cond, out["hindsight"][cond])
    for label in RATES:
        print(label, "median utterance s", round(timing[f"{label}/utterance_s_median"], 1),
              "median L1 slack s", round(timing[f"{label}/L1_slack_s_median"], 1))
        for policy in ("turn", "stream"):
            mean = timing[f"{label}/{policy}"][0]
            picks = [0, 10, 16, 20, 25, 30, 35, 40]
            print(f"  {policy:6s}", " ".join(f"{COSTS[j]:g}s:{mean[j]:.2f}" for j in picks))


if __name__ == "__main__":
    main()
