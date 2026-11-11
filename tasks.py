"""Project tasks. List them with `uv run inv --list`; see README.md for the order.

Examples:
    uv run inv analyze                       # analysis, figures, numbers, paper (no Ollama)
    uv run inv fetch-data
    uv run inv e2-run --args="--think --out results/e2-think"
    uv run inv anon                          # anonymised review copy under dist/
"""

import sys
from pathlib import Path

from invoke import Context, task

ROOT = Path(__file__).resolve().parent
PY = sys.executable
SRC = {"PYTHONPATH": str(ROOT / "src")}


def _py(c: Context, script: str, args: str = "") -> None:
    c.run(f"{PY} {script} {args}".strip(), env=SRC, pty=False)


@task
def fetch_data(c, locomo_only=False, cache_only=False):
    """Download LoCoMo and the optional embedding cache (not stored in git)."""
    sys.path.insert(0, str(ROOT / "src"))
    import fetch_data as fetch

    if not cache_only:
        fetch.fetch_locomo()
    if not locomo_only:
        fetch.fetch_cache()


@task
def e1_replay(c, args=""):
    """Experiment 1: replay LoCoMo with lagged and fresh retrieval (~12 min without the cache)."""
    _py(c, "src/e1_replay.py", args)


@task
def e1_analyze(c):
    """Experiment 1: analysis and timing model."""
    _py(c, "src/e1_analyze.py")


@task
def build_pack(c):
    """Generate the Circumstances pack and fixture from pack-src/."""
    _py(c, "src/build_pack.py")


@task
def e2_run(c, args=""):
    """Experiment 2: run the six memory conditions (~18 min; needs Ollama). Extra CLI args via --args."""
    _py(c, "src/e2_run.py", args)


@task
def e2_analyze(c):
    """Experiment 2: analysis and audit sample."""
    _py(c, "src/e2_analyze.py")


@task
def scrub_paths(c, dirs="results/e2"):
    """Replace absolute pack paths in sealed bundles and re-seal them (space-separated dirs)."""
    _py(c, "src/scrub_paths.py", dirs)


@task
def figures(c):
    """Draw the figures."""
    _py(c, "src/figures.py")


@task
def numbers(c):
    """Write number macros and table bodies for the paper."""
    _py(c, "src/make_numbers.py")


@task
def paper(c):
    """Compile paper/main.tex with tectonic (preprint build)."""
    with c.cd("paper"):
        c.run("tectonic main.tex")


@task(pre=[e1_analyze, e2_analyze, figures, numbers, paper])
def analyze(c):
    """Everything that needs no model: analysis, figures, numbers, paper."""


@task(pre=[fetch_data, e1_replay, e1_analyze, build_pack, e2_run, e2_analyze, figures, numbers, paper])
def reproduce(c):
    """The whole pipeline from scratch (needs Ollama; about 30 minutes)."""


@task
def anon(c):
    """Build the anonymised review copy: dist/stale-but-on-time-anon.{pdf,zip}."""
    if not (ROOT / "src" / "make_anon.py").exists():
        sys.exit("make_anon.py exists only in the source repository, not in the anonymised copy.")
    _py(c, "src/make_anon.py")
