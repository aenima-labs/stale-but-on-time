"""Experiment 2 as a Cloud Run job with a GPU (infra/gcp, src/gcp_job.py)."""

from invoke import task

from ._common import run_src


def _opts(run, args, max_hours, models, gpu, cpu, memory):
    o = f"--run {run} --max-hours {max_hours} --gpu {gpu} --cpu {cpu} --memory-gib {memory}"
    if args:
        o += f' --args "{args}"'
    if models:
        o += " --models " + " ".join(models.split(","))
    return o


HELP = {
    "run": "results/<run> to create",
    "args": "extra e2_run.py arguments for the job, e.g. '--max-cases 2'",
    "max_hours": "task timeout (hard stop, at most 12)",
    "models": "comma-separated Ollama models to upload (default gemma4:e4b,nomic-embed-text)",
}


@task(help=HELP)
def estimate(c, run, args="", max_hours=2, models="", gpu="nvidia-l4", cpu=4, memory=24):
    """Estimate a Cloud Run run (job time and cost, worst case at the task timeout). Creates nothing."""
    run_src(c, "gcp_job.py", _opts(run, args, max_hours, models, gpu, cpu, memory) + " --estimate-only")


@task(help=HELP)
def plan(c, run, args="", max_hours=2, models="", gpu="nvidia-l4", cpu=4, memory=24):
    """terraform plan of infra/gcp. Creates nothing."""
    run_src(c, "gcp_job.py", _opts(run, args, max_hours, models, gpu, cpu, memory) + " --plan-only")


@task(help={**HELP, "yes": "skip the confirmation"})
def run(c, run, args="", max_hours=2, models="", gpu="nvidia-l4", cpu=4, memory=24, yes=False):
    """Apply the infrastructure, build and push the image, run the job, copy the results back.

    uv run inv gcp.run --run e2-cloudrun-l4-subset --args="--max-cases 2"
    """
    run_src(c, "gcp_job.py", _opts(run, args, max_hours, models, gpu, cpu, memory) + (" --yes" if yes else ""))


@task
def destroy(c):
    """Delete the job, registry, service account (the bucket stays unless force_destroy=true)."""
    c.run("terraform -chdir=infra/gcp destroy -input=false")
