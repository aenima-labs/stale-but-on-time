"""Run Experiment 2 on a GPU machine in GCP, from start to teardown.

    python src/gcp_job.py --run e2-gcp-g4 [--machine-type g4-standard-48] [--yes | --estimate-only | --plan-only]

1. Estimate (trials, tokens, run time, machine cost for start-up + run +
   teardown, worst case at the hard lifetime) and confirmation, as for any run.
2. ``git archive`` of HEAD (the working tree must be clean), so the machine runs
   exactly a commit; nothing is pushed.
3. ``terraform apply`` of ``infra/gcp``: bucket, service account, network,
   machine. The machine installs Ollama and the models, runs ``inv e2.run``,
   uploads ``results/<run>`` and deletes itself.
4. Follow the machine's status markers in the bucket; copy the results back.
5. ``terraform destroy`` in a ``finally`` block: on success, failure, timeout
   or Ctrl-C. Compute Engine's ``max_run_duration`` deletes the machine even if
   this process dies.
6. ``machine.json`` (billed hours and cost), telemetry summary and
   ``estimate_vs_actual.md`` beside the bundles.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import estimate as est_mod
import telemetry_summary
from pricing import PriceTable, machine_cost

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "infra" / "gcp"
MARKERS = ("BOOTED", "MODELS_READY", "RUN_STARTED", "RUN_FINISHED", "DONE", "FAILED", "DELETING")


def sh(cmd: list[str], *, check: bool = True, capture: bool = False, cwd: Path | None = None) -> str:
    print("+ " + " ".join(cmd), flush=True)
    done = subprocess.run(cmd, cwd=cwd, check=check, text=True,
                          capture_output=capture)
    return done.stdout if capture else ""


def tf_vars(a: argparse.Namespace, tarball: Path) -> list[str]:
    pairs = {
        "run_id": a.run_id, "run_name": a.run, "run_args": a.args, "machine_type": a.machine_type,
        "zone": a.zone, "region": a.region, "spot": str(a.spot).lower(),
        "max_lifetime_hours": str(a.max_hours), "disk_gib": str(a.disk_gib),
        "models": json.dumps(a.models), "source_tarball": str(tarball),
    }
    out = []
    for k, v in pairs.items():
        out += ["-var", f"{k}={v}"]
    return out


def run_id_from(run: str) -> str:
    rid = re.sub(r"[^a-z0-9-]", "-", run.lower()).strip("-")[:20].rstrip("-")
    return rid if rid[:1].isalpha() else f"r{rid}"[:20]


def markers(bucket: str) -> dict[str, str]:
    out = subprocess.run(["gcloud", "storage", "ls", f"gs://{bucket}/status/"],
                         capture_output=True, text=True, check=False).stdout
    found = {}
    for line in out.split():
        name = line.rstrip("/").rsplit("/", 1)[-1]
        if name in MARKERS:
            text = subprocess.run(["gcloud", "storage", "cat", line], capture_output=True,
                                  text=True, check=False).stdout.strip()
            found[name] = text
    return found


def build_estimate(a: argparse.Namespace, out: Path) -> dict:
    spec = {"machine_type": a.machine_type, "region": a.region, "spot": a.spot,
            "disk_gib": a.disk_gib,
            "disk_type": "hyperdisk-balanced" if a.machine_type.startswith("g4-") else "pd-balanced",
            "startup_min": a.startup_min,
            "teardown_min": a.teardown_min, "max_lifetime_h": a.max_hours}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(spec, f)
    subprocess.run(
        [sys.executable, str(ROOT / "src" / "e2_run.py"), "--estimate-only", "--out", str(out),
         "--machine-json", f.name, *a.args.split()],
        check=True, capture_output=True, text=True,
    )
    return json.loads((out / "estimate.json").read_text())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--run", required=True, help="results/<run> to create (must not exist)")
    p.add_argument("--args", default="", help="extra e2_run.py arguments for the machine, e.g. '--model gemma4:26b'")
    p.add_argument("--machine-type", default="g4-standard-48")
    p.add_argument("--region", default="europe-west1")
    p.add_argument("--zone", default="europe-west1-b")
    p.add_argument("--spot", action="store_true")
    p.add_argument("--max-hours", type=int, default=4, help="hard machine lifetime")
    p.add_argument("--disk-gib", type=int, default=200)
    p.add_argument("--models", nargs="+", default=["gemma4:e4b", "nomic-embed-text"])
    p.add_argument("--startup-min", type=float, default=20.0)
    p.add_argument("--teardown-min", type=float, default=5.0)
    p.add_argument("--poll-s", type=int, default=60)
    p.add_argument("--yes", action="store_true")
    p.add_argument("--estimate-only", action="store_true")
    p.add_argument("--plan-only", action="store_true", help="terraform plan and stop (creates nothing)")
    a = p.parse_args()
    a.run_id = run_id_from(a.run)

    out = ROOT / "results" / a.run
    leftovers = {f.name for f in out.iterdir()} - {"estimate.json", "estimate.md"} if out.exists() else set()
    if leftovers and not (a.estimate_only or a.plan_only):
        raise SystemExit(f"{out} already holds a run; choose another --run.")
    est = build_estimate(a, out)
    saved_estimate = (out / "estimate.json").read_text(), (out / "estimate.md").read_text()
    if a.plan_only:
        print(est_mod.markdown(est))
    elif not est_mod.confirm(est, yes=a.yes, estimate_only=a.estimate_only):
        return

    if not a.plan_only and subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                                          text=True).stdout.strip():
        raise SystemExit("The working tree has changes; commit them so the machine runs a commit.")
    commit = sh(["git", "rev-parse", "--short", "HEAD"], capture=True, cwd=ROOT).strip()
    workdir = Path(tempfile.mkdtemp(prefix="sbot-gcp-"))
    tarball = workdir / f"source-{commit}.tgz"
    sh(["git", "archive", "--format=tar.gz", "-o", str(tarball), "HEAD"], cwd=ROOT)
    tfv = tf_vars(a, tarball)
    sh(["terraform", "init", "-input=false"], cwd=TF)
    if a.plan_only:
        try:
            sh(["terraform", "plan", "-input=false", *tfv], cwd=TF)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        return

    started = time.time()
    status: dict[str, str] = {}
    outcome = "not started"
    try:
        sh(["terraform", "apply", "-input=false", "-auto-approve", *tfv], cwd=TF)
        bucket = sh(["terraform", "output", "-raw", "bucket"], capture=True, cwd=TF).strip()
        deadline = started + a.max_hours * 3600 + 600
        seen: set[str] = set()
        while time.time() < deadline:
            status = markers(bucket)
            for name in MARKERS:
                if name in status and name not in seen:
                    seen.add(name)
                    print(f"[{dt.datetime.now(dt.UTC):%H:%M:%S}Z] {name}: {status[name]}", flush=True)
            if "DONE" in status or "FAILED" in status:
                break
            time.sleep(a.poll_s)
        outcome = "done" if "DONE" in status else "failed" if "FAILED" in status else "timed out"
        if "DONE" in status or "FAILED" in status:
            time.sleep(30)  # let the last uploads land
            out.parent.mkdir(parents=True, exist_ok=True)
            sh(["gcloud", "storage", "cp", "-r", f"gs://{bucket}/results/{a.run}", str(out.parent)], check=False)
            (out / "machine").mkdir(parents=True, exist_ok=True)
            sh(["gcloud", "storage", "cp", f"gs://{bucket}/log/job.log", str(out / "machine" / "job.log")],
               check=False)
    finally:
        sh(["terraform", "destroy", "-input=false", "-auto-approve", *tfv], cwd=TF, check=False)
        ended = time.time()
        shutil.rmtree(workdir, ignore_errors=True)
        out.mkdir(parents=True, exist_ok=True)
        # The task's own window (apply start to destroy end) bounds the billed time from above.
        hours = (ended - started) / 3600
        prices = PriceTable()
        mp = prices.machine_price(a.machine_type, a.region)
        disk = prices.disk_price_per_gib_hour(
            "hyperdisk-balanced" if a.machine_type.startswith("g4-") else "pd-balanced", a.region) or 0.0
        machine = {
            "machine_type": a.machine_type, "zone": a.zone, "spot": a.spot, "commit": commit,
            "outcome": outcome, "status_markers": status,
            "started_utc": dt.datetime.fromtimestamp(started, dt.UTC).isoformat(),
            "destroyed_utc": dt.datetime.fromtimestamp(ended, dt.UTC).isoformat(),
            "hours": hours,
            "cost_usd": machine_cost(mp, hours, spot=a.spot, disk_gib=a.disk_gib, disk_per_gib_hour=disk)
            if mp else float("nan"),
            "note": "Hours from terraform apply start to destroy end: an upper bound on the billed time.",
        }
        (out / "machine.json").write_text(json.dumps(machine, indent=2) + "\n")
        (out / "estimate.json").write_text(saved_estimate[0])
        (out / "estimate.md").write_text(saved_estimate[1])
        print(json.dumps(machine, indent=2))
    if (out / "telemetry").is_dir():
        telemetry_summary.write(out)
        print(est_mod.compare(out))
    if outcome != "done":
        raise SystemExit(f"job {outcome}; see {out / 'machine' / 'job.log'}")


if __name__ == "__main__":
    main()
