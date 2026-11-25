"""Development aid for the deeper recall step: what it rates and loads on the four
development cases, with the whole conversation (fresh) and with the lead-in only
(stale). The cases are in pack-src/dev-slow-recall.yaml and are not in the pack.

    uv run python src/dev_slow_recall.py
"""

from __future__ import annotations

import time
from pathlib import Path

import yaml

from subject import RecallSession, RecallSubject

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    subject = RecallSubject("deep")
    session = RecallSession.__new__(RecallSession)
    session.subject = subject
    session.memorome = subject.memorome("tessaly-v1")
    for case in yaml.safe_load((ROOT / "pack-src" / "dev-slow-recall.yaml").read_text())["cases"]:
        lead_in = [{"role": "user", "content": case["u1"]}, {"role": "assistant", "content": case["a1"]}]
        for name, turns in (("stale", lead_in), ("fresh", [*lead_in, {"role": "user", "content": case["u2"]}])):
            started = time.perf_counter()
            pages, rated = session._deep_recall(turns, "dev")
            seconds = time.perf_counter() - started
            gold = case["gold"][0]
            rank = rated["candidates"].index(gold) + 1 if gold in rated["candidates"] else None
            score = rated["scores"][rank - 1] if rank else None
            print(f"{case['id']:14s} {name}  {seconds:4.1f} s  gold rank {rank}  gold score {score}  "
                  f"loaded gold {gold in pages}  scores {rated['scores']}  loaded {pages}")


if __name__ == "__main__":
    main()
