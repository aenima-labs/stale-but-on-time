"""Run Experiment 2 as a Cloud Run job with a GPU, from estimate to results.

    python src/gcp_job.py --run e2-cloudrun-l4-subset --args "--max-cases 2" [--yes | --estimate-only | --plan-only]

1. Estimate (trials, run time, job cost for start-up and run, worst case at the
   task timeout) and confirmation, as for any run.
2. ``terraform apply`` of ``infra/gcp`` (Artifact Registry repository, bucket,
   service account, the job). Idempotent; nothing there bills while idle except
   storage.
3. Build ``infra/gcp/Dockerfile`` from ``git archive HEAD`` (tracked files must
   have no uncommitted changes) with Cloud Build and push it tagged with the
   commit. Skipped when that tag exists.
4. The local model manifests (about 1 KB each) go to the bucket with their
   SHA-256; the job takes each blob they name from the bucket or downloads it
   by digest from Ollama's registry inside GCP, and checks every hash, so the
   weights are those of the local runs even after a registry tag moved.
5. Point the job at the image, execute it with the run's name and arguments
   and a hard task timeout, and wait. Ctrl-C cancels the execution.
6. Copy ``gs://<bucket>/results/<run>/`` to ``results/<run>/`` and write
   ``machine.json`` (billed seconds from the execution's start and completion
   times, and their cost), the telemetry summary and ``estimate_vs_actual.md``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

import estimate as est_mod
import telemetry_summary
from pricing import PriceTable

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "infra" / "gcp"
PROJECT = "kodama-500509"
REGION = "europe-west1"
JOB = "sbot-e2"
OLLAMA_MODELS = Path(os.environ.get("OLLAMA_MODELS", Path.home() / ".ollama" / "models"))


def sh(cmd: list[str], *, check: bool = True, capture: bool = False, cwd: Path | None = None,
       quiet: bool = False) -> str:
    if not quiet:
        print("+ " + " ".join(cmd), flush=True)
    done = subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=capture)
    return done.stdout if capture else ""


def tf_vars(a: argparse.Namespace, image: str | None = None) -> list[str]:
    pairs = {"cpu": a.cpu, "memory_gib": a.memory_gib, "gpu": a.gpu, "task_timeout_hours": a.max_hours}
    if image:
        pairs["image"] = image
    return [x for k, v in pairs.items() for x in ("-var", f"{k}={v}")]


def model_files(models: list[str]) -> list[Path]:
    """Manifests and blobs of the given Ollama models, relative to the models dir."""
    files: list[Path] = []
    for model in models:
        name, _, tag = model.partition(":")
        manifest = OLLAMA_MODELS / "manifests" / "registry.ollama.ai" / "library" / name / (tag or "latest")
        if not manifest.is_file():
            raise SystemExit(f"{model} is not in {OLLAMA_MODELS}; run `ollama pull {model}` first.")
        files.append(manifest.relative_to(OLLAMA_MODELS))
        data = json.loads(manifest.read_text())
        for layer in [data.get("config", {}), *data.get("layers", [])]:
            digest = layer.get("digest", "")
            if digest:
                files.append(Path("blobs") / digest.replace(":", "-"))
    return files


def manifest_hashes(models: list[str]) -> str:
    """name=sha256 of each local manifest, as the job checks them."""
    import hashlib

    pairs = []
    for model in models:
        name, _, tag = model.partition(":")
        manifest = OLLAMA_MODELS / "manifests" / "registry.ollama.ai" / "library" / name / (tag or "latest")
        if not manifest.is_file():
            raise SystemExit(f"{model} is not in {OLLAMA_MODELS}; run `ollama pull {model}` first.")
        pairs.append(f"{model}={hashlib.sha256(manifest.read_bytes()).hexdigest()}")
    return ",".join(pairs)


def upload_manifests(bucket: str, models: list[str]) -> None:
    """The local manifests (about 1 KB each); the job fetches the blobs they name."""
    for model in models:
        rel = model_files([model])[0]
        sh(["gcloud", "storage", "cp", str(OLLAMA_MODELS / rel), f"gs://{bucket}/models/{rel.as_posix()}"],
           quiet=True)


def upload_models(bucket: str, models: list[str]) -> None:
    """Optional (--stages models): copy the local blobs to the bucket. Slow over a
    home connection; by default the job pulls them in GCP and checks the manifests."""
    listed = sh(["gcloud", "storage", "ls", "-r", f"gs://{bucket}/models/**"], check=False, capture=True, quiet=True)
    present = {line.split(f"gs://{bucket}/models/", 1)[1] for line in listed.split() if "/models/" in line}
    missing = [f for f in model_files(models) if f.as_posix() not in present]
    if not missing:
        print(f"models already in gs://{bucket}/models/: {', '.join(models)}")
        return
    for f in missing:
        sh(["gcloud", "storage", "cp", str(OLLAMA_MODELS / f), f"gs://{bucket}/models/{f.as_posix()}"])


def build_image(registry: str, commit: str) -> str:
    image = f"{registry}/e2-job:{commit}"
    if subprocess.run(["gcloud", "artifacts", "docker", "images", "describe", image],
                      capture_output=True, text=True).returncode == 0:
        print(f"image exists: {image}")
        return image
    # Built by Cloud Build in GCP: only the source (~25 MB) leaves this machine;
    # the 3 GB base image and the push stay inside Google's network.
    with tempfile.TemporaryDirectory(prefix="sbot-build-") as tmp:
        archive = Path(tmp) / "source.tar"
        sh(["git", "archive", "--format=tar", "-o", str(archive), "HEAD"], cwd=ROOT)
        context = Path(tmp) / "context"
        with tarfile.open(archive) as t:
            t.extractall(context, filter="data")
        (context / "Dockerfile").write_bytes((context / "infra/gcp/Dockerfile").read_bytes())
        sh(["gcloud", "builds", "submit", str(context), f"--tag={image}", f"--project={PROJECT}",
            "--timeout=1800s", "--quiet"])
    return image


def apply(a: argparse.Namespace, image: str | None = None) -> None:
    """terraform plan to a file, print it, and apply exactly that plan."""
    plan = TF / "job.tfplan"
    sh(["terraform", "plan", "-input=false", "-no-color", f"-out={plan}", *tf_vars(a, image)], cwd=TF)
    try:
        sh(["terraform", "apply", "-input=false", str(plan)], cwd=TF)
    finally:
        plan.unlink(missing_ok=True)


def current_image() -> str:
    """The job's container image ('' if the job does not exist yet)."""
    raw = sh(["gcloud", "run", "jobs", "describe", JOB, f"--region={REGION}", f"--project={PROJECT}",
              "--format=json"], capture=True, quiet=True, check=False)

    def find(node: object) -> str:
        if isinstance(node, dict):
            if isinstance(node.get("image"), str):
                return node["image"]
            return next((x for x in map(find, node.values()) if x), "")
        if isinstance(node, list):
            return next((x for x in map(find, node) if x), "")
        return ""

    return find(json.loads(raw)) if raw.strip() else ""


def build_estimate(a: argparse.Namespace, out: Path) -> dict:
    spec = {"machine_type": "", "region": REGION, "kind": "cloud_run", "gpu": a.gpu, "vcpus": a.cpu,
            "memory_gib": a.memory_gib, "startup_min": a.startup_min, "teardown_min": 1.0,
            "max_lifetime_h": a.max_hours, "duration_factor": list(a.duration_factor)}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(spec, f)
    done = subprocess.run(
        [sys.executable, str(ROOT / "src" / "e2_run.py"), "--estimate-only", "--out", str(out),
         "--machine-json", f.name, *a.args.split()],
        capture_output=True, text=True,
    )
    if done.returncode != 0:
        raise SystemExit(done.stdout + done.stderr)
    return json.loads((out / "estimate.json").read_text())


def _time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def describe(execution: str) -> dict:
    raw = sh(["gcloud", "run", "jobs", "executions", "describe", execution, f"--region={REGION}",
              f"--project={PROJECT}", "--format=json"], capture=True, check=False, quiet=True)
    return json.loads(raw or "{}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--run", required=True, help="results/<run> to create")
    p.add_argument("--args", default="", help="extra e2_run.py arguments for the job, e.g. '--max-cases 2'")
    p.add_argument("--models", nargs="+", default=["gemma4:e4b", "nomic-embed-text"])
    p.add_argument("--gpu", default="nvidia-l4")
    p.add_argument("--cpu", type=int, default=6)
    p.add_argument("--memory-gib", type=int, default=24)
    p.add_argument("--max-hours", type=int, default=1, help="task timeout: Cloud Run stops the job here")
    p.add_argument("--startup-min", type=float, default=5.0, help="estimate: image pull, model copy, model load")
    p.add_argument("--duration-factor", type=float, nargs=3, default=(0.5, 1.0, 2.0),
                   help="estimate: job run time relative to the laptop's stored run (low expected high)")
    p.add_argument("--poll-s", type=int, default=30)
    p.add_argument("--yes", action="store_true")
    p.add_argument("--estimate-only", action="store_true")
    p.add_argument("--plan-only", action="store_true", help="terraform plan and stop (creates nothing)")
    p.add_argument("--stages", nargs="+", default=["infra", "image", "execute"],
                   choices=["infra", "image", "models", "execute"], help="steps to run (default: all)")
    a = p.parse_args()

    out = ROOT / "results" / a.run
    leftovers = {f.name for f in out.iterdir()} - {"estimate.json", "estimate.md"} if out.exists() else set()
    if leftovers and not (a.estimate_only or a.plan_only):
        raise SystemExit(f"{out} already holds a run; choose another --run.")
    est = build_estimate(a, out)
    saved = (out / "estimate.json").read_text(), (out / "estimate.md").read_text()
    if a.plan_only:
        print(est_mod.markdown(est))
        sh(["terraform", "init", "-input=false"], cwd=TF, quiet=True)
        sh(["terraform", "plan", "-input=false", *tf_vars(a)], cwd=TF)
        return
    if not est_mod.confirm(est, yes=a.yes, estimate_only=a.estimate_only):
        return
    if subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        raise SystemExit("The working tree has changes; commit them so the job runs a commit.")
    commit = sh(["git", "rev-parse", "--short", "HEAD"], capture=True, cwd=ROOT, quiet=True).strip()

    # Stages: infrastructure, image, models, then the execution. Each can be run alone.
    stages = set(a.stages)
    sh(["terraform", "init", "-input=false"], cwd=TF, quiet=True)
    if "infra" in stages:
        apply(a, current_image() or None)
    registry = sh(["terraform", "output", "-raw", "registry"], capture=True, cwd=TF, quiet=True).strip()
    bucket = sh(["terraform", "output", "-raw", "bucket"], capture=True, cwd=TF, quiet=True).strip()
    image = f"{registry}/e2-job:{commit}"
    if "image" in stages:
        image = build_image(registry, commit)
        if current_image() != image:
            apply(a, image)
    if "models" in stages:
        upload_models(bucket, a.models)  # only when asked: the job fetches and checks them itself
    if "execute" not in stages:
        return
    upload_manifests(bucket, a.models)
    if current_image() != image:
        raise SystemExit(f"The job runs {current_image()}, not {image}; run the image stage first.")

    execution, outcome, info = "", "failed to start", {}
    try:
        started = sh(["gcloud", "run", "jobs", "execute", JOB, f"--region={REGION}", f"--project={PROJECT}",
                      f"--update-env-vars=^@^RUN_NAME={a.run}@RUN_ARGS={a.args}"
                      f"@MODEL_MANIFESTS={manifest_hashes(a.models)}",
                      f"--task-timeout={a.max_hours * 3600}s", "--async", "--format=json"], capture=True)
        execution = json.loads(started)["metadata"]["name"]
        print(f"execution {execution} started; waiting (Ctrl-C cancels it)", flush=True)
        deadline = time.time() + a.max_hours * 3600 + 900
        seen: set[str] = set()
        while time.time() < deadline:
            listed = sh(["gcloud", "storage", "ls", f"gs://{bucket}/results/{a.run}/status/"],
                        check=False, capture=True, quiet=True)
            for marker in sorted({line.rstrip("/").rsplit("/", 1)[-1] for line in listed.split()} - seen):
                seen.add(marker)
                print(f"[{dt.datetime.now(dt.UTC):%H:%M:%S}Z] {marker}", flush=True)
            info = describe(execution)
            if info.get("status", {}).get("completionTime"):
                break
            time.sleep(a.poll_s)
        outcome = "finished" if info.get("status", {}).get("completionTime") else "timed out"
    except KeyboardInterrupt:
        outcome = "canceled"
    finally:
        if execution and outcome != "finished":
            sh(["gcloud", "run", "jobs", "executions", "cancel", execution, f"--region={REGION}",
                f"--project={PROJECT}", "--quiet"], check=False)
            info = describe(execution)
        status = info.get("status", {})
        start, end = status.get("startTime"), status.get("completionTime")
        seconds = (_time(end) - _time(start)).total_seconds() if start and end else float("nan")
        if outcome == "finished":
            outcome = "succeeded" if int(status.get("succeededCount", 0) or 0) else "failed"
        mp = PriceTable().cloud_run_price(REGION, a.gpu, a.cpu, a.memory_gib)
        out.mkdir(parents=True, exist_ok=True)
        sh(["gcloud", "storage", "cp", "-r", f"gs://{bucket}/results/{a.run}/*", str(out)], check=False)
        machine = {
            "kind": "cloud_run", "job": JOB, "execution": execution, "image": image, "commit": commit,
            "gpu": a.gpu, "vcpus": a.cpu, "memory_gib": a.memory_gib, "region": REGION, "outcome": outcome,
            "started_utc": start, "completed_utc": end, "seconds": seconds, "hours": seconds / 3600,
            "cost_usd": seconds / 3600 * mp.on_demand_per_hour if mp else float("nan"),
            "note": "Billed time from the execution's start to completion (Cloud Run bills per second while "
                    "the task runs); the monthly free tier is not subtracted.",
        }
        (out / "machine.json").write_text(json.dumps(machine, indent=2) + "\n")
        (out / "estimate.json").write_text(saved[0])
        (out / "estimate.md").write_text(saved[1])
        print(json.dumps(machine, indent=2))
    if (out / "telemetry").is_dir() and any((out / "telemetry").glob("*.spans.jsonl")):
        telemetry_summary.write(out)
        print(est_mod.compare(out))
    if outcome != "succeeded":
        raise SystemExit(f"job {outcome}; see {out / 'machine'} and the execution's logs in Cloud Logging")


if __name__ == "__main__":
    main()
