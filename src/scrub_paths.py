"""Make sealed run bundles independent of the machine that produced them.

`run.json` records the absolute path of the pack (`lock.pack_source`). That is the only
local path in a bundle. This module rewrites it to the relative "pack" and re-seals
the bundle (the seal covers run.json), then verifies it with Circumstances.

    python src/scrub_paths.py results/e2 [results/e2-think ...]

Idempotent. Bundles still being written are hidden dot-directories and are skipped.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from circumstances.artifacts import verify_bundle


def canonical(value: object) -> bytes:
    """Byte format Circumstances uses for every JSON file it writes."""
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return text.encode() + b"\n"


def reseal(bundle: Path) -> None:
    """Recompute every file digest in seal.json after files in the bundle were edited."""
    seal_path = bundle / "seal.json"
    seal = json.loads(seal_path.read_text())
    seal["files"] = {
        p.relative_to(bundle).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(bundle.rglob("*"))
        if p.is_file() and p.name != "seal.json"
    }
    seal_path.write_bytes(canonical(seal))


def scrub_bundle(bundle: Path) -> bool:
    """Return True if the bundle was changed."""
    run_path = bundle / "run.json"
    raw = run_path.read_bytes()
    run = json.loads(raw)
    if canonical(run) != raw:
        raise SystemExit(f"{run_path}: not in canonical form, refusing to rewrite")
    lock = run.get("lock", {})
    source = lock.get("pack_source", "")
    if not Path(source).is_absolute():
        return False
    lock["pack_source"] = "pack"
    run_path.write_bytes(canonical(run))
    reseal(bundle)
    problems = verify_bundle(bundle)
    if problems:
        raise SystemExit(f"{bundle}: seal does not verify after scrub: {problems}")
    return True


def main(argv: list[str]) -> None:
    roots = [Path(a) for a in argv] or [Path("results/e2")]
    for root in roots:
        for seal in sorted(root.glob("*/*/seal.json")):
            changed = scrub_bundle(seal.parent)
            print(("scrubbed " if changed else "clean    ") + str(seal.parent))


if __name__ == "__main__":
    main(sys.argv[1:])
