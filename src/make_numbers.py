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
    put(f"Srch{tag}", pct(e["searched_rate"]))
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

(PAPER / "numbers.tex").write_text(
    "% Generated by src/make_numbers.py. Do not edit.\n"
    + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in macros.items())
)

# ---------------------------------------------------------------- tables
NAMES = {"none": "No memory", "tool": "Search tool", "blocking": "Blocking retrieval",
         "prefetch50": "Async, prefetch 50\\%", "lag1": "Async, lag 1",
         "hybrid": "Async lag 1 + search"}
ORDER = ["none", "tool", "blocking", "prefetch50", "lag1", "hybrid"]

rows = []
for cond in ORDER:
    e = bc[cond]
    cells = [NAMES[cond], f"{pct(e['recall_pass'][0])} {pctci(e['recall_pass'])}"]
    cells += [pct(e["by_class"][c]["pass"][0]) for c in ("asked-continuing", "asked-shift", "unprompted", "abstain")]
    cells += [pct(e["gold_in_context"][0]) if cond != "none" else "--",
              f"{e['pre_generation_ms']['median']:.0f}", f"{e['pre_generation_ms']['p90']:.0f}"]
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
    for c in ("asked-continuing", "asked-shift", "unprompted", "abstain"):
        b = e["by_class"][c]
        cells.append(f"{pct(b['pass'][0])} {pctci(b['pass'])}")
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

rows = []
for cond in ("L1", "L2", "L3", "P50", "P75", "RAND"):
    label = {"L1": "Lag 1", "L2": "Lag 2", "L3": "Lag 3", "P50": "Prefix 50\\%",
             "P75": "Prefix 75\\%", "RAND": "Unrelated ambience"}[cond]
    rows.append(label + " & " + " & ".join(f2(q[0]) for q in e1["by_shift"][cond]) + r" \\")
(PAPER / "tab-e1-shift.tex").write_text("\n".join(rows) + "\n")
print(len(macros), "macros;", "tables written")
