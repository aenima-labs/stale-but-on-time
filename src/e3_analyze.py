"""Experiment 3 analysis: the async-recall pack run against the product.

Reads the sealed bundles and the trial table under ``results/e3-kodama`` (the
reported run) and ``results/e3-kodama-run1`` (the first run, kept for
disclosure), checks every seal and that the trial table agrees with the grades
stored in the bundles, and writes ``results/e3_summary.json``.

The trial table (``trials.csv``) is produced by the product's own evaluation
code (``evals/recall/analyze.py`` in the product repository) from the events
stored in the bundles. Intervals are 95% percentile intervals from a bootstrap
over cases, as in Experiment 2.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from circumstances.artifacts import verify_bundle
from e2_analyze import BOOT, SEED, case_boot, paired_diff

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("a-tool", "b-backthought", "c-blocking", "d-blocking-backthought", "e-backthought-tool")
CLASSES = ("asked-continuing", "asked-shift", "unprompted", "abstain")
RUNS = {"run2": "e3-kodama", "run1": "e3-kodama-run1"}


def flag(value: str) -> bool:
    return value == "True"


def load(run_dir: Path) -> tuple[list[dict], dict]:
    rows = list(csv.DictReader(open(run_dir / "trials.csv")))
    meta: dict = {}
    for condition in CONDITIONS:
        info = json.loads((run_dir / condition / "condition.json").read_text())
        bundles = [p for p in (run_dir / condition).iterdir() if p.is_dir()]
        assert len(bundles) == 1, condition
        assert verify_bundle(bundles[0]) == [], condition
        graded = 0
        for path in (bundles[0] / "trials").glob("*.json"):
            trial = json.loads(path.read_text())
            graded += bool(trial["grades"]) and all(g["status"] == "pass" for g in trial["grades"])
        table = sum(flag(r["passed"]) for r in rows if r["condition"] == condition)
        assert graded == table == info["passed"], (condition, graded, table, info["passed"])
        meta[condition] = {k: info[k] for k in ("backend_commit", "started_at", "finished_at", "trials")}
        meta[condition]["model"] = info["settings_document"]["models"]["realtime"]["model"]
    for r in rows:
        for key in ("passed", "gold_in_wm", "searched", "templated", "abstain_tool",
                    "abstain_recorded", "abstain_text"):
            if key in r:
                r[key] = flag(r[key])
        r["path_ms"] = float(r["path_ms"])
        # Declined by any route: the abstain tool, the refusal sentence, words, or
        # an abstain call that the model wrote out as text.
        if "abstain_recorded" in r:
            r["declined_any"] = r["abstain_recorded"] or r["abstain_text"] or r["templated"] or "abstain(" in r["reply"]
    return rows, meta


def median_ms(rows: list[dict], key: str) -> float | None:
    """Median of a timing column; None when the condition never records it."""
    values = [float(r[key]) for r in rows if r.get(key) not in (None, "", "nan", "None")]
    return float(np.median(values)) if values else None


def summarise(rows: list[dict], rng: np.random.Generator) -> dict:
    out: dict = {}
    for condition in CONDITIONS:
        sub = [r for r in rows if r["condition"] == condition]
        recall = [r for r in sub if r["class"] != "abstain"]
        abstain = [r for r in sub if r["class"] == "abstain"]
        entry: dict = {
            "trials": len(sub),
            "errors": sum(bool(r["error"]) for r in sub),
            "recall_pass": case_boot(recall, "passed", rng),
            "gold_in_wm": case_boot(recall, "gold_in_wm", rng),
            "searched_rate": float(np.mean([r["searched"] for r in sub])),
            "templated": sum(r["templated"] for r in sub),
            "path_ms": {
                "median": float(np.median([r["path_ms"] for r in sub])),
                "p90": float(np.percentile([r["path_ms"] for r in sub], 90)),
            },
            "llm_ms_median": median_ms(sub, "llm_total_ms"),
            "blocking_ms_median": median_ms(sub, "blocking_ms"),
            "offpath_recall_ms_median": median_ms(sub, "offpath_recall_ms"),
            "by_class": {},
            "abstain": {
                key: float(np.mean([r[key] for r in abstain]))
                for key in ("abstain_tool", "abstain_recorded", "abstain_text", "declined_any")
                if key in abstain[0]
            },
        }
        for cls in CLASSES:
            part = [r for r in sub if r["class"] == cls]
            entry["by_class"][cls] = {
                "pass": case_boot(part, "passed", rng),
                "searched": float(np.mean([r["searched"] for r in part])),
            }
        with_gold = [r["passed"] for r in recall if r["gold_in_wm"]]
        without = [r["passed"] for r in recall if not r["gold_in_wm"]]
        entry["pass_given_gold"] = [float(np.mean(with_gold)) if with_gold else None, len(with_gold)]
        entry["pass_given_no_gold"] = [float(np.mean(without)) if without else None, len(without)]
        out[condition] = entry
    return out


def main() -> None:
    rng = np.random.default_rng(SEED)
    result: dict = {"bootstrap": BOOT}
    for name, folder in RUNS.items():
        rows, meta = load(ROOT / "results" / folder)
        result[name] = {"n_trials": len(rows), "meta": meta, "by_condition": summarise(rows, rng)}
        if name == "run2":
            recall = [r for r in rows if r["class"] != "abstain"]
            result[name]["paired_recall_diff"] = {
                f"{a}|{b}": paired_diff(recall, a, b, rng)
                for a, b in (
                    ("c-blocking", "b-backthought"),
                    ("c-blocking", "a-tool"),
                    ("d-blocking-backthought", "c-blocking"),
                    ("e-backthought-tool", "a-tool"),
                    ("e-backthought-tool", "b-backthought"),
                )
            }
            loaded = [r for r in recall if r["condition"] in ("b-backthought", "c-blocking", "d-blocking-backthought")]
            result[name]["loaded_conditions"] = {
                "pass_given_gold": [float(np.mean([r["passed"] for r in loaded if r["gold_in_wm"]])),
                                    sum(r["gold_in_wm"] for r in loaded)],
                "pass_given_no_gold": [float(np.mean([r["passed"] for r in loaded if not r["gold_in_wm"]])),
                                       sum(not r["gold_in_wm"] for r in loaded)],
            }
    (ROOT / "results" / "e3_summary.json").write_text(json.dumps(result, indent=1))

    for name in RUNS:
        print(name)
        for condition, e in result[name]["by_condition"].items():
            rp = e["recall_pass"]
            print(
                f"  {condition:24s} recall {100 * rp[0]:5.1f} [{100 * rp[1]:3.0f},{100 * rp[2]:3.0f}]  "
                + " ".join(f"{100 * e['by_class'][c]['pass'][0]:5.0f}" for c in CLASSES)
                + f"  goldWM {100 * e['gold_in_wm'][0]:3.0f}  srch {100 * e['searched_rate']:3.0f}"
                + f"  tmpl {e['templated']:3d}  path {e['path_ms']['median']:5.0f}/{e['path_ms']['p90']:5.0f}"
                + f"  abst {e['abstain']}  |gold {e['pass_given_gold']}  |no gold {e['pass_given_no_gold']}"
            )
    print("paired:", {k: [round(100 * x) for x in v] for k, v in result["run2"]["paired_recall_diff"].items()})
    print("loaded conditions:", result["run2"]["loaded_conditions"])


if __name__ == "__main__":
    main()
