"""Analysis of the experiment with slow recall (design/slow-recall.md).

Four agents on four kinds of turn. The kinds are fixed by the cases:

  A  the turn stays with the memory in play, the cheap lookup finds the note
  B  the turn brings a new need,              the cheap lookup finds the note
  C  the turn stays with the memory in play, the cheap lookup misses the note
  D  the turn brings a new need,              the cheap lookup misses the note

Grading is that of Experiment 2 (``e2_analyze``): a key must begin a word, and a
refusal in plain words counts as an abstention.

Usage:  uv run python src/slow_analyze.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import yaml

from circumstances.artifacts import verify_bundle
from e2_analyze import REFUSAL, SEED, case_boot, case_level, key_starts_word, paired_diff

ROOT = Path(__file__).resolve().parents[1]
RUN = "slow-recall"
CONDITIONS = ("blocking", "deep", "deep_stale", "both")  # fast fresh, deep fresh, deep stale, both
CHECK = "none"  # no memory, on the 20 new cases only
CELLS = {
    "A": ("asked-carry",),
    "B": ("asked-continuing", "asked-shift", "unprompted"),
    "C": ("hard-carry",),
    "D": ("hard-shift",),
}
CONTRASTS = (("deep_stale", "blocking"), ("both", "blocking"), ("deep", "blocking"), ("both", "deep_stale"))


def cell_of(cls: str) -> str:
    return next((cell for cell, classes in CELLS.items() if cls in classes), "abstain")


def load() -> list[dict]:
    source = yaml.safe_load((ROOT / "pack-src" / "tessaly.yaml").read_text())
    meta = {c["id"]: c for c in source["cases"]}
    rows: list[dict] = []
    for condition in (CHECK, *CONDITIONS):
        bundles = sorted((ROOT / "results" / RUN / condition).iterdir())
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
            sealed = bool(trial["grades"]) and all(g["status"] == "pass" for g in trial["grades"])
            text = reply[-1] if reply else ""
            format_ok = bool(obs.get("reply.format_ok"))
            refused_in_words = (not format_ok) and bool(REFUSAL.search(text))
            if case["class"] == "abstain":
                passed = sealed or refused_in_words
            else:
                passed = sealed and key_starts_word(text, case["keys"])
            gold = case["gold"]
            loaded = ctx[-1] if ctx else []
            rated = obs.get("recall.rated") or {}
            candidates = rated.get("candidates", [])
            rank = next((candidates.index(g) + 1 for g in gold if g in candidates), None)
            rows.append(
                {
                    "condition": condition,
                    "case": case["id"],
                    "class": case["class"],
                    "cell": cell_of(case["class"]),
                    "attempt": trial["attempt"],
                    "seed": trial["seed"],
                    "passed": passed,
                    "passed_sealed": sealed,
                    "abstained": bool(obs.get("reply.abstained")) or refused_in_words,
                    "gold_in_context": bool(gold) and any(g in loaded for g in gold),
                    "notes_loaded": len(loaded),
                    # the deeper recall: where the cheap lookup ranked the target among the
                    # 16 candidates, how the model rated it, and whether the job selected it
                    "candidates_read": len(candidates),
                    "gold_candidate_rank": rank,
                    "gold_score": rated["scores"][rank - 1] if rank else None,
                    "gold_selected": bool(gold) and any(g in rated.get("selected", []) for g in gold),
                    "ready": obs.get("recall.ready"),
                    "available_ms": met.get("offpath.available_ms", float("nan")),
                    "offpath_recall_ms": met.get("offpath.recall_ms", float("nan")),
                    "pre_generation_ms": met.get("path.pre_generation_ms", float("nan")),
                    "total_ms": met.get("path.total_ms", float("nan")),
                    "llm_calls": met.get("path.llm_calls", float("nan")),
                    "error": trial["trajectory"]["error"] or "",
                    "started_at": trial["trajectory"]["started_at"],
                    "reply": text,
                }
            )
    return rows


def share(rows: list[dict], key: str) -> float | None:
    return float(np.mean([bool(r[key]) for r in rows])) if rows else None


def cases_with(rows: list[dict], key: str) -> int:
    """Cases in which the field holds in most trials (retrieval is the same in all five)."""
    by_case: dict[str, list[bool]] = {}
    for r in rows:
        by_case.setdefault(r["case"], []).append(bool(r[key]))
    return int(sum(np.mean(v) > 0.5 for v in by_case.values()))


def main() -> None:
    rows = load()
    rng = np.random.default_rng(SEED)
    main_rows = [r for r in rows if r["condition"] in CONDITIONS]
    out: dict = {
        "run": RUN,
        "trials": len(main_rows),
        "errors": sum(bool(r["error"]) for r in rows),
        "cases": {cell: len({r["case"] for r in main_rows if r["cell"] == cell}) for cell in (*CELLS, "abstain")},
        "candidates_read": max(r["candidates_read"] for r in main_rows),
        "by_condition": {},
        "contrasts": {},
    }

    for condition in CONDITIONS:
        sub = [r for r in main_rows if r["condition"] == condition]
        entry: dict = {
            "trials": len(sub),
            "reply_ms_median": float(np.median([r["total_ms"] for r in sub])),
            "wait_ms_median": float(np.median([r["pre_generation_ms"] for r in sub])),
            "notes_loaded_mean": float(np.mean([r["notes_loaded"] for r in sub])),
            "abstain_pass": case_boot([r for r in sub if r["cell"] == "abstain"], "passed", rng),
            "by_cell": {},
        }
        for cell in CELLS:
            part = [r for r in sub if r["cell"] == cell]
            entry["by_cell"][cell] = {
                "pass": case_boot(part, "passed", rng),
                "gold_in_context": share(part, "gold_in_context"),
                "gold_cases": cases_with(part, "gold_in_context"),
                "cases": len({r["case"] for r in part}),
                "reply_ms_median": float(np.median([r["total_ms"] for r in part])),
            }
            if condition != "blocking":
                # what the deeper recall itself delivered, whether or not it was ready in time
                entry["by_cell"][cell]["gold_among_candidates"] = share(part, "gold_candidate_rank")
                entry["by_cell"][cell]["gold_selected"] = share(part, "gold_selected")
                entry["by_cell"][cell]["gold_selected_cases"] = cases_with(part, "gold_selected")
            if condition in ("deep_stale", "both"):
                entry["by_cell"][cell]["ready"] = share(part, "ready")
                entry["by_cell"][cell]["ready_cases"] = cases_with(part, "ready")
        recall = [r for r in sub if r["cell"] != "abstain"]
        entry["pass_given_gold"] = [share([r for r in recall if r["gold_in_context"]], "passed"),
                                    sum(r["gold_in_context"] for r in recall)]
        entry["pass_given_no_gold"] = [share([r for r in recall if not r["gold_in_context"]], "passed"),
                                       sum(not r["gold_in_context"] for r in recall)]
        if condition == "deep":
            job = [r["pre_generation_ms"] for r in sub]
        elif condition in ("deep_stale", "both"):
            job = [r["offpath_recall_ms"] for r in sub]
        else:
            job = []
        if job:
            entry["deep_recall_ms"] = {"median": float(np.median(job)), "min": float(np.min(job)),
                                       "p90": float(np.percentile(job, 90)), "max": float(np.max(job))}
        if condition in ("deep_stale", "both"):
            entry["ready"] = share(sub, "ready")
            entry["not_ready_trials"] = sum(r["ready"] is False for r in sub)
            entry["not_ready_cases"] = sorted({r["case"] for r in sub if r["ready"] is False})
            entry["available_ms"] = {"median": float(np.median([r["available_ms"] for r in sub])),
                                     "min": float(np.min([r["available_ms"] for r in sub])),
                                     "max": float(np.max([r["available_ms"] for r in sub]))}
            ready = [r for r in recall if r["ready"]]
            entry["pass_given_ready_by_cell"] = {
                cell: [share([r for r in ready if r["cell"] == cell], "passed"),
                       len([r for r in ready if r["cell"] == cell])]
                for cell in CELLS
            }
        out["by_condition"][condition] = entry

    # Contrasts fixed in the design: in each cell, a paired difference over cases.
    for a, b in CONTRASTS:
        out["contrasts"][f"{a}|{b}"] = {}
        for cell in CELLS:
            part = [r for r in main_rows if r["cell"] == cell]
            out["contrasts"][f"{a}|{b}"][cell] = {
                "diff": paired_diff(part, a, b, rng),
                **case_level(part, a, b),
            }

    check = [r for r in rows if r["condition"] == CHECK]
    out["no_memory_check"] = {"trials": len(check), "passed": sum(r["passed"] for r in check),
                              "cases": len({r["case"] for r in check})}

    (ROOT / "results" / f"{RUN}_summary.json").write_text(json.dumps(out, indent=1))
    with open(ROOT / "results" / f"{RUN}_trials.csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    # A sample for reading the replies against the grades: 15 trials of each agent, at random.
    sample_rng = np.random.default_rng(SEED)
    sample = []
    for condition in CONDITIONS:
        sub = [r for r in main_rows if r["condition"] == condition]
        sample += [sub[i] for i in sorted(sample_rng.choice(len(sub), size=15, replace=False))]
    keys = {c["id"]: "|".join(str(k) for k in c.get("keys", []))
            for c in yaml.safe_load((ROOT / "pack-src" / "tessaly.yaml").read_text())["cases"]}
    with open(ROOT / "results" / f"{RUN}_audit_sample.csv", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["condition", "case", "class", "attempt", "passed", "target_note_loaded", "keys", "reply",
                         "grade_is_right"])
        for r in sample:
            writer.writerow([r["condition"], r["case"], r["class"], r["attempt"], r["passed"],
                             r["gold_in_context"], keys[r["case"]], r["reply"], ""])

    print(f"{out['trials']} trials, {out['errors']} errors; no-memory check {out['no_memory_check']}")
    print(f"{'':12s}" + "".join(f"{cell:>22s}" for cell in CELLS) + f"{'abstain':>10s}{'reply s':>9s}{'wait s':>8s}")
    for condition, e in out["by_condition"].items():
        cells = "".join(
            f"{100 * c['pass'][0]:6.0f} [{100 * c['pass'][1]:3.0f},{100 * c['pass'][2]:3.0f}] g{c['gold_cases']:2d}/{c['cases']:2d}"
            for c in e["by_cell"].values()
        )
        print(f"{condition:12s}{cells}{100 * e['abstain_pass'][0]:10.0f}"
              f"{e['reply_ms_median'] / 1000:9.1f}{e['wait_ms_median'] / 1000:8.2f}")
    for condition in ("deep", "deep_stale", "both"):
        e = out["by_condition"][condition]
        print(condition, "deep recall ms", {k: round(v) for k, v in e["deep_recall_ms"].items()},
              "ready", e.get("ready"), "not ready in", e.get("not_ready_cases"))
        print("   target selected by the job, by cell:",
              {cell: round(100 * c["gold_selected"]) for cell, c in e["by_cell"].items()})
    for name, cells in out["contrasts"].items():
        print(name, {cell: [round(100 * x) for x in c["diff"]] + [f"{c['ahead']}+ {c['behind']}-"]
                     for cell, c in cells.items()})


if __name__ == "__main__":
    main()
