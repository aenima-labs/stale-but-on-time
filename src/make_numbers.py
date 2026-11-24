"""Write every number the paper cites, straight from the result files.

Produces ``paper/numbers.tex`` (macros used in running text) and the table
bodies ``paper/tab-*.tex``. Nothing in the manuscript is typed by hand.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
e1 = json.loads((ROOT / "results" / "e1_summary.json").read_text())
e2 = json.loads((ROOT / "results" / "e2_summary.json").read_text())
extra = json.loads((ROOT / "results" / "e2_extra.json").read_text())
trials = list(csv.DictReader(open(ROOT / "results" / "e2_trials.csv")))
# The main run without its control class: the 40 cases that every other run also has.
# Shares of trials with a search and times to a reply are taken from these, so that
# they compare with the other runs.
trials40 = [r for r in trials if r["class"] != "asked-carry"]

macros: dict[str, str] = {}


def put(name: str, value: str) -> None:
    assert name.isalpha() and name not in macros, name
    macros[name] = value


def f2(x: float) -> str:
    return f"{x:.2f}"


def ci2(t: list[float]) -> str:
    return f"[{t[1]:.2f}, {t[2]:.2f}]"


def pct(x: float) -> str:
    return f"{100 * x:.0f}"


def signed(x: float) -> str:
    """Integer with a typographic minus sign."""
    return f"$-${abs(x):.0f}" if round(x) < 0 else f"{x:.0f}"


def pctci(t: list[float]) -> str:
    return f"[{100 * t[1]:.0f}, {100 * t[2]:.0f}]"


def pct_with_ci(t: list[float]) -> str:
    """A rate with its interval for a table cell; the interval is left out when every
    case gave the same result and it has no width."""
    return pct(t[0]) if t[1] == t[2] else f"{pct(t[0])} {pctci(t)}"


# ---------------------------------------------------------------- Experiment 1
ag = e1["agreement"]
put("EoneTurns", f"{e1['n_turns']:,}")
put("EoneSessions", str(e1["n_sessions"]))
put("EoneMemMedian", f"{e1['memory_size']['median']:.0f}")
put("EoneMemMin", str(e1["memory_size"]["min"]))
put("EoneMemMax", str(e1["memory_size"]["max"]))
put("EoneWordsMean", f"{e1['words_per_utterance']['mean']:.0f}")
for tag, key in (
    ("Lone", "L1"), ("Ltwo", "L2"), ("Lthree", "L3"), ("Lsix", "L6"), ("Rand", "RAND"),
    ("Pquarter", "P25"), ("Phalf", "P50"), ("Pthreeq", "P75"),
):
    put(f"Ov{tag}", f2(ag[f"k5/w3/{key}"][0]))
    put(f"Ov{tag}CI", ci2(ag[f"k5/w3/{key}"]))
put("OvWoneLone", f2(ag["k5/w1/L1"][0]))
put("OvWonePhalf", f2(ag["k5/w1/P50"][0]))
put("OvWfiveLone", f2(ag["k5/w5/L1"][0]))
put("OvWfivePhalf", f2(ag["k5/w5/P50"][0]))
put("TopOneLone", pct(e1["top1_retained"]["w3/L1"][0]))
put("TopOnePhalf", pct(e1["top1_retained"]["w3/P50"][0]))
put("ShiftLoneQone", f2(e1["by_shift"]["L1"][0][0]))
put("ShiftLoneQfour", f2(e1["by_shift"]["L1"][3][0]))
put("ShiftPhalfQone", f2(e1["by_shift"]["P50"][0][0]))
put("ShiftPhalfQfour", f2(e1["by_shift"]["P50"][3][0]))
h = e1["hindsight"]
put("HindTurns", f"{h['n_turns']:,}")
for tag, key in (("Fresh", "L0"), ("Lone", "L1"), ("Lthree", "L3"), ("Phalf", "P50"), ("Rand", "RAND")):
    put(f"Hind{tag}", f"{h[key][0]:.3f}")
    put(f"Hind{tag}CI", f"[{h[key][1]:.3f}, {h[key][2]:.3f}]")
put("HindRetained", pct((h["L1"][0] - h["RAND"][0]) / (h["L0"][0] - h["RAND"][0])))
# Two fresh retrievals that differ only in the window: the reference for the overlap.
wc = e1["window_change"]
put("OvFreshWfive", f2(wc["w3_vs_w5"][0]))
put("OvFreshWfiveCI", ci2(wc["w3_vs_w5"]))
put("OvFreshWone", f2(wc["w3_vs_w1"][0]))
t = e1["timing"]
cost = t["cost_s"]


def at(policy: str, seconds: float, rate: str = "150wpm") -> str:
    j = int(np.argmin(np.abs(np.array(cost) - seconds)))
    return f2(t[f"{rate}/{policy}"][0][j])


put("UttMedianSec", f"{t['150wpm/utterance_s_median']:.1f}")
put("SlackMedianSec", f"{t['150wpm/L1_slack_s_median']:.0f}")
put("TimTurnFive", at("turn", 5.4))
put("TimTurnTwelve", at("turn", 12.1))
put("TimTurnTwentySeven", at("turn", 27))
put("TimStreamTenth", at("stream", 0.1))
put("TimStreamOne", at("stream", 1.3))
put("TimStreamTwo", at("stream", 2.4))
put("TimStreamFive", at("stream", 5.4))
put("TimStreamOneFast", at("stream", 1.3, "210wpm"))
put("TimTurnTwelveFast", at("turn", 12.1, "210wpm"))

# ---------------------------------------------------------------- Experiment 2
bc = e2["by_condition"]
TAG = {"none": "None", "tool": "Tool", "blocking": "Block", "lag1": "Lag",
       "prefetch50": "Pre", "hybrid": "Hyb"}
put("EtwoTrials", f"{e2['n_trials']:,}")
for cond, tag in TAG.items():
    e = bc[cond]
    put(f"Rec{tag}", pct(e["recall_pass"][0]))
    put(f"Rec{tag}CI", pctci(e["recall_pass"]))
    put(f"Gold{tag}", pct(e["gold_in_context"][0]))
    put(f"Abst{tag}", pct(e["by_class"]["abstain"]["pass"][0]))
    put(f"Srch{tag}", pct(float(np.mean([r["searched"] == "True" for r in trials40 if r["condition"] == cond]))))
    for cls, ctag in (("asked-continuing", "Cont"), ("asked-shift", "Shift"), ("unprompted", "Unp")):
        put(f"{ctag}{tag}", pct(e["by_class"][cls]["pass"][0]))
    o = e["asked_outcomes"]
    put(f"Stated{tag}", pct(o["stated_fact"]))
    put(f"Declined{tag}", pct(o["abstained"]))
    put(f"Other{tag}", pct(o["other_answer"]))
for name, tag in (
    ("blocking-lag1", "BlockLag"), ("blocking-prefetch50", "BlockPre"), ("blocking-tool", "BlockTool"),
    ("prefetch50-lag1", "PreLag"), ("hybrid-lag1", "HybLag"), ("blocking-hybrid", "BlockHyb"),
    ("tool-lag1", "ToolLag"),
):
    d = e2["paired_recall_diff"][name]
    put(f"Diff{tag}", signed(100 * d[0]))
    put(f"Diff{tag}CI", f"[{signed(100 * d[1])}, {signed(100 * d[2])}]")
put("PassGivenGold", pct(extra["pooled"]["pass_given_gold"][0]))
put("PassGivenGoldN", str(extra["pooled"]["pass_given_gold"][1]))
put("PassGivenNoGoldN", str(extra["pooled"]["pass_given_no_gold"][1]))
put("PreBlockMed", f"{bc['blocking']['pre_generation_ms']['median']:.0f}")
put("PreBlockPninety", f"{bc['blocking']['pre_generation_ms']['p90']:.0f}")
put("PreToolMed", f"{bc['tool']['pre_generation_ms']['median']:.0f}")
put("PreToolPninety", f"{bc['tool']['pre_generation_ms']['p90']:.0f}")
put("PreHybMed", f"{bc['hybrid']['pre_generation_ms']['median']:.0f}")
put("PreHybPninety", f"{bc['hybrid']['pre_generation_ms']['p90']:.0f}")
put("OffpathMed", f"{bc['lag1']['offpath_recall_ms_median']:.0f}")
put("RepairedHyb", str(bc["hybrid"]["repaired"]))
put("RepairedTool", str(bc["tool"]["repaired"]))
put("FormatErrors", str(sum(bc[c]["format_errors"] for c in bc)))
put("RunErrors", str(sum(bc[c]["errors"] for c in bc)))


def rate(cond: str, cls: str, field: str) -> str:
    sub = [r for r in trials if r["condition"] == cond and r["class"] == cls]
    return pct(float(np.mean([r[field] == "True" for r in sub])))


put("SrchShiftTool", rate("tool", "asked-shift", "searched"))
put("SrchShiftHyb", rate("hybrid", "asked-shift", "searched"))
put("SrchUnpTool", rate("tool", "unprompted", "searched"))
put("SrchUnpHyb", rate("hybrid", "unprompted", "searched"))
put("SrchContHyb", rate("hybrid", "asked-continuing", "searched"))

# The control class of pack 1.1.0 (answer in the note in play); never pooled into "recall".
CARRY = "asked-carry"
put("EtwoCases", str(len({r["case"] for r in trials})))
put("EtwoPerCondition", str(e2["n_trials"] // len(TAG)))
for cond, tag in TAG.items():
    c = bc[cond]["by_class"][CARRY]
    put(f"Carry{tag}", pct(c["pass"][0]))
    put(f"Carry{tag}CI", pctci(c["pass"]))
    put(f"CarryGold{tag}", pct(c["gold_in_context"]))
    put(f"CarrySrch{tag}", pct(c["searched"]))
for name, tag in (("blocking-lag1", "BlockLag"), ("blocking-prefetch50", "BlockPre"), ("blocking-tool", "BlockTool")):
    d = e2["paired_carry_diff"][name]
    put(f"CarryDiff{tag}", signed(100 * d[0]))
    put(f"CarryDiff{tag}CI", f"[{signed(100 * d[1])}, {signed(100 * d[2])}]")
put("CarryPassGivenGold", pct(extra["carry_pooled"]["pass_given_gold"][0]))
put("CarryPassGivenGoldN", str(extra["carry_pooled"]["pass_given_gold"][1]))
put("CarryNoGoldN", str(extra["carry_pooled"]["pass_given_no_gold"][1]))
put("CarryNoGoldPassed", str(round((extra["carry_pooled"]["pass_given_no_gold"][0] or 0)
                                   * extra["carry_pooled"]["pass_given_no_gold"][1])))


def gold_cases(rows: list[dict], cond: str, classes: tuple[str, ...]) -> tuple[int, int]:
    """Cases in which the target note was in context, and cases in all. Local retrieval
    is deterministic, so a case has the note in all of its trials or in none."""
    by_case: dict[str, list[bool]] = {}
    for r in rows:
        if r["condition"] == cond and r["class"] in classes:
            by_case.setdefault(r["case"], []).append(r["gold_in_context"] == "True")
    # A hosted embedding model need not return the same vector twice, so a case
    # counts when the note was there in most of its trials.
    return sum(np.mean(v) > 0.5 for v in by_case.values()), len(by_case)


NEW_NEED = ("asked-continuing", "asked-shift", "unprompted")
for cond, tag in (("lag1", "Lag"), ("prefetch50", "Pre"), ("blocking", "Block")):
    put(f"GoldCases{tag}", str(gold_cases(trials, cond, NEW_NEED)[0]))
    put(f"CarryGoldCases{tag}", str(gold_cases(trials, cond, (CARRY,))[0]))
for name, tag in (("blocking-lag1", "BlockLag"), ("blocking-prefetch50", "BlockPre"), ("blocking-tool", "BlockTool")):
    c = e2["case_level"][name]
    put(f"CaseAhead{tag}", str(c["ahead"]))
    put(f"CaseBehind{tag}", str(c["behind"]))
    put(f"CaseLevel{tag}", str(c["level"]))
    put(f"CaseP{tag}", "< 0.001" if c["sign_flip_p"] < 0.001 else f"= {c['sign_flip_p']:.2f}")

# The first full run of the main setting (pack 1.0.0, 40 cases, 10 November): prefix Fr.
fr = json.loads((ROOT / "results" / "e2-run1_summary.json").read_text())
put("FrTrials", f"{fr['n_trials']:,}")
for cond, tag in TAG.items():
    put(f"FrRec{tag}", pct(fr["by_condition"][cond]["recall_pass"][0]))
d = fr["paired_recall_diff"]["blocking-lag1"]
put("FrDiffBlockLag", signed(100 * d[0]))
put("FrDiffBlockLagCI", f"[{signed(100 * d[1])}, {signed(100 * d[2])}]")
put("FrMaxDiff", f"{max(abs(100 * (fr['by_condition'][c]['recall_pass'][0] - bc[c]['recall_pass'][0])) for c in TAG):.0f}")


def new_need_rate(cond: str, without: str) -> float:
    """New-need pass rate of a condition with one case left out (mean over cases)."""
    by_case: dict[str, list[bool]] = {}
    for r in trials:
        if r["condition"] == cond and r["class"] in NEW_NEED and r["case"] != without:
            by_case.setdefault(r["case"], []).append(r["passed"] == "True")
    return float(np.mean([np.mean(v) for v in by_case.values()]))


# The case that the review judged unfair (a second note fits the remark as well).
put("NoApprRecBlock", pct(new_need_rate("blocking", "amb-apprenticeship")))
put("NoApprRecLag", pct(new_need_rate("lag1", "amb-apprenticeship")))

# ------------------------------------------------- robustness runs (Section 6.3)
# Same pack, same seeds, a different model setting. The reasoning run shared the
# GPU with another process for part of its duration (results/e2-think_NOTES.md);
# latency is taken only from trials that started outside that window.
ROBUST = {"e2-think": "Th", "e2-qwen3": "Qw", "e2-anthropic": "Hs"}  # Hs: hosted model
DIRTY = {"e2-think": ("2026-11-11T12:44", "2026-11-11T13:20")}
MIN_CLEAN = 100  # trials needed to report a latency


def load_run(run: str) -> tuple[dict, list[dict]]:
    summary = json.loads((ROOT / "results" / f"{run}_summary.json").read_text())
    rows = list(csv.DictReader(open(ROOT / "results" / f"{run}_trials.csv")))
    return summary, rows


def reply_seconds(run: str, rows: list[dict], cond: str) -> float | None:
    """Median time to a complete reply, in seconds, over uncontaminated trials."""
    lo, hi = DIRTY.get(run, ("9", "9"))
    clean = [float(r["total_ms"]) for r in rows
             if r["condition"] == cond and not lo <= r["started_at"] < hi]
    return float(np.median(clean)) / 1000 if len(clean) >= MIN_CLEAN else None


def class_rate(rows: list[dict], cond: str, cls: str, field: str) -> str:
    sub = [r for r in rows if r["condition"] == cond and r["class"] == cls]
    return pct(float(np.mean([r[field] == "True" for r in sub])))


robust = {"e2": (e2, trials40)}
for run, prefix in ROBUST.items():
    summary, rows = load_run(run)
    robust[run] = (summary, rows)
    rb = summary["by_condition"]
    put(f"{prefix}Trials", f"{summary['n_trials']:,}")
    for cond, tag in TAG.items():
        e = rb[cond]
        put(f"{prefix}Rec{tag}", pct(e["recall_pass"][0]))
        put(f"{prefix}Rec{tag}CI", pctci(e["recall_pass"]))
        put(f"{prefix}Gold{tag}", pct(e["gold_in_context"][0]))
        put(f"{prefix}Abst{tag}", pct(e["by_class"]["abstain"]["pass"][0]))
        put(f"{prefix}Declined{tag}", pct(e["asked_outcomes"]["abstained"]))
        put(f"{prefix}Other{tag}", pct(e["asked_outcomes"]["other_answer"]))
        for cls, ctag in (("asked-continuing", "Cont"), ("asked-shift", "Shift"), ("unprompted", "Unp")):
            put(f"{prefix}{ctag}{tag}", pct(e["by_class"][cls]["pass"][0]))
        sec = reply_seconds(run, rows, cond)
        if sec is not None:
            put(f"{prefix}Reply{tag}", f"{sec:.1f}")
    for name, tag in (("blocking-lag1", "BlockLag"), ("blocking-tool", "BlockTool"),
                      ("prefetch50-lag1", "PreLag"), ("blocking-hybrid", "BlockHyb"),
                      ("hybrid-lag1", "HybLag")):
        d = summary["paired_recall_diff"][name]
        put(f"{prefix}Diff{tag}", signed(100 * d[0]))
        put(f"{prefix}Diff{tag}CI", f"[{signed(100 * d[1])}, {signed(100 * d[2])}]")
    ex = json.loads((ROOT / "results" / f"{run}_extra.json").read_text())["pooled"]
    put(f"{prefix}PassGivenGold", pct(ex["pass_given_gold"][0]))
    put(f"{prefix}PassGivenGoldN", str(ex["pass_given_gold"][1]))
    put(f"{prefix}PassGivenNoGold", pct(ex["pass_given_no_gold"][0]))
    put(f"{prefix}PassGivenNoGoldN", str(ex["pass_given_no_gold"][1]))
    put(f"{prefix}PassedNoGold", str(round(ex["pass_given_no_gold"][0] * ex["pass_given_no_gold"][1])))
    put(f"{prefix}SrchShiftHyb", class_rate(rows, "hybrid", "asked-shift", "searched"))
    put(f"{prefix}SrchUnpHyb", class_rate(rows, "hybrid", "unprompted", "searched"))
    put(f"{prefix}SrchContHyb", class_rate(rows, "hybrid", "asked-continuing", "searched"))
    put(f"{prefix}SrchUnpTool", class_rate(rows, "tool", "unprompted", "searched"))
    put(f"{prefix}SrchHyb", pct(rb["hybrid"]["searched_rate"]))
    put(f"{prefix}SrchTool", pct(rb["tool"]["searched_rate"]))
    put(f"{prefix}RepairedHyb", str(rb["hybrid"]["repaired"]))
    put(f"{prefix}RepairedTool", str(rb["tool"]["repaired"]))
    put(f"{prefix}FormatErrors", str(sum(rb[c]["format_errors"] for c in rb)))
    put(f"{prefix}RunErrors", str(sum(rb[c]["errors"] for c in rb)))
    put(f"{prefix}PreHybMed", f"{rb['hybrid']['pre_generation_ms']['median'] / 1000:.1f}")
    put(f"{prefix}PreToolMed", f"{rb['tool']['pre_generation_ms']['median'] / 1000:.1f}")
    put(f"{prefix}RegradedRecall", str(sum(rb[c]["regraded"]["recall_to_fail"] for c in rb)))
    put(f"{prefix}RegradedAbstain", str(sum(rb[c]["regraded"]["abstain_to_pass"] for c in rb)))
for cond, tag in TAG.items():
    put(f"Reply{tag}", f"{reply_seconds('e2', trials40, cond):.1f}")
put("RegradedRecall", str(sum(bc[c]["regraded"]["recall_to_fail"] for c in bc)))
put("RegradedAbstain", str(sum(bc[c]["regraded"]["abstain_to_pass"] for c in bc)))
put("RobustRuns", str(len(ROBUST)))

# The hosted run: time and money from its telemetry (exact token counts of the providers).
hs_tel = json.loads((ROOT / "results" / "e2-anthropic" / "telemetry_summary.json").read_text())
hs_c = hs_tel["conditions"]
put("HsRecallMs", f"{hs_c['blocking']['latency_ms']['recall:reply_path']['median']:.0f}")
put("HsRecallMsPninety", f"{hs_c['blocking']['latency_ms']['recall:reply_path']['p90']:.0f}")
for cond, tag in TAG.items():
    put(f"HsCost{tag}", f"{100 * hs_c[cond]['per_trial']['cost_usd']['mean']:.2f}")  # US cents per trial
put("HsCostRun", f"{sum(hs_c[c]['totals']['cost_usd'] for c in hs_c):.2f}")
put("HsCallsHyb", f"{hs_c['hybrid']['per_trial']['chat_calls']['mean']:.1f}")
no_gold = [json.loads((ROOT / "results" / f"{run}_extra.json").read_text())["pooled"]["pass_given_no_gold"]
           for run in robust]
put("AllNoGoldN", f"{sum(n for _, n in no_gold):,}")
put("AllNoGoldPassed", str(round(sum(rate * n for rate, n in no_gold))))
put("AllTrials", f"{sum(summary['n_trials'] for summary, _ in robust.values()):,}")
for cond, tag in (("lag1", "Lag"), ("prefetch50", "Pre"), ("blocking", "Block")):
    put(f"HsGoldCases{tag}", str(gold_cases(robust["e2-anthropic"][1], cond, NEW_NEED)[0]))

# ------------------------------------------------ Experiment 3 (the product)
e3 = json.loads((ROOT / "results" / "e3_summary.json").read_text())
KTAG = {"a-tool": "Tool", "b-backthought": "Lag", "c-blocking": "Block",
        "d-blocking-backthought": "Both", "e-backthought-tool": "Hyb"}
k2, k1 = e3["run2"], e3["run1"]
put("KTrials", f"{k2['n_trials']:,}")
put("KErrors", str(sum(e["errors"] for e in k2["by_condition"].values())))
put("KTemplated", str(sum(e["templated"] for e in k2["by_condition"].values())))
put("KfTemplated", str(sum(e["templated"] for e in k1["by_condition"].values())))
for cond, tag in KTAG.items():
    e, f = k2["by_condition"][cond], k1["by_condition"][cond]
    put(f"KRec{tag}", pct(e["recall_pass"][0]))
    put(f"KRec{tag}CI", pctci(e["recall_pass"]))
    put(f"KGold{tag}", pct(e["gold_in_wm"][0]))
    put(f"KSrch{tag}", pct(e["searched_rate"]))
    put(f"KPath{tag}", f"{e['path_ms']['median'] / 1000:.1f}")
    put(f"KAbstTool{tag}", pct(e["abstain"]["abstain_recorded"]))
    put(f"KAbstWords{tag}", pct(e["abstain"]["abstain_text"]))
    for cls, ctag in (("asked-continuing", "Cont"), ("asked-shift", "Shift"), ("unprompted", "Unp")):
        put(f"K{ctag}{tag}", pct(e["by_class"][cls]["pass"][0]))
    put(f"KfRec{tag}", pct(f["recall_pass"][0]))
    put(f"KfTmpl{tag}", str(f["templated"]))
for name, tag in (("c-blocking|b-backthought", "BlockLag"), ("c-blocking|a-tool", "BlockTool"),
                  ("d-blocking-backthought|c-blocking", "BothBlock"), ("e-backthought-tool|a-tool", "HybTool")):
    d = k2["paired_recall_diff"][name]
    put(f"KDiff{tag}", signed(100 * d[0]))
    put(f"KDiff{tag}CI", f"[{signed(100 * d[1])}, {signed(100 * d[2])}]")
guessed = [1 - e["abstain"]["declined_any"] for e in k2["by_condition"].values()]
put("KGuessMin", pct(min(guessed)))
put("KGuessMax", pct(max(guessed)))
put("KPassGivenGold", pct(k2["loaded_conditions"]["pass_given_gold"][0]))
put("KPassGivenGoldN", str(k2["loaded_conditions"]["pass_given_gold"][1]))
put("KNoGoldN", str(k2["loaded_conditions"]["pass_given_no_gold"][1]))
put("KNoGoldPassed", str(round(k2["loaded_conditions"]["pass_given_no_gold"][0] * k2["loaded_conditions"]["pass_given_no_gold"][1])))
put("KBlockMs", f"{k2['by_condition']['c-blocking']['blocking_ms_median']:.0f}")
put("KOffpathMs", f"{k2['by_condition']['b-backthought']['offpath_recall_ms_median']:.0f}")
put("KLlmTool", f"{k2['by_condition']['a-tool']['llm_ms_median'] / 1000:.1f}")
put("KLlmBlock", f"{k2['by_condition']['c-blocking']['llm_ms_median'] / 1000:.1f}")

# ----------------------------- Experiment 3 on hosted models (prefix KH)
kh = e3["hosted"]
put("KHTrials", f"{kh['n_trials']:,}")
put("KHTrialsPerCase", str(kh["n_trials"] // 200))
put("KHModel", kh["meta"]["c-blocking"]["model"])
put("KHErrors", str(sum(e["errors"] for e in kh["by_condition"].values())))
put("KHTemplated", str(sum(e["templated"] for e in kh["by_condition"].values())))
for cond, tag in KTAG.items():
    e = kh["by_condition"][cond]
    put(f"KHRec{tag}", pct(e["recall_pass"][0]))
    put(f"KHRec{tag}CI", pctci(e["recall_pass"]))
    put(f"KHGold{tag}", pct(e["gold_in_wm"][0]))
    put(f"KHSrch{tag}", pct(e["searched_rate"]))
    put(f"KHPath{tag}", f"{e['path_ms']['median'] / 1000:.1f}")
    put(f"KHAbstTool{tag}", pct(e["abstain"]["abstain_recorded"]))
    put(f"KHUnp{tag}", pct(e["by_class"]["unprompted"]["pass"][0]))
    put(f"KHCost{tag}", f"{100 * kh['cost']['conditions'][cond]['cost_usd_per_trial']:.2f}")
    put(f"KHCalls{tag}", f"{kh['cost']['conditions'][cond]['model_calls_per_trial']:.1f}")
for name, tag in (("c-blocking|b-backthought", "BlockLag"), ("c-blocking|a-tool", "BlockTool"),
                  ("d-blocking-backthought|c-blocking", "BothBlock"), ("e-backthought-tool|a-tool", "HybTool"),
                  ("e-backthought-tool|b-backthought", "HybLag")):
    d = kh["paired_recall_diff"][name]
    put(f"KHDiff{tag}", signed(100 * d[0]))
    put(f"KHDiff{tag}CI", f"[{signed(100 * d[1])}, {signed(100 * d[2])}]")
kh_guessed = [1 - e["abstain"]["declined_any"] for e in kh["by_condition"].values()]
put("KHGuessMax", pct(max(kh_guessed)))
kh_tool = [e["abstain"]["abstain_recorded"] for e in kh["by_condition"].values()]
put("KHAbstToolMin", pct(min(kh_tool)))
put("KHAbstToolMax", pct(max(kh_tool)))
put("KHBlockMs", f"{kh['by_condition']['c-blocking']['blocking_ms_median']:.0f}")
put("KHCostRun", f"{kh['cost']['total_usd']:.2f}")
put("KHCostRunUpper", f"{kh['cost']['total_usd_upper']:.2f}")
# All hosted runs of Experiment 3 that the paper reports: the main one and the later ones.
put("KHCostAll", f"{kh['cost']['total_usd'] + sum(e3[k]['cost']['total_usd'] for k in ('hosted_carry', 'hosted_bringup') if k in e3):.2f}")
# The pilot and the first hosted run, which the paper names but does not report as results.
put("KHCostEarlier", f"{e3['hosted1']['cost']['total_usd'] + e3['pilot']['cost']['total_usd']:.2f}")
# The first hosted run: four conditions on the product commit before the queue fix.
kf = e3["hosted1"]
put("KHFirstTrials", f"{kf['n_trials']:,}")
put("KHFirstErrors", str(sum(e["errors"] for e in kf["by_condition"].values())))
for cond, tag in list(KTAG.items())[:4]:
    put(f"KHFirstRec{tag}", pct(kf["by_condition"][cond]["recall_pass"][0]))
d = kf["paired_recall_diff"]["c-blocking|b-backthought"]
put("KHFirstDiffBlockLag", signed(100 * d[0]))
put("KHFirstDiffBlockLagCI", f"[{signed(100 * d[1])}, {signed(100 * d[2])}]")
put("KHFirstCostRun", f"{kf['cost']['total_usd']:.2f}")
kp = e3["pilot"]
# Trials whose pass the word-start rule turned into a failure, per run.
def regraded(run: dict) -> str:
    return str(sum(e["regraded_recall_to_fail"] for e in run["by_condition"].values()))


put("KRegraded", str(int(regraded(k2)) + int(regraded(k1))))
put("KHRegraded", regraded(kh))
put("KHFirstRegraded", regraded(kf))
put("KPilotRegraded", regraded(kp))
put("KPilotTrials", str(kp["n_trials"]))
put("KPilotRecBlock", pct(kp["by_condition"]["c-blocking"]["recall_pass"][0]))
put("KPilotRecLag", pct(kp["by_condition"]["b-backthought"]["recall_pass"][0]))

# ----------------- later runs of Experiment 3: control cases and the sixth condition
# A run that has not been delivered yet shows as "??" in the manuscript.
MISSING = r"\textbf{??}"
BRINGUP = "a2-tool-bringup"
for key, prefix in (("carry", "KCarry"), ("hosted_carry", "KHCarry")):
    run = e3.get(key)
    put(f"{prefix}Trials", str(run["n_trials"]) if run else MISSING)
    put(f"{prefix}Errors", str(sum(e["errors"] for e in run["by_condition"].values())) if run else MISSING)
    for cond, tag in KTAG.items():
        c = run["by_condition"][cond]["by_class"]["asked-carry"] if run else None
        put(f"{prefix}{tag}", pct(c["pass"][0]) if c else MISSING)
        put(f"{prefix}{tag}CI", pctci(c["pass"]) if c else "")
        put(f"{prefix}GoldCases{tag}", str(c["gold_cases"]) if c else MISSING)
    d = run["paired_diff"]["c-blocking|b-backthought"] if run else None
    put(f"{prefix}DiffBlockLag", signed(100 * d[0]) if d else MISSING)
    put(f"{prefix}DiffBlockLagCI", f"[{signed(100 * d[1])}, {signed(100 * d[2])}]" if d else "")
for key, prefix in (("bringup", "KBring"), ("hosted_bringup", "KHBring")):
    run = e3.get(key)
    e = run["by_condition"][BRINGUP] if run else None
    put(f"{prefix}Trials", str(run["n_trials"]) if run else MISSING)
    put(f"{prefix}Rec", pct(e["recall_pass"][0]) if e else MISSING)
    put(f"{prefix}RecCI", pctci(e["recall_pass"]) if e else "")
    put(f"{prefix}Unp", pct(e["by_class"]["unprompted"]["pass"][0]) if e else MISSING)
    put(f"{prefix}SrchUnp", pct(e["by_class"]["unprompted"]["searched"]) if e else MISSING)
    put(f"{prefix}Path", f"{e['path_ms_median'] / 1000:.1f}" if e else MISSING)
    put(f"{prefix}Guess", pct(1 - e["abstain"]["declined_any"]) if e else MISSING)
    # Unprompted passes as counts, and those with neither the memory nor a search behind them.
    u = e["unprompted_support"] if e else None
    put(f"{prefix}UnpPassed", str(u["passed"]) if u else MISSING)
    put(f"{prefix}UnpTrials", str(u["trials"]) if u else MISSING)
    put(f"{prefix}UnpLoose", str(u["unsupported"]) if u else MISSING)
    put(f"{prefix}UnpSupported", str(u["passed"] - u["unsupported"]) if u else MISSING)
    ab = e["abstain"] if e else None
    put(f"{prefix}AbstErrors", str(ab["errors"]) if ab else MISSING)
    put(f"{prefix}AbstTool", pct(ab["abstain_recorded"]) if ab else MISSING)
    put(f"{prefix}AbstToolRan", pct(ab["abstain_tool_count"] / (ab["trials"] - ab["errors"])) if ab else MISSING)
    for name, tag in (("against_shipped", "VsShipped"), ("blocking_against_bringup", "BlockVs")):
        for part, ptag in (("new_need", "Rec"), ("unprompted", "Unp")):
            d = run[name][part] if run else None
            put(f"{prefix}{tag}{ptag}", signed(100 * d[0]) if d else MISSING)
            put(f"{prefix}{tag}{ptag}CI", f"[{signed(100 * d[1])}, {signed(100 * d[2])}]" if d else "")
# The same count in the reported runs, over all five conditions.
for macro, run in (("KLooseMain", k2), ("KHLooseMain", kh)):
    loose = sum(e["unprompted_support"]["unsupported"] for e in run["by_condition"].values())
    put(macro, str(loose) if loose else "none")
# The share of unprompted trials with a search in the shipped condition, for comparison.
put("KSrchUnpTool", pct(k2["by_condition"]["a-tool"]["by_class"]["unprompted"]["searched"]))
# The shipped search tool on the version of the sixth condition, once that run is delivered;
# until then, and for the hosted models (one version throughout), the reported run.
base = e3.get("bringup_baseline")
ship = base["by_condition"]["a-tool"] if base else k2["by_condition"]["a-tool"]
put("KShipUnp", pct(ship["by_class"]["unprompted"]["pass"][0]))
put("KShipSrchUnp", pct(ship["by_class"]["unprompted"]["searched"]))
put("KShipRec", pct(ship["recall_pass"][0]))
put("KShipVersion", "on the same version" if base else "in the reported run, on an earlier version")
put("KHSrchUnpTool", pct(kh["by_condition"]["a-tool"]["by_class"]["unprompted"]["searched"]))

# ------------------------------------ what waiting costs in time (Section 8)
# One row per set-up: the wait for recall on the reply path, and the median time
# to a complete reply in the four conditions that load or search memories.
import figures  # noqa: E402  (the set-ups and the curve of Figure "correct by time")

CLOUD = "e2-cloudrun-l4-timing"  # one trial per case on a cloud GPU; timing only
deploy = [
    ("Agent, local models, laptop", bc["blocking"]["pre_generation_ms"]["median"],
     [reply_seconds("e2", trials40, c) for c in ("lag1", "blocking", "tool", "hybrid")]),
]
if (ROOT / "results" / f"{CLOUD}_summary.json").exists():
    cloud_summary, cloud_rows = load_run(CLOUD)
    cb = cloud_summary["by_condition"]
    cloud_reply = [float(np.median([float(r["total_ms"]) for r in cloud_rows if r["condition"] == c])) / 1000
                   for c in ("lag1", "blocking", "tool", "hybrid")]
    deploy.append(("Agent, local models, cloud GPU",
                   cb["blocking"]["pre_generation_ms"]["median"], cloud_reply))
    put("CloudRecallMs", f"{cb['blocking']['pre_generation_ms']['median']:.0f}")
    put("CloudTrials", str(cloud_summary["n_trials"]))
    cloud_machine = json.loads((ROOT / "results" / CLOUD / "machine.json").read_text())
    put("CloudCost", f"{cloud_machine['cost_usd']:.2f}")
    for c, tag in (("lag1", "Lag"), ("blocking", "Block"), ("tool", "Tool"), ("hybrid", "Hyb")):
        put(f"CloudReply{tag}", f"{cloud_reply[('lag1', 'blocking', 'tool', 'hybrid').index(c)]:.1f}")
hs_rows = robust["e2-anthropic"][1]
deploy.append(("Agent, hosted models",
               hs_c["blocking"]["latency_ms"]["recall:reply_path"]["median"],
               [reply_seconds("e2-anthropic", hs_rows, c) for c in ("lag1", "blocking", "tool", "hybrid")]))
deploy.append(("Product, local models, laptop", k2["by_condition"]["c-blocking"]["blocking_ms_median"],
               [k2["by_condition"][c]["path_ms"]["median"] / 1000
                for c in ("b-backthought", "c-blocking", "a-tool", "e-backthought-tool")]))
deploy.append(("Product, hosted models", kh["by_condition"]["c-blocking"]["blocking_ms_median"],
               [kh["by_condition"][c]["path_ms"]["median"] / 1000
                for c in ("b-backthought", "c-blocking", "a-tool", "e-backthought-tool")]))
put("RecallWaitMin", f"{min(wait for _, wait, _ in deploy):.0f}")
put("RecallWaitMax", f"{max(wait for _, wait, _ in deploy):.0f}")
(PAPER / "tab-deploy.tex").write_text(
    "\n".join(" & ".join([name, f"{wait:.0f}", *[f"{x:.1f}" for x in secs]]) + r" \\"
              for name, wait, secs in deploy) + "\n")
put("DeploySetups", str(len(deploy)))

# Correct by time: how far the never-wait agent is ever ahead of blocking retrieval.
csv.field_size_limit(10**9)
grid = np.linspace(0, 30, 6001)
lead_best = (-1.0, 0.0, 0.0, "")
lag_ceilings = []
SETUP_WORDS = {"Lap": "with the reference agent on local models",
               "Hs": "with the reference agent on hosted models",
               "K": "in the product on local models", "KH": "in the product on hosted models"}
for (title, path, field, conds), tag in zip(figures.ONTIME_SETUPS, ("Lap", "Hs", "K", "KH"), strict=True):
    ot_rows = figures.ontime_rows(path)
    lag_curve = figures.correct_by_time(ot_rows, conds["lag1"], field, grid)
    block_curve = figures.correct_by_time(ot_rows, conds["blocking"], field, grid)
    lead = lag_curve - block_curve
    lag_ceilings.append(float(lag_curve[-1]))
    i = int(np.argmax(lead))
    passed_at = float(grid[np.argmax(block_curve > lag_curve[-1])])
    put(f"OnTimeLead{tag}", f"{lead[i]:.0f}")
    put(f"OnTimePassed{tag}", f"{passed_at:.1f}")
    if lead[i] > lead_best[0]:
        lead_best = (float(lead[i]), float(grid[i]), passed_at, tag)
put("OnTimeLeadMax", f"{lead_best[0]:.0f}")
put("OnTimeLeadMaxAt", f"{lead_best[1]:.1f}")
put("OnTimeLeadMaxLost", f"{lead_best[2] - lead_best[1]:.1f}")
put("OnTimeLeadMaxSetup", SETUP_WORDS[lead_best[3]])
put("LagCeilMin", f"{min(lag_ceilings):.0f}")
put("LagCeilMax", f"{max(lag_ceilings):.0f}")

(PAPER / "numbers.tex").write_text(
    "% Generated by src/make_numbers.py. Do not edit.\n"
    + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in macros.items())
)

# ---------------------------------------------------------------- tables
NAMES = {"none": "No memory", "tool": "Search tool", "blocking": "Blocking retrieval",
         "prefetch50": "Prefetch 50\\%", "lag1": "Lag 1",
         "hybrid": "Lag 1 + search"}
ORDER = ["none", "tool", "blocking", "prefetch50", "lag1", "hybrid"]

rows = []
for cond in ORDER:
    e = bc[cond]
    carry = e["by_class"][CARRY]["pass"]
    cells = [NAMES[cond], pct_with_ci(e["recall_pass"])]
    cells += [pct(e["by_class"][c]["pass"][0]) for c in ("asked-continuing", "asked-shift", "unprompted")]
    cells += [pct_with_ci(carry), pct(e["by_class"]["abstain"]["pass"][0])]
    cells += ([str(gold_cases(trials, cond, NEW_NEED)[0]), str(gold_cases(trials, cond, (CARRY,))[0])]
              if cond in ("blocking", "prefetch50", "lag1", "hybrid") else ["--", "--"])
    cells += [f"{e['pre_generation_ms']['median']:.0f}"]
    rows.append(" & ".join(cells) + r" \\")
(PAPER / "tab-e2.tex").write_text("\n".join(rows) + "\n")

rows = []
for label, key in (("6", "L6"), ("5", "L5"), ("4", "L4"), ("3", "L3"), ("2", "L2"), ("1", "L1")):
    rows.append(f"Lag, utterances behind & {label} & " + " & ".join(
        f"{f2(ag[f'k5/w{w}/{key}'][0])} {ci2(ag[f'k5/w{w}/{key}'])}" for w in (1, 3, 5))
        + f" & {f2(ag[f'k10/w3/{key}'][0])}" + r" \\")
for label, key in (("25\\%", "P25"), ("50\\%", "P50"), ("75\\%", "P75")):
    rows.append(f"Prefix of incoming utterance & {label} & " + " & ".join(
        f"{f2(ag[f'k5/w{w}/{key}'][0])} {ci2(ag[f'k5/w{w}/{key}'])}" for w in (1, 3, 5))
        + f" & {f2(ag[f'k10/w3/{key}'][0])}" + r" \\")
rows.append("Unrelated ambience (floor) & -- & " + " & ".join(
    f"{f2(ag[f'k5/w{w}/RAND'][0])} {ci2(ag[f'k5/w{w}/RAND'])}" for w in (1, 3, 5))
    + f" & {f2(ag['k10/w3/RAND'][0])}" + r" \\")
(PAPER / "tab-e1.tex").write_text("\n".join(rows) + "\n")

rows = []
for cond in ORDER:
    e = bc[cond]
    cells = [NAMES[cond]]
    for c in (CARRY, "asked-continuing", "asked-shift", "unprompted", "abstain"):
        b = e["by_class"][c]
        cells.append(pct_with_ci(b["pass"]))
        cells.append(pct(b["pass_all_5"]))
    rows.append(" & ".join(cells) + r" \\")
(PAPER / "tab-e2-classes.tex").write_text("\n".join(rows) + "\n")

rows = []
for cond in ORDER:
    e = bc[cond]
    o = e["asked_outcomes"]
    g = extra[cond]["pass_given_gold"]
    rows.append(" & ".join([
        NAMES[cond], pct(o["stated_fact"]), pct(o["abstained"]), pct(o["other_answer"]),
        pct(e["searched_rate"]),
        f"{pct(g[0])} ({g[1]})" if g[0] is not None else "--",
        f"{e['total_ms']['median']:.0f}", f"{e['total_ms']['p90']:.0f}",
    ]) + r" \\")
(PAPER / "tab-e2-detail.tex").write_text("\n".join(rows) + "\n")

RUN_NAMES = {"e2": r"\texttt{gemma4:e4b}, reasoning off (main run)",
             "e2-think": r"\texttt{gemma4:e4b}, reasoning on",
             "e2-qwen3": r"\texttt{qwen3:8b}, reasoning off",
             "e2-anthropic": r"\texttt{claude-sonnet-5}, hosted, with hosted embeddings"}
rows = []
for run, (summary, run_rows) in robust.items():
    if rows:
        rows.append(r"\addlinespace")
    rows.append(r"\multicolumn{9}{@{}l}{" + RUN_NAMES[run] + r"} \\")
    for cond in ORDER:
        e = summary["by_condition"][cond]
        sec = reply_seconds(run, run_rows, cond)
        cells = [r"\quad " + NAMES[cond], f"{pct(e['recall_pass'][0])} {pctci(e['recall_pass'])}"]
        cells += [pct(e["by_class"][c]["pass"][0])
                  for c in ("asked-continuing", "asked-shift", "unprompted", "abstain")]
        cells += [pct(e["asked_outcomes"]["other_answer"]),
                  pct(float(np.mean([r["searched"] == "True" for r in run_rows if r["condition"] == cond])))
                  if cond in ("tool", "hybrid") else "--",
                  f"{sec:.1f}" if sec is not None else r"--$^{\dagger}$"]
        rows.append(" & ".join(cells) + r" \\")
(PAPER / "tab-robust.tex").write_text("\n".join(rows) + "\n")

KNAMES = {"a-tool": "Search tool (shipped)", "b-backthought": "Lag 1",
          "c-blocking": "Blocking retrieval", "d-blocking-backthought": "Blocking + lag 1",
          "e-backthought-tool": "Lag 1 + search"}
def carry_cell(key: str, cond: str) -> str:
    run = e3.get(key)
    return pct(run["by_condition"][cond]["by_class"]["asked-carry"]["pass"][0]) if run else MISSING


def bringup_row(key: str, hosted: bool) -> list[str]:
    """The sixth condition as a table row, or nothing while its run is not delivered."""
    run = e3.get(key)
    if not run:
        return []
    e = run["by_condition"][BRINGUP]
    cells = ["Search tool + sentence", f"{pct(e['recall_pass'][0])} {pctci(e['recall_pass'])}"]
    cells += [pct(e["by_class"][c]["pass"][0]) for c in ("asked-continuing", "asked-shift", "unprompted")]
    cells += ["--", "--", pct(e["searched_rate"])]
    if hosted:
        c = run["cost"]["conditions"][BRINGUP]
        cells += [pct(e["abstain"]["abstain_recorded"]), f"{e['path_ms_median'] / 1000:.1f}",
                  f"{c['model_calls_per_trial']:.1f}", f"{100 * c['cost_usd_per_trial']:.2f}"]
    else:
        cells += [pct(e["abstain"]["abstain_recorded"]), pct(e["abstain"]["abstain_text"]),
                  f"{e['path_ms_median'] / 1000:.1f}"]
    return [r"\addlinespace[2pt]", " & ".join(cells) + r" \\"]


rows = []
for cond in ("a-tool", "c-blocking", "b-backthought", "d-blocking-backthought", "e-backthought-tool"):
    e = k2["by_condition"][cond]
    cells = [KNAMES[cond], f"{pct(e['recall_pass'][0])} {pctci(e['recall_pass'])}"]
    cells += [pct(e["by_class"][c]["pass"][0]) for c in ("asked-continuing", "asked-shift", "unprompted")]
    cells += [carry_cell("carry", cond)]
    cells += [pct(e["gold_in_wm"][0]) if cond != "a-tool" else "--",
              pct(e["searched_rate"]) if "tool" in cond else "--",
              pct(e["abstain"]["abstain_recorded"]), pct(e["abstain"]["abstain_text"]),
              f"{e['path_ms']['median'] / 1000:.1f}"]
    rows.append(" & ".join(cells) + r" \\")
rows += bringup_row("bringup", hosted=False)
(PAPER / "tab-e3.tex").write_text("\n".join(rows) + "\n")

rows = []
for cond in ("a-tool", "c-blocking", "b-backthought", "d-blocking-backthought", "e-backthought-tool"):
    e = kh["by_condition"][cond]
    c = kh["cost"]["conditions"][cond]
    cells = [KNAMES[cond], f"{pct(e['recall_pass'][0])} {pctci(e['recall_pass'])}"]
    cells += [pct(e["by_class"][cls]["pass"][0]) for cls in ("asked-continuing", "asked-shift", "unprompted")]
    cells += [carry_cell("hosted_carry", cond)]
    cells += [pct(e["gold_in_wm"][0]) if cond != "a-tool" else "--",
              pct(e["searched_rate"]) if "tool" in cond else "--",
              pct(e["abstain"]["abstain_recorded"]),
              f"{e['path_ms']['median'] / 1000:.1f}",
              f"{c['model_calls_per_trial']:.1f}", f"{100 * c['cost_usd_per_trial']:.2f}"]
    rows.append(" & ".join(cells) + r" \\")
rows += bringup_row("hosted_bringup", hosted=True)
(PAPER / "tab-e3-hosted.tex").write_text("\n".join(rows) + "\n")

rows = []
for cond in ("L1", "L2", "L3", "P50", "P75", "RAND"):
    label = {"L1": "Lag 1", "L2": "Lag 2", "L3": "Lag 3", "P50": "Prefix 50\\%",
             "P75": "Prefix 75\\%", "RAND": "Unrelated ambience"}[cond]
    rows.append(label + " & " + " & ".join(f2(q[0]) for q in e1["by_shift"][cond]) + r" \\")
(PAPER / "tab-e1-shift.tex").write_text("\n".join(rows) + "\n")
print(len(macros), "macros;", "tables written")
