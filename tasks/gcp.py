"""Experiment 2 on a GPU machine in GCP (infra/gcp). Creates billable resources only in gcp.run."""

from invoke import task

from ._common import run_src


def _opts(run, machine, spot, max_hours, args, models):
    o = f"--run {run} --machine-type {machine} --max-hours {max_hours}"
    if spot:
        o += " --spot"
    if args:
        o += f' --args "{args}"'
    if models:
        o += " --models " + " ".join(models.split(","))
    return o


@task
def estimate(c, run, machine="g4-standard-48", spot=False, max_hours=4, args="", models=""):
    """Estimate a GCP run (machine time and cost, worst case at the hard lifetime). Creates nothing."""
    run_src(c, "gcp_job.py", _opts(run, machine, spot, max_hours, args, models) + " --estimate-only")


@task
def plan(c, run, machine="g4-standard-48", spot=False, max_hours=4, args="", models=""):
    """terraform validate and plan for a GCP run. Creates nothing (needs gcloud ADC)."""
    c.run("terraform -chdir=infra/gcp init -input=false -backend=false && terraform -chdir=infra/gcp validate")
    run_src(c, "gcp_job.py", _opts(run, machine, spot, max_hours, args, models) + " --plan-only")


@task
def run(c, run, machine="g4-standard-48", spot=False, max_hours=4, args="", models="", yes=False):
    """Create the machine, run Experiment 2 on it, copy results back, destroy everything.

    Asks for confirmation after the estimate unless --yes. Example:
    uv run inv gcp.run --run e2-gcp-g4
    uv run inv gcp.run --run e2-gcp-g4-26b --args="--model gemma4:26b" --models=gemma4:26b,nomic-embed-text
    """
    run_src(c, "gcp_job.py", _opts(run, machine, spot, max_hours, args, models) + (" --yes" if yes else ""))
