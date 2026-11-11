"""Draw the data figures from the two summary files.

Vector PDFs go to ``figures/`` for the paper; PNG previews go next to them.
Colours follow a validated categorical palette (blue, orange) and a single-hue
ordinal ramp; text stays in ink, never in a series colour.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
INK, MUTED, GRID, AXIS = "#1a1a19", "#5f5e5a", "#e1e0d9", "#a8a79f"
BLUE, ORANGE = "#2a78d6", "#eb6834"
RAMP = {1: "#86b6ef", 3: "#2a78d6", 5: "#104281"}  # ordinal: window size
WIDTH = 6.5  # inches; the text width of the TMLR template

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["cmr10"],  # Computer Modern, to match the paper's Latin Modern
        "mathtext.fontset": "cm",
        "axes.formatter.use_mathtext": True,
        "axes.unicode_minus": False,
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 9,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 8.5,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.5,
        "axes.axisbelow": True,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    }
)


def save(fig, name: str) -> None:
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=220)
    plt.close(fig)


def fig_staleness(e1: dict) -> None:
    conds = ["L6", "L5", "L4", "L3", "L2", "L1", "P25", "P50", "P75"]
    labels = ["6", "5", "4", "3", "2", "1", "25%", "50%", "75%", "100%"]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(WIDTH, 2.7))
    for w in (1, 3, 5):
        triples = [e1["agreement"][f"k5/w{w}/{c}"] for c in conds]
        mean = [t[0] for t in triples] + [1.0]
        lo = [t[1] for t in triples] + [1.0]
        hi = [t[2] for t in triples] + [1.0]
        ax.fill_between(x, lo, hi, color=RAMP[w], alpha=0.18, linewidth=0)
        ax.plot(x, mean, color=RAMP[w], linewidth=1.4, marker="o", markersize=3.6,
                markeredgecolor="white", markeredgewidth=0.6,
                label=f"$w={w}$ utterance" + ("s" if w > 1 else ""), zorder=3)
    floor = e1["agreement"]["k5/w3/RAND"][0]
    ax.axhline(floor, color=MUTED, linewidth=0.8, linestyle=(0, (3, 2)))
    ax.text(9.3, floor + 0.02, "unrelated ambience (floor)", color=MUTED, fontsize=8, va="bottom",
            ha="right")
    ax.axvline(5.5, color=AXIS, linewidth=0.6)
    ax.text(2.5, 1.07, "record lags by whole utterances", ha="center", fontsize=8.5, color=MUTED)
    ax.text(7.5, 1.07, "record saw part of the incoming one", ha="center", fontsize=8.5,
            color=MUTED)
    ax.annotate("fresh\n(blocking)", (9, 1.0), (8.25, 0.52), fontsize=8, color=MUTED, ha="center",
                arrowprops={"arrowstyle": "-", "color": AXIS, "linewidth": 0.6})
    ax.set_xticks(x, labels)
    ax.set_xlim(-0.35, 9.35)
    ax.set_ylim(0, 1.04)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("utterances behind                                                   "
                  "share of incoming utterance seen")
    ax.set_ylabel("overlap@5 with fresh retrieval")
    ax.grid(axis="x", visible=False)
    ax.legend(title="ambience window", title_fontsize=8.5, loc="upper left",
              bbox_to_anchor=(0.0, 0.93), handlelength=1.6, labelspacing=0.3)
    save(fig, "fig-staleness")


def fig_timing(e1: dict) -> None:
    t = e1["timing"]
    cost = np.array(t["cost_s"])
    fig, ax = plt.subplots(figsize=(WIDTH, 2.7))
    ax.axhline(1.0, color=INK, linewidth=1.2)
    ax.text(0.105, 1.025, "blocking retrieval: full agreement, but every reply waits $c$ seconds",
            fontsize=8.5, color=INK, va="bottom")
    series = (
        ("stream", ORANGE, "asynchronous, jobs also start on partial transcripts"),
        ("turn", BLUE, "asynchronous, jobs start at utterance ends only"),
    )
    for policy, colour, label in series:
        mean, lo, hi = (np.array(v) for v in t[f"150wpm/{policy}"])
        ax.fill_between(cost, lo, hi, color=colour, alpha=0.18, linewidth=0)
        ax.plot(cost, mean, color=colour, linewidth=1.5, label=label, zorder=3)
        ax.plot(cost, t[f"210wpm/{policy}"][0], color=colour, linewidth=0.9,
                linestyle=(0, (3, 2)), zorder=2)
    ax.plot([], [], color=MUTED, linewidth=0.9, linestyle=(0, (3, 2)),
            label="same, faster speech (210 instead of 150 words/min)")
    ax.set_xscale("log")
    ax.set_xlim(0.1, 60)
    ax.set_xticks([0.1, 0.3, 1, 3, 10, 30, 60], ["0.1", "0.3", "1", "3", "10", "30", "60"])
    ax.minorticks_off()
    ax.set_ylim(0, 1.12)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("cost of one recall job, $c$ (seconds, log scale)")
    ax.set_ylabel("expected overlap@5\nwith fresh retrieval")
    ax.legend(loc="lower left", handlelength=1.8, labelspacing=0.3)
    save(fig, "fig-timing")


NAMES = {
    "none": "No memory",
    "tool": "Search tool",
    "blocking": "Blocking retrieval",
    "prefetch50": "Async, prefetch 50%",
    "lag1": "Async, lag 1",
    "hybrid": "Async lag 1 + search",
}
ORDER = ["none", "tool", "blocking", "prefetch50", "lag1", "hybrid"]
CLASS_TITLES = {
    "asked-continuing": "Asked, topic continues",
    "asked-shift": "Asked, topic shifts",
    "unprompted": "Unprompted",
    "abstain": "Must abstain",
}


def fig_classes(e2: dict) -> None:
    fig, axes = plt.subplots(1, 4, figsize=(WIDTH, 1.95), sharey=True)
    y = np.arange(len(ORDER))[::-1]
    for ax, (cls, title) in zip(axes, CLASS_TITLES.items(), strict=True):
        triples = [e2["by_condition"][c]["by_class"][cls]["pass"] for c in ORDER]
        mean = np.array([100 * t[0] for t in triples])
        lo = np.array([100 * t[1] for t in triples])
        hi = np.array([100 * t[2] for t in triples])
        ax.hlines(y, lo, hi, color=BLUE, linewidth=1.1, alpha=0.55)
        ax.plot(mean, y, "o", color=BLUE, markersize=4.6, markeredgecolor="white",
                markeredgewidth=0.7, zorder=3)
        ax.set_title(title, pad=4)
        ax.set_xlim(-6, 106)
        ax.set_xticks([0, 50, 100])
        ax.set_ylim(-0.6, len(ORDER) - 0.4)
        ax.grid(axis="y", visible=False)
        ax.tick_params(axis="y", length=0)
    axes[0].set_yticks(y, [NAMES[c] for c in ORDER])
    for label in axes[0].get_yticklabels():
        label.set_color(INK)
    fig.supxlabel("trials passed (%)", fontsize=9, y=-0.08)
    fig.subplots_adjust(wspace=0.12)
    save(fig, "fig-classes")


def fig_tradeoff(e2: dict) -> None:
    fig, ax = plt.subplots(figsize=(WIDTH * 0.66, 2.5))
    offsets = {
        "none": (7, 5), "tool": (-7, 0), "blocking": (7, 0),
        "prefetch50": (7, 0), "lag1": (7, 0), "hybrid": (-7, 0),
    }
    for c in ORDER:
        e = e2["by_condition"][c]
        xval = e["pre_generation_ms"]["mean"]
        mean, lo, hi = (100 * v for v in e["recall_pass"])
        ax.vlines(xval, lo, hi, color=BLUE, linewidth=1.1, alpha=0.55)
        ax.plot(xval, mean, "o", color=BLUE, markersize=5, markeredgecolor="white",
                markeredgewidth=0.7, zorder=3)
        dx, dy = offsets[c]
        ax.annotate(NAMES[c], (xval, mean), (dx, dy), textcoords="offset points",
                    fontsize=8.5, ha="left" if dx > 0 else "right", va="center")
    ax.set_xlim(-25, 540)
    ax.set_ylim(-5, 104)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xlabel("mean delay added before the reply starts to generate (ms)")
    ax.set_ylabel("recall trials passed (%)")
    save(fig, "fig-tradeoff")


def main() -> None:
    which = sys.argv[1:] or ["e1", "e2"]
    if "e1" in which:
        e1 = json.loads((ROOT / "results" / "e1_summary.json").read_text())
        fig_staleness(e1)
        fig_timing(e1)
    if "e2" in which:
        e2 = json.loads((ROOT / "results" / "e2_summary.json").read_text())
        fig_classes(e2)
        fig_tradeoff(e2)


if __name__ == "__main__":
    main()
