"""Experiment 2: run the async-recall pack once per memory condition.

Each condition is a separate Circumstances run with its own sealed bundle
under ``results/e2/<condition>/<run-id>/``. Seeds are fixed per job index, so
trial ``n`` of a case uses the same decoding seed in every condition.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import time
from pathlib import Path

from circumstances.artifacts import FileArtifactStore, verify_bundle
from circumstances.cli import _evaluator_registry
from circumstances.models import RunPlan
from circumstances.pack import lint_pack, load_pack
from circumstances.runner import run_loaded_pack
from scrub_paths import scrub_bundle
from circumstances.selftest import run_pack_selftests
from subject import CONDITIONS, RecallSubject

ROOT = Path(__file__).resolve().parents[1]
BASE_SEED = 20261110


async def run_condition(
    condition: str, model: str, cases: list[str] | None, out: Path, think: bool = False
) -> None:
    pack = load_pack(ROOT / "pack")
    subject = RecallSubject(condition, model=model, think=think)
    registry = _evaluator_registry()
    warnings = lint_pack(pack, subject_capabilities=set(subject.descriptor.capabilities))
    failures = await run_pack_selftests(pack, registry)
    if warnings or failures:
        raise SystemExit(f"pack is not clean: {warnings + failures}")
    jobs = sum(case.trials for case in pack.cases.values())
    started = time.time()
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
    print(
        json.dumps(
            {
                "condition": condition,
                "trials": len(summary.results),
                "passed": passed,
                "seconds": round(time.time() - started),
                "bundle": str(bundle.relative_to(ROOT)),
                "seal_problems": problems,
            }
        ),
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conditions", nargs="*", default=list(CONDITIONS))
    parser.add_argument("--model", default="gemma4:e4b")
    parser.add_argument("--case", action="append")
    parser.add_argument("--think", action="store_true", help="enable the model's reasoning mode")
    parser.add_argument("--out", default=str(ROOT / "results" / "e2"))
    args = parser.parse_args()
    for condition in args.conditions:
        asyncio.run(run_condition(condition, args.model, args.case, Path(args.out), args.think))


if __name__ == "__main__":
    main()
