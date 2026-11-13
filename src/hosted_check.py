"""One-trial connectivity check of a model provider (no bundle is written).

Runs a single trial of one case in one condition through the reference agent,
exactly as a run would, prints the reply, the grade-relevant observations and
the traced calls (tokens, latency, finish reason, cost), and writes the spans to
``--spans`` (default: a scratch file). The default condition, ``tool``, uses
both native tool calling and JSON mode when the model searches.

    python src/hosted_check.py --provider openai --kodama-secrets ../kodama/config/secrets.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from pathlib import Path

from circumstances.models import TrialSpec
from circumstances.pack import load_pack

import telemetry
from pricing import PriceTable
from providers import DEFAULT_EMBED_MODELS, DEFAULT_MODELS, EMBED_PROVIDERS, PROVIDERS, chat_client, embed_client
from subject import CONDITIONS, RecallSubject
from telemetry_summary import call_cost, duration_ms, span_kind

ROOT = Path(__file__).resolve().parents[1]


async def check(args: argparse.Namespace) -> int:
    pack = load_pack(ROOT / "pack")
    case = pack.case(args.case)
    chat = chat_client(args.provider, args.model, kodama_secrets=args.kodama_secrets,
                       vertex_project=args.vertex_project, openai_api=args.openai_api)
    embed = embed_client(args.embed_provider, args.embed_model, kodama_secrets=args.kodama_secrets)
    spans_file = args.spans or Path(tempfile.mkdtemp()) / "check.spans.jsonl"
    spans_file.unlink(missing_ok=True)
    provider = telemetry.install(spans_file, {"e2.run_name": "hosted-check"})
    subject = RecallSubject(args.condition, chat_client=chat, embed_client=embed,
                            tracer=telemetry.tracer(provider))
    trial = TrialSpec(run_id="hosted-check", trial_id=f"{case.id}--1--check", pack_id=pack.manifest.id,
                      pack_version=pack.manifest.version, case=case, attempt=1, seed=20261110)
    session = await subject.prepare(trial)
    error = None
    try:
        events = await session.execute(case.actions[0], timeout_s=case.timeout_s)
    except Exception as exc:  # report, then fail
        events, error = [], f"{type(exc).__name__}: {exc}"
    finally:
        await session.close()
        provider.shutdown()
    prices, missing = PriceTable(), set()
    print(f"provider {chat.provider}/{chat.model}, embeddings {embed.provider}/{embed.model}, "
          f"case {case.id}, condition {args.condition}")
    for e in events:
        if e.kind == "message" and e.role == "assistant":
            print(f"  reply: {e.content!r}")
        elif e.kind in ("observation", "metric"):
            print(f"  {e.name} = {e.value}")
        elif e.kind == "tool_call":
            print(f"  tool call: {e.name} {json.dumps(e.arguments)}")
    total = 0.0
    for s in telemetry.read_spans(spans_file):
        a = s["attributes"]
        if a.get("gen_ai.operation.name") in ("chat", "embeddings"):
            cost = call_cost(s, prices, missing)
            total += cost
            print(f"  {span_kind(s):22s} {duration_ms(s):8.0f} ms  in {a.get('gen_ai.usage.input_tokens', '?'):>6}  "
                  f"out {a.get('gen_ai.usage.output_tokens', '-'):>4}  finish {a.get('gen_ai.response.finish_reasons', ['-'])[0]:10s}"
                  f"  ${cost:.6f}  {a.get('gen_ai.response.model', '')}")
    print(f"  total model spend ${total:.6f}; spans in {spans_file}")
    if missing:
        print(f"  no price for: {', '.join(sorted(missing))}")
    if error:
        print(f"  FAILED: {error}")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--provider", choices=PROVIDERS, required=True)
    parser.add_argument("--model", default=None, help=f"default: {DEFAULT_MODELS}")
    parser.add_argument("--embed-provider", choices=EMBED_PROVIDERS, default="ollama")
    parser.add_argument("--embed-model", default=None, help=f"default: {DEFAULT_EMBED_MODELS}")
    parser.add_argument("--condition", choices=CONDITIONS, default="tool")
    parser.add_argument("--case", default="recall-when-asked/anniversary-clock")
    parser.add_argument("--kodama-secrets", type=Path, default=None)
    parser.add_argument("--vertex-project", default=None)
    parser.add_argument("--openai-api", choices=["responses", "chat"], default="responses")
    parser.add_argument("--spans", type=Path, default=None)
    raise SystemExit(asyncio.run(check(parser.parse_args())))


if __name__ == "__main__":
    main()
