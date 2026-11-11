"""Generate the Circumstances pack and the memorome fixture from one source.

Packs are data. This script only expands ``pack-src/tessaly.yaml`` into the
directory layout of pack format v4 and checks the authored cases.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pack-src" / "tessaly.yaml"
PACK = ROOT / "pack"
FIXTURE = ROOT / "fixtures" / "tessaly-v1.json"
TRIALS = 5

RULES = {
    "recall-when-asked": {
        "title": "State the remembered fact when asked",
        "description": (
            "When the listener asks for a fact that the memorome contains, the "
            "spoken reply states that fact."
        ),
        "severity": "medium",
        "tags": ["recall", "grounding"],
    },
    "recall-unprompted": {
        "title": "Bring up a relevant memory without being asked",
        "description": (
            "When the listener's remark relates to a memory and no question is "
            "asked, the reply brings that memory up (proactive recall)."
        ),
        "severity": "low",
        "tags": ["recall", "proactive"],
    },
    "abstain-when-silent": {
        "title": "Abstain when the memorome is silent",
        "description": (
            "When the memorome does not contain the requested fact, the agent "
            "says it does not know instead of guessing or inferring."
        ),
        "severity": "high",
        "tags": ["grounding", "abstention"],
        "evaluators": [
            {
                "id": "abstained",
                "type": "outcome.state",
                "tier": "outcome",
                "config": {"observation": "reply.abstained", "equals": True},
            }
        ],
        "selftests": [
            {
                "evaluator_id": "abstained",
                "expected_status": "pass",
                "events": [
                    {"kind": "observation", "sequence": 0, "name": "reply.abstained", "value": True}
                ],
            },
            {
                "evaluator_id": "abstained",
                "expected_status": "fail",
                "events": [
                    {"kind": "observation", "sequence": 0, "name": "reply.abstained", "value": False}
                ],
            },
        ],
    },
}
CLASS_RULE = {
    "asked-continuing": ("recall-when-asked", "positive"),
    "asked-shift": ("recall-when-asked", "recovery"),
    "unprompted": ("recall-unprompted", "normal"),
    "abstain": ("abstain-when-silent", "negative"),
}


def dump(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=100))


def main() -> None:
    source = yaml.safe_load(SOURCE.read_text())
    memorome: dict[str, str] = source["memorome"]

    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(
        json.dumps({"persona": source["persona"], "memorome": memorome}, indent=1, ensure_ascii=False)
    )
    digest = "sha256:" + hashlib.sha256(FIXTURE.read_bytes()).hexdigest()

    if PACK.exists():
        shutil.rmtree(PACK)
    dump(
        PACK / "pack.yaml",
        {
            "format_version": 4,
            "id": "aenima/async-recall",
            "version": "1.0.0",
            "title": "Asynchronous recall in a live conversation",
            "description": (
                "Recall when asked, recall unprompted, and abstention, each after a "
                "scripted two-utterance lead-in that either continues or abruptly "
                "changes the topic."
            ),
            "license": "Apache-2.0",
            "publisher": {"name": "Aenima Labs", "url": "https://aenimalabs.com"},
            "created_at": "2026-11-10T00:00:00Z",
            "reviewed_at": "2026-11-10T00:00:00Z",
            "required_capabilities": ["message.text"],
            "permissions": [],
            "tags": ["recall", "memory", "fictional-fixtures"],
            "evaluators": [],
            "selftests": [],
        },
    )
    for rule_id, rule in RULES.items():
        dump(
            PACK / "rules" / rule_id / "rule.yaml",
            {
                "id": rule_id,
                "title": rule["title"],
                "description": rule["description"],
                "severity": rule["severity"],
                "tags": rule["tags"],
                "provenance": ["Written for this study; fictional"],
                "evaluators": rule.get("evaluators", []),
                "selftests": rule.get("selftests", []),
            },
        )

    seen: set[str] = set()
    for case in source["cases"]:
        rule_id, polarity = CLASS_RULE[case["class"]]
        assert case["id"] not in seen, case["id"]
        seen.add(case["id"])
        for gold in case["gold"]:
            assert gold in memorome, (case["id"], gold)
        evaluators: list[dict] = []
        selftests: list[dict] = []
        if case["class"] != "abstain":
            keys = [str(k) for k in case["keys"]]
            gold_text = " ".join(memorome[g] for g in case["gold"])
            # Every key must be literally recoverable from a gold page, and no
            # key may already be present in the scripted lead-in.
            lead_in = " ".join([case["u1"], case["a1"], case["u2"]]).casefold()
            assert any(k.casefold() in gold_text.casefold() for k in keys), case["id"]
            assert not any(k.casefold() in lead_in for k in keys), case["id"]
            evaluators.append(
                {
                    "id": "key-fact",
                    "type": "smoke.text",
                    "tier": "smoke",
                    "config": {"contains_any": keys},
                }
            )
            selftests = [
                {
                    "evaluator_id": "key-fact",
                    "expected_status": "pass",
                    "events": [
                        {"kind": "message", "sequence": 0, "role": "assistant", "content": gold_text}
                    ],
                },
                {
                    "evaluator_id": "key-fact",
                    "expected_status": "fail",
                    "events": [
                        {
                            "kind": "message",
                            "sequence": 0,
                            "role": "assistant",
                            "content": "I don't know; I have no memory of that.",
                        }
                    ],
                },
            ]
        else:
            assert "keys" not in case and not case["gold"], case["id"]
        dump(
            PACK / "rules" / rule_id / "cases" / case["id"] / "case.yaml",
            {
                "id": f"{rule_id}/{case['id']}",
                "title": case["u2"],
                "description": f"{case['class']} after a {case['continuity']} lead-in.",
                "targets": [rule_id],
                "polarity": polarity,
                "actors": {"user": "grandchild"},
                "fixture": {
                    "type": "asyncrecall.memorome",
                    "version": "1",
                    "digest": digest,
                    "privacy": "public",
                    "config": {
                        "memorome": "tessaly-v1",
                        "history": [
                            {"role": "user", "content": case["u1"]},
                            {"role": "assistant", "content": case["a1"]},
                        ],
                    },
                },
                "actions": [{"kind": "message", "role": "user", "content": case["u2"]}],
                "expected_outcomes": (
                    ["Say that the memories do not contain the answer."]
                    if case["class"] == "abstain"
                    else [f"Mention a fact from: {', '.join(case['gold'])}."]
                ),
                "evaluators": evaluators,
                "selftests": selftests,
                "trials": TRIALS,
                "timeout_s": 120,
                "holdout": False,
                "tags": [
                    "fictional",
                    f"class:{case['class']}",
                    f"continuity:{case['continuity']}",
                    *[f"gold:{g}" for g in case["gold"]],
                ],
            },
        )
    print(f"{len(memorome)} memorome pages, {len(seen)} cases, fixture {digest[:19]}…")


if __name__ == "__main__":
    main()
