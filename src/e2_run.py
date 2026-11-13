"""Experiment 2: run the async-recall pack once per memory condition.

Each condition is a separate Circumstances run with its own sealed bundle
under ``results/<run>/<condition>/<run-id>/``. Seeds are fixed per job index, so
trial ``n`` of a case uses the same decoding seed in every condition.

Before the run, an estimate (trials, model calls, tokens, spend, duration) is
printed and written to ``results/<run>/estimate.{json,md}``. A run that spends
money waits for confirmation (``--yes`` skips it; ``--estimate-only`` stops
after the estimate). Local runs do not wait.

Every trial is traced with OpenTelemetry into
``results/<run>/telemetry/<condition>.spans.jsonl`` (and to an OTLP endpoint if
``OTEL_EXPORTER_OTLP_ENDPOINT`` is set). After the run,
``telemetry_summary.{json,md}``, ``actual.json`` and ``estimate_vs_actual.md``
are written beside the bundles. The sealed bundles are unchanged in format.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import time
from pathlib import Path

from circumstances.artifacts import FileArtifactStore, verify_bundle
from circumstances.cli import _evaluator_registry
from circumstances.models import RunPlan
from circumstances.pack import lint_pack, load_pack
from circumstances.runner import run_loaded_pack
from circumstances.selftest import run_pack_selftests

import estimate as est_mod
import telemetry
import telemetry_summary
from providers import (
    DEFAULT_EMBED_MODELS,
    DEFAULT_MODELS,
    EMBED_PROVIDERS,
    PROVIDERS,
    chat_client,
    embed_client,
)
from scrub_paths import scrub_bundle
from subject import CONDITIONS, RecallSubject

ROOT = Path(__file__).resolve().parents[1]
BASE_SEED = 20261110


async def run_condition(
    condition: str,
    cases: list[str] | None,
    out: Path,
    *,
    think: bool = False,
    make_clients=None,
    trace_file: Path | None = None,
    resource: dict[str, str] | None = None,
) -> dict:
    pack = load_pack(ROOT / "pack")
    chat, embed = make_clients() if make_clients else (None, None)
    provider = telemetry.install(trace_file, resource or {}) if trace_file else None
    subject = RecallSubject(
        condition, think=think, chat_client=chat, embed_client=embed,
        tracer=telemetry.tracer(provider),
    )
    registry = _evaluator_registry()
    warnings = lint_pack(pack, subject_capabilities=set(subject.descriptor.capabilities))
    failures = await run_pack_selftests(pack, registry)
    if warnings or failures:
        raise SystemExit(f"pack is not clean: {warnings + failures}")
    jobs = sum(case.trials for case in pack.cases.values())
    started = time.time()
    try:
        summary = await run_loaded_pack(
            pack,
            RunPlan(
                pack_ref="pack",
                case_ids=cases,
                subject=subject.descriptor.id,
                repetitions=1,
                seeds=[BASE_SEED + n for n in range(jobs)],
                concurrency=1,
                retention="artifacts",
            ),
            subject=subject,
            evaluators=registry,
        )
    finally:
        if provider is not None:
            provider.shutdown()  # writes every pending span
    target = out / condition
    if target.exists():
        shutil.rmtree(target)
    files = {
        p.relative_to(pack.root).as_posix(): p.read_bytes()
        for p in pack.root.rglob("*")
        if p.is_file()
    }
    bundle = FileArtifactStore(target).persist(summary, pack_files=files)
    scrub_bundle(bundle)  # keep the author's absolute pack path out of the sealed bundle
    problems = verify_bundle(bundle)
    passed = sum(result.passed for result in summary.results)
    line = {
        "condition": condition,
        "trials": len(summary.results),
        "passed": passed,
        "seconds": round(time.time() - started),
        "bundle": str(bundle.relative_to(ROOT)) if bundle.is_relative_to(ROOT) else str(bundle),
        "seal_problems": problems,
    }
    print(json.dumps(line), flush=True)
    return line


def select_cases(pack, cases: list[str] | None, max_cases: int | None) -> list[str]:
    """The case ids to run. ``max_cases`` takes cases spread evenly over the pack."""
    ids = cases or list(pack.cases)
    if max_cases and max_cases < len(ids):
        step = len(ids) / max_cases
        ids = [ids[int(i * step)] for i in range(max_cases)]
    return ids


def default_profile(provider: str, model: str, think: bool) -> str:
    """The newest run with telemetry of the same provider and model, else a stored run."""
    runs = sorted(
        (d for d in (ROOT / "results").iterdir()
         if d.is_dir() and any((d / "telemetry").glob("*.spans.jsonl"))),
        key=lambda d: d.stat().st_mtime, reverse=True,
    )
    for d in runs:
        p = est_mod.profile_from_telemetry(d)
        if p["provider"] == provider and p["model"] == model and bool(p["think"]) == think:
            return d.name
    return "e2-think" if think else "e2-qwen3" if model == "qwen3:8b" else "e2"


def git_commit() -> str:
    done = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True, check=False)
    return done.stdout.strip() or "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--conditions", nargs="*", default=list(CONDITIONS))
    parser.add_argument("--provider", choices=PROVIDERS, default="ollama",
                        help="chat model provider (default: local Ollama)")
    parser.add_argument("--model", default=None,
                        help=f"chat model (defaults: {', '.join(f'{k}={v}' for k, v in DEFAULT_MODELS.items())})")
    parser.add_argument("--embed-provider", choices=EMBED_PROVIDERS, default="ollama",
                        help="embedding provider for the retriever (default: local nomic-embed-text)")
    parser.add_argument("--embed-model", default=None)
    parser.add_argument("--case", action="append", help="run only this case (repeatable)")
    parser.add_argument("--max-cases", type=int, default=None,
                        help="run only this many cases, spread evenly over the pack (pilots)")
    parser.add_argument("--think", action="store_true", help="enable the model's reasoning mode")
    parser.add_argument("--out", default=str(ROOT / "results" / "e2"))
    parser.add_argument("--profile", default=None,
                        help="run (name under results/ or path) whose telemetry or bundles the estimate scales")
    parser.add_argument("--kodama-secrets", type=Path, default=None,
                        help="Kodama's config/secrets.yaml, read for API keys not in the environment")
    parser.add_argument("--vertex-project", default=None, help="GCP project for Vertex (or VERTEX_PROJECT)")
    parser.add_argument("--yes", action="store_true", help="start a run that spends money without asking")
    parser.add_argument("--estimate-only", action="store_true", help="print the estimate and stop")
    parser.add_argument("--no-telemetry", action="store_true", help="do not write spans")
    parser.add_argument("--machine-json", type=Path, default=None,
                        help="(GCP job) a machine spec for the estimate; see tasks/gcp.py")
    args = parser.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = (Path.cwd() / out).resolve()
    model = args.model or DEFAULT_MODELS[args.provider]
    embed_model = args.embed_model or DEFAULT_EMBED_MODELS[args.embed_provider]
    pack = load_pack(ROOT / "pack")
    cases = select_cases(pack, args.case, args.max_cases)
    selected = None if (args.case is None and args.max_cases is None) else cases
    trials_per_condition = sum(pack.case(c).trials for c in cases)

    machine = None
    if args.machine_json:
        spec = json.loads(args.machine_json.read_text())
        spec["duration_factor"] = tuple(spec.get("duration_factor", (0.25, 0.5, 1.0)))
        machine = est_mod.MachineSpec(**spec)
    plan = est_mod.Plan(
        run=out.name, conditions=list(args.conditions),
        trials={c: trials_per_condition for c in args.conditions},
        provider=args.provider, model=model, embed_provider=args.embed_provider,
        embed_model=embed_model, think=args.think, machine=machine,
    )
    profile_name = args.profile or default_profile(args.provider, model, args.think)
    estimate = est_mod.estimate(plan, est_mod.load_profile(profile_name))

    def make_clients():
        return (
            chat_client(args.provider, model, kodama_secrets=args.kodama_secrets,
                        vertex_project=args.vertex_project),
            embed_client(args.embed_provider, embed_model, kodama_secrets=args.kodama_secrets),
        )

    if not args.estimate_only:
        make_clients()  # a missing key stops here, before anything runs
    est_mod.write_estimate(estimate, out)
    if not est_mod.confirm(estimate, yes=args.yes, estimate_only=args.estimate_only):
        return

    resource = {
        "e2.run_name": out.name,
        "e2.git_commit": git_commit(),
        "e2.provider": args.provider,
        "e2.model": model,
        "e2.embed_provider": args.embed_provider,
        "e2.embed_model": embed_model,
    }
    for condition in args.conditions:
        trace_file = None
        if not args.no_telemetry:
            trace_file = out / "telemetry" / f"{condition}.spans.jsonl"
            trace_file.unlink(missing_ok=True)
        asyncio.run(run_condition(
            condition, selected, out, think=args.think, make_clients=make_clients,
            trace_file=trace_file, resource={**resource, "e2.condition": condition},
        ))
    if not args.no_telemetry:
        summary = telemetry_summary.write(out)
        print(telemetry_summary.markdown(summary))
        print(est_mod.compare(out))


if __name__ == "__main__":
    main()
