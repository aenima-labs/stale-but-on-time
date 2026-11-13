"""Experiment 2: the async-recall pack on a reference agent."""

from invoke import task

from ._common import run_src


@task
def build_pack(c):
    """Generate the Circumstances pack and fixture from pack-src/."""
    run_src(c, "build_pack.py")


@task
def run(c, args=""):
    """Run the six memory conditions (~18 min, needs Ollama). Extra CLI args via --args.

    Robustness runs: --args="--think --out results/e2-think" (about 2.7 hours) and
    --args="--model qwen3:8b --out results/e2-qwen3".
    """
    run_src(c, "e2_run.py", args)


RUNS = ("e2", "e2-think", "e2-qwen3")  # main run, reasoning on, second model


@task
def analyze(c):
    """Analysis of the main run and of the two robustness runs."""
    for name in RUNS:
        run_src(c, "e2_analyze.py", f"--run {name}")


@task
def analyze_product(c):
    """Experiment 3: analysis of the two runs against the product (results/e3-kodama*)."""
    run_src(c, "e3_analyze.py")


@task
def scrub_paths(c, dirs="results/e2"):
    """Replace absolute pack paths in sealed bundles and re-seal them (space-separated dirs)."""
    run_src(c, "scrub_paths.py", dirs)
