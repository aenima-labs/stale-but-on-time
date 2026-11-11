"""Figures, numbers, the manuscript and the anonymised review copy."""

import sys

from invoke import task

from ._common import ROOT, run_src


@task
def figures(c):
    """Draw the figures."""
    run_src(c, "figures.py")


@task
def numbers(c):
    """Write number macros and table bodies for the paper."""
    run_src(c, "make_numbers.py")


@task
def build(c):
    """Compile paper/main.tex with tectonic (preprint build)."""
    with c.cd("paper"):
        c.run("tectonic main.tex")


@task
def anon(c):
    """Build the anonymised review copy: dist/stale-but-on-time-anon.{pdf,zip}."""
    if not (ROOT / "src" / "make_anon.py").exists():
        sys.exit("make_anon.py exists only in the source repository, not in the anonymised copy.")
    run_src(c, "make_anon.py")
