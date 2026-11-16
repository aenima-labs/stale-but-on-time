"""Experiment 3 analysis: the async-recall pack run against the product.

Reads the sealed bundles and the trial table under ``results/e3-kodama`` (the
reported run), ``results/e3-kodama-run1`` (the first run, kept for disclosure)
``results/e3-kodama-hosted`` (the product on hosted models),
``results/e3-kodama-hosted-run1`` (the first hosted run, four conditions) and
``results/e3-kodama-hosted-luna`` (the hosted pilot, one trial per case), checks
every seal and that the trial table agrees with the grades stored in the bundles,
and writes ``results/e3_summary.json`` and ``results/e3_regraded.csv``.

The trial table (``trials.csv``) is produced by the product's own evaluation
code (``evals/recall/analyze.py`` in the product repository) from the events
stored in the bundles. Intervals are 95% percentile intervals from a bootstrap
over cases, as in Experiment 2.

Grades are the sealed ones with the first correction of Experiment 2, applied to
every run alike: a recall trial passes only if a key starts at the start of a
word. The sealed evaluator matches substrings, so the key "Mori" matched inside
"memories" and counted a refusal as a pass. ``regraded_rows`` returns the trial
table with the corrected ``passed`` (``passed_sealed`` keeps the sealed grade);
``trials.csv`` itself is left as the product wrote it, and every changed trial
is listed in ``results/e3_regraded.csv``.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import numpy as np
import yaml

from circumstances.artifacts import verify_bundle
from e2_analyze import BOOT, SEED, case_boot, paired_diff

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("a-tool", "b-backthought", "c-blocking", "d-blocking-backthought", "e-backthought-tool")
CLASSES = ("asked-continuing", "asked-shift", "unprompted", "abstain")
RUNS = {"run2": "e3-kodama", "run1": "e3-kodama-run1", "hosted": "e3-kodama-hosted",
        "hosted1": "e3-kodama-hosted-run1", "pilot": "e3-kodama-hosted-luna"}
PAIRED = ("run2", "hosted", "hosted1")  # runs whose conditions are compared case by case
# The first hosted run has no bundle for the last condition (see its NOTE.md).
RUN_CONDITIONS = {"hosted1": CONDITIONS[:4]}
PAIRS = (
    ("c-blocking", "b-backthought"),
    ("c-blocking", "a-tool"),
    ("d-blocking-backthought", "c-blocking"),
    ("e-backthought-tool", "a-tool"),
    ("e-backthought-tool", "b-backthought"),
)


def flag(value: str) -> bool:
    return value == "True"


def bundle_of(run_dir: Path, condition: str) -> Path:
    bundles = [p for p in (run_dir / condition).iterdir() if p.is_dir()]
    assert len(bundles) == 1, condition
    return bundles[0]


def key_patterns(bundle: Path) -> dict[str, re.Pattern]:
    """Per recall case, the keys of the sealed text match, required to start a word.

    The keys are read from the pack stored in the bundle: a list of strings
    (``contains_any``) or, for the cases whose numbers may be spoken, a regex.
    """
    patterns: dict[str, re.Pattern] = {}
    for path in (bundle / "pack" / "rules").glob("*/cases/*/case.yaml"):
        case = yaml.safe_load(path.read_text())
        parts: list[str] = []
        for evaluator in case.get("evaluators") or []:
            config = evaluator.get("config") or {}
            parts += [re.escape(str(k)) for k in config.get("contains_any") or []]
            if config.get("regex"):
                parts.append(config["regex"])
        if parts:
            patterns[case["id"].split("/")[-1]] = re.compile(
                r"(?<![A-Za-z])(?:" + "|".join(parts) + ")", re.IGNORECASE
            )
    return patterns


def regraded_rows(run_dir: Path) -> list[dict]:
    """The trial table as strings, with ``passed`` corrected by the word-start rule."""
    csv.field_size_limit(10**9)
    with open(run_dir / "trials.csv", newline="") as handle:
        rows = list(csv.DictReader(handle))
    patterns = {c: key_patterns(bundle_of(run_dir, c)) for c in sorted({r["condition"] for r in rows})}
    for r in rows:
        r["passed_sealed"] = r["passed"]
        pattern = patterns[r["condition"]].get(r["case"])
        if r["class"] != "abstain" and flag(r["passed"]):
            assert pattern is not None, (run_dir, r["case"])
            r["passed"] = str(bool(pattern.search(r["reply"])))
        r["regraded"] = str(r["passed"] != r["passed_sealed"])
    return rows


def load(run_dir: Path, conditions: tuple[str, ...] = CONDITIONS) -> tuple[list[dict], dict]:
    rows = regraded_rows(run_dir)
    assert {r["condition"] for r in rows} == set(conditions), run_dir
    meta: dict = {}
    for condition in conditions:
        info = json.loads((run_dir / condition / "condition.json").read_text())
        bundle = bundle_of(run_dir, condition)
        assert verify_bundle(bundle) == [], condition
        graded = 0
        for path in (bundle / "trials").glob("*.json"):
            trial = json.loads(path.read_text())
            graded += bool(trial["grades"]) and all(g["status"] == "pass" for g in trial["grades"])
        table = sum(flag(r["passed_sealed"]) for r in rows if r["condition"] == condition)
        assert graded == table == info["passed"], (condition, graded, table, info["passed"])
        meta[condition] = {k: info[k] for k in ("backend_commit", "started_at", "finished_at", "trials")}
        meta[condition]["model"] = info["settings_document"]["models"]["realtime"]["model"]
    for r in rows:
        for key in ("passed", "passed_sealed", "regraded", "gold_in_wm", "searched", "templated",
                    "abstain_tool", "abstain_recorded", "abstain_text"):
            if key in r:
                r[key] = flag(r[key])
        r["path_ms"] = float(r["path_ms"])
        # Declined by any route: the abstain tool, the refusal sentence, words, or
        # an abstain call that the model wrote out as text.
        if "abstain_recorded" in r:
            r["declined_any"] = r["abstain_recorded"] or r["abstain_text"] or r["templated"] or "abstain(" in r["reply"]
    return rows, meta


def load_cost(run_dir: Path, conditions: tuple[str, ...] = CONDITIONS) -> dict | None:
    """Tokens, model calls and cost per condition, for runs whose model calls were metered.

    ``telemetry.csv`` has one row per trial, written by the product's evaluation code
    from the spans of each model request; ``cost_usd_upper`` also bills in full the
    calls that the product stopped early, which report no usage.
    """
    path = run_dir / "telemetry.csv"
    if not path.exists():
        return None
    rows = list(csv.DictReader(open(path)))
    out: dict = {"conditions": {}}
    for condition in conditions:
        sub = [r for r in rows if r["condition"] == condition]
        out["conditions"][condition] = {
            "trials": len(sub),
            "model_calls_per_trial": float(np.mean([float(r["model_calls"]) for r in sub])),
            "input_tokens_per_trial": float(np.mean([float(r["input_tokens"]) for r in sub])),
            "output_tokens_per_trial": float(np.mean([float(r["output_tokens"]) for r in sub])),
            "cost_usd_per_trial": float(np.mean([float(r["cost_usd"]) for r in sub])),
            "cost_usd": float(sum(float(r["cost_usd"]) for r in sub)),
            "cost_usd_upper": float(sum(float(r["cost_usd_upper"]) for r in sub)),
        }
    out["cost_usd"] = sum(c["cost_usd"] for c in out["conditions"].values())
    out["cost_usd_upper"] = sum(c["cost_usd_upper"] for c in out["conditions"].values())
    # The embedding requests are not metered per trial; cost.json estimates them from
    # the characters embedded and adds them to the totals of the run.
    totals = json.loads((run_dir / "cost.json").read_text())
    out["embeddings_usd"] = totals["embeddings_estimate"]["cost_usd"]
    out["total_usd"] = totals["total_usd"]
    out["total_usd_upper"] = totals["total_usd_upper"]
    assert abs(out["cost_usd"] - totals["run"]["cost_usd"]) < 0.005, run_dir
    return out


def median_ms(rows: list[dict], key: str) -> float | None:
    """Median of a timing column; None when the condition never records it."""
    values = [float(r[key]) for r in rows if r.get(key) not in (None, "", "nan", "None")]
    return float(np.median(values)) if values else None


def summarise(rows: list[dict], rng: np.random.Generator, conditions: tuple[str, ...] = CONDITIONS) -> dict:
    out: dict = {}
    for condition in conditions:
        sub = [r for r in rows if r["condition"] == condition]
        recall = [r for r in sub if r["class"] != "abstain"]
        abstain = [r for r in sub if r["class"] == "abstain"]
        entry: dict = {
            "trials": len(sub),
            "errors": sum(bool(r["error"]) for r in sub),
            "regraded_recall_to_fail": sum(r["regraded"] for r in recall),
            "recall_pass": case_boot(recall, "passed", rng),
            "gold_in_wm": case_boot(recall, "gold_in_wm", rng),
            "searched_rate": float(np.mean([r["searched"] for r in sub])),
            "templated": sum(r["templated"] for r in sub),
            "path_ms": {  # a trial that ended in an error has no reply-path time
                "median": float(np.nanmedian([r["path_ms"] for r in sub])),
                "p90": float(np.nanpercentile([r["path_ms"] for r in sub], 90)),
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
    changed: list[dict] = []
    for name, folder in RUNS.items():
        conditions = RUN_CONDITIONS.get(name, CONDITIONS)
        rows, meta = load(ROOT / "results" / folder, conditions)
        changed += [
            {"run": folder, "condition": r["condition"], "case": r["case"], "attempt": r["attempt"],
             "passed_sealed": r["passed_sealed"], "passed": r["passed"], "reply": r["reply"]}
            for r in rows if r["regraded"]
        ]
        result[name] = {"n_trials": len(rows), "meta": meta, "by_condition": summarise(rows, rng, conditions)}
        cost = load_cost(ROOT / "results" / folder, conditions)
        if cost:
            result[name]["cost"] = cost
        if name in PAIRED:
            recall = [r for r in rows if r["class"] != "abstain"]
            result[name]["paired_recall_diff"] = {
                f"{a}|{b}": paired_diff(recall, a, b, rng)
                for a, b in PAIRS
                if a in conditions and b in conditions
            }
            loaded = [r for r in recall if r["condition"] in ("b-backthought", "c-blocking", "d-blocking-backthought")]
            result[name]["loaded_conditions"] = {
                "pass_given_gold": [float(np.mean([r["passed"] for r in loaded if r["gold_in_wm"]])),
                                    sum(r["gold_in_wm"] for r in loaded)],
                "pass_given_no_gold": [float(np.mean([r["passed"] for r in loaded if not r["gold_in_wm"]])),
                                       sum(not r["gold_in_wm"] for r in loaded)],
            }
    (ROOT / "results" / "e3_summary.json").write_text(json.dumps(result, indent=1))
    with open(ROOT / "results" / "e3_regraded.csv", "w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["run", "condition", "case", "attempt", "passed_sealed", "passed", "reply"]
        )
        writer.writeheader()
        writer.writerows(changed)

    for name in RUNS:
        print(name)
        for condition, e in result[name]["by_condition"].items():
            rp = e["recall_pass"]
            print(
                f"  {condition:24s} recall {100 * rp[0]:5.1f} [{100 * rp[1]:3.0f},{100 * rp[2]:3.0f}]  "
                + " ".join(f"{100 * e['by_class'][c]['pass'][0]:5.0f}" for c in CLASSES)
                + f"  goldWM {100 * e['gold_in_wm'][0]:3.0f}  srch {100 * e['searched_rate']:3.0f}"
                + f"  regr {e['regraded_recall_to_fail']:2d}  tmpl {e['templated']:3d}  path {e['path_ms']['median']:5.0f}/{e['path_ms']['p90']:5.0f}"
                + f"  abst {e['abstain']}  |gold {e['pass_given_gold']}  |no gold {e['pass_given_no_gold']}"
            )
    for name in PAIRED:
        print(name, "paired:", {k: [round(100 * x) for x in v] for k, v in result[name]["paired_recall_diff"].items()})
        print(name, "loaded conditions:", result[name]["loaded_conditions"])


if __name__ == "__main__":
    main()
