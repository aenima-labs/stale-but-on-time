"""Experiment 2: the async-recall pack on a reference agent."""

from invoke import task

from ._common import run_src


@task
def build_pack(c):
    """Generate the Circumstances pack and fixture from pack-src/."""
    run_src(c, "build_pack.py")


@task
def run(c, args=""):
    """Run the six memory conditions (~18 min, needs Ollama). Extra CLI args via --args."""
    run_src(c, "e2_run.py", args)


@task
def analyze(c):
    """Analysis and audit sample."""
    run_src(c, "e2_analyze.py")


@task
def scrub_paths(c, dirs="results/e2"):
    """Replace absolute pack paths in sealed bundles and re-seal them (space-separated dirs)."""
    run_src(c, "scrub_paths.py", dirs)
