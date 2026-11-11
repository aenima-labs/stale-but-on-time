"""Experiment 1: staleness of lagged recall, replayed on LoCoMo."""

from invoke import task

from ._common import run_src


@task
def replay(c, args=""):
    """Replay LoCoMo with lagged and fresh retrieval (~12 min without the embedding cache)."""
    run_src(c, "e1_replay.py", args)


@task
def analyze(c):
    """Analysis and timing model."""
    run_src(c, "e1_analyze.py")
