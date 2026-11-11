"""Experiment 2 analysis. Reads the sealed bundles under ``results/e2`` and
writes ``results/e2_summary.json`` plus ``results/e2_trials.csv``.

Confidence intervals are 95% percentile intervals from a bootstrap that
resamples cases (the unit of authoring); the five trials of a case stay
together.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

from circumstances.artifacts import verify_bundle

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("none", "tool", "blocking", "lag1", "prefetch50", "hybrid")
CLASSES = ("asked-continuing", "asked-shift", "unprompted", "abstain")
BOOT = 10000
SEED = 20261110


def load() -> list[dict]:
    source = yaml.safe_load((ROOT / "pack-src" / "tessaly.yaml").read_text())
    meta = {c["id"]: c for c in source["cases"]}
    rows: list[dict] = []
    for condition in CONDITIONS:
        bundles = sorted((ROOT / "results" / "e2" / condition).iterdir())
        assert len(bundles) == 1, condition
        assert verify_bundle(bundles[0]) == [], condition
        for path in sorted((bundles[0] / "trials").glob("*.json")):
            trial = json.loads(path.read_text())
            case = meta[trial["case_id"].split("/")[-1]]
            events = trial["trajectory"]["events"]
            obs = {e["name"]: e["value"] for e in events if e["kind"] == "observation"}
            met = {e["name"]: e["value"] for e in events if e["kind"] == "metric"}
            ctx = [e["components"]["recall"] for e in events if e["kind"] == "context_snapshot"]
            reply = [e["content"] for e in events if e["kind"] == "message" and e["role"] == "assistant"]
            passed = bool(trial["grades"]) and all(g["status"] == "pass" for g in trial["grades"])
            rows.append(
                {
                    "condition": condition,
                    "case": case["id"],
                    "class": case["class"],
                    "continuity": case["continuity"],
                    "attempt": trial["attempt"],
                    "seed": trial["seed"],
                    "passed": passed,
                    "abstained": bool(obs.get("reply.abstained")),
                    "format_ok": bool(obs.get("reply.format_ok")),
                    "repaired": bool(obs.get("reply.repaired", False)),
                    "searched": any(e["kind"] == "tool_call" for e in events),
                    "gold_in_context": bool(case["gold"]) and any(g in ctx[-1] for g in case["gold"]) if ctx else False,
                    "error": trial["trajectory"]["error"] or "",
                    "pre_generation_ms": met.get("path.pre_generation_ms", float("nan")),
                    "total_ms": met.get("path.total_ms", float("nan")),
                    "offpath_recall_ms": met.get("offpath.recall_ms", float("nan")),
                    "reply": reply[-1] if reply else "",
                }
            )
    return rows


def case_boot(rows: list[dict], key: str, rng: np.random.Generator) -> list[float]:
    """Mean of a 0/1 field with a case-level bootstrap CI."""
    by_case: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        by_case[r["case"]].append(float(r[key]))
    means = np.array([np.mean(v) for v in by_case.values()])
    draws = rng.integers(0, len(means), size=(BOOT, len(means)))
    lo, hi = np.percentile(means[draws].mean(axis=1), [2.5, 97.5])
    return [float(means.mean()), float(lo), float(hi)]


def paired_diff(rows: list[dict], a: str, b: str, rng: np.random.Generator) -> list[float]:
    """Pass-rate difference a - b over the same cases, case-level bootstrap."""
    rate: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["condition"] in (a, b):
            rate[r["case"]][r["condition"]].append(float(r["passed"]))
    diffs = np.array([np.mean(v[a]) - np.mean(v[b]) for v in rate.values()])
    draws = rng.integers(0, len(diffs), size=(BOOT, len(diffs)))
    lo, hi = np.percentile(diffs[draws].mean(axis=1), [2.5, 97.5])
    return [float(diffs.mean()), float(lo), float(hi)]


def main() -> None:
    rows = load()
    rng = np.random.default_rng(SEED)
    with open(ROOT / "results" / "e2_trials.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    out: dict = {"n_trials": len(rows), "by_condition": {}}
    for condition in CONDITIONS:
        sub = [r for r in rows if r["condition"] == condition]
        recall = [r for r in sub if r["class"] != "abstain"]
        asked = [r for r in sub if r["class"].startswith("asked")]
        entry: dict = {
            "trials": len(sub),
            "errors": sum(bool(r["error"]) for r in sub),
            "format_errors": sum(not r["format_ok"] for r in sub),
            "repaired": sum(r["repaired"] for r in sub),
            "searched_rate": float(np.mean([r["searched"] for r in sub])),
            "recall_pass": case_boot(recall, "passed", rng),
            "overall_pass": case_boot(sub, "passed", rng),
            "gold_in_context": case_boot(recall, "gold_in_context", rng),
            "pre_generation_ms": {
                "median": float(np.median([r["pre_generation_ms"] for r in sub])),
                "p90": float(np.percentile([r["pre_generation_ms"] for r in sub], 90)),
                "mean": float(np.mean([r["pre_generation_ms"] for r in sub])),
            },
            "total_ms": {
                "median": float(np.median([r["total_ms"] for r in sub])),
                "p90": float(np.percentile([r["total_ms"] for r in sub], 90)),
                "mean": float(np.mean([r["total_ms"] for r in sub])),
            },
            "offpath_recall_ms_median": float(np.median([r["offpath_recall_ms"] for r in sub])),
            # What a miss looks like when a question was asked.
            "asked_outcomes": {
                "stated_fact": float(np.mean([r["passed"] for r in asked])),
                "abstained": float(np.mean([(not r["passed"]) and r["abstained"] for r in asked])),
                "other_answer": float(
                    np.mean([(not r["passed"]) and not r["abstained"] for r in asked])
                ),
            },
            "by_class": {},
            "by_continuity": {},
        }
        for cls in CLASSES:
            part = [r for r in sub if r["class"] == cls]
            cases: dict[str, list[bool]] = defaultdict(list)
            for r in part:
                cases[r["case"]].append(r["passed"])
            entry["by_class"][cls] = {
                "pass": case_boot(part, "passed", rng),
                "pass_all_5": float(np.mean([all(v) for v in cases.values()])),
                "pass_any_5": float(np.mean([any(v) for v in cases.values()])),
                "gold_in_context": float(np.mean([r["gold_in_context"] for r in part])),
                "searched": float(np.mean([r["searched"] for r in part])),
            }
        for cont in ("continuing", "abrupt"):
            part = [r for r in recall if r["continuity"] == cont]
            entry["by_continuity"][cont] = {
                "pass": case_boot(part, "passed", rng),
                "gold_in_context": float(np.mean([r["gold_in_context"] for r in part])),
                "n_cases": len({r["case"] for r in part}),
            }
        out["by_condition"][condition] = entry

    recall_rows = [r for r in rows if r["class"] != "abstain"]
    out["paired_recall_diff"] = {
        f"{a}-{b}": paired_diff(recall_rows, a, b, rng)
        for a, b in (
            ("blocking", "lag1"),
            ("blocking", "prefetch50"),
            ("blocking", "tool"),
            ("prefetch50", "lag1"),
            ("tool", "lag1"),
            ("hybrid", "lag1"),
            ("blocking", "hybrid"),
        )
    }
    (ROOT / "results" / "e2_summary.json").write_text(json.dumps(out, indent=1))

    # Mediation: pass rate of recall trials given whether a target note was in context.
    def given(sub: list[dict], present: bool) -> list:
        hits = [r["passed"] for r in sub if r["gold_in_context"] is present]
        return [float(np.mean(hits)) if hits else None, len(hits)]

    extra = {
        condition: {
            "pass_given_gold": given([r for r in recall_rows if r["condition"] == condition], True),
            "pass_given_no_gold": given([r for r in recall_rows if r["condition"] == condition], False),
        }
        for condition in CONDITIONS
    }
    with_memory = [r for r in recall_rows if r["condition"] != "none"]
    extra["pooled"] = {
        "pass_given_gold": given(with_memory, True),
        "pass_given_no_gold": given(with_memory, False),
    }
    (ROOT / "results" / "e2_extra.json").write_text(json.dumps(extra, indent=1))

    def pct(triple: list[float]) -> str:
        return f"{100 * triple[0]:5.1f} [{100 * triple[1]:4.0f},{100 * triple[2]:4.0f}]"

    print(f"{'condition':11s} {'recall pass':18s} " + " ".join(f"{c[:14]:>14s}" for c in CLASSES)
          + "  gold  srch  pre50 pre90 tot50  fmt rep err")
    for condition, e in out["by_condition"].items():
        print(
            f"{condition:11s} {pct(e['recall_pass']):18s} "
            + " ".join(f"{100 * e['by_class'][c]['pass'][0]:14.1f}" for c in CLASSES)
            + f"  {100 * e['gold_in_context'][0]:4.0f}  {100 * e['searched_rate']:4.0f}"
            + f"  {e['pre_generation_ms']['median']:5.0f} {e['pre_generation_ms']['p90']:5.0f}"
            + f" {e['total_ms']['median']:5.0f}  {e['format_errors']:3d} {e['repaired']:3d} {e['errors']:3d}"
        )
    print("pass^5 (all five trials pass), by class")
    for condition, e in out["by_condition"].items():
        print(f"  {condition:11s}", " ".join(f"{100 * e['by_class'][c]['pass_all_5']:6.0f}" for c in CLASSES))
    print("recall pass by continuity (continuing / abrupt), and gold in context")
    for condition, e in out["by_condition"].items():
        c, a = e["by_continuity"]["continuing"], e["by_continuity"]["abrupt"]
        print(f"  {condition:11s} {pct(c['pass'])} gold {100 * c['gold_in_context']:3.0f} | "
              f"{pct(a['pass'])} gold {100 * a['gold_in_context']:3.0f}")
    print("asked cases: stated fact / abstained / other answer")
    for condition, e in out["by_condition"].items():
        o = e["asked_outcomes"]
        print(f"  {condition:11s} {100 * o['stated_fact']:5.1f} {100 * o['abstained']:5.1f} {100 * o['other_answer']:5.1f}")
    print("paired differences in recall pass rate (percentage points)")
    for name, triple in out["paired_recall_diff"].items():
        print(f"  {name:22s} {pct(triple)}")


if __name__ == "__main__":
    main()
