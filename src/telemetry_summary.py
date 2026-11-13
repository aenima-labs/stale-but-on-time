"""Summarise the telemetry of a run: latency, tokens, calls and cost per condition.

Reads ``results/<run>/telemetry/<condition>.spans.jsonl`` (written by
``e2_run.py``) and writes ``results/<run>/telemetry_summary.json`` and
``results/<run>/telemetry_summary.md``.

One trace is one trial. Per condition the summary gives:

- latency (median and 90th percentile, ms) per span kind: the trial, the reply
  path, each model call by purpose, each embedding call by purpose, each
  retrieval by placement and each tool round;
- tokens in and out per trial (chat calls), embedding tokens per trial, model
  calls per trial;
- cost per trial and per run from ``pricing/prices.yaml``, at the price valid on
  the day of each call. Indexing the memorome (embedding the 48 notes once per
  condition) is a per-run overhead and is reported apart from the per-trial
  figures.

    python src/telemetry_summary.py --run e2-smoke
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from pricing import PriceTable, token_cost
from providers import RELOAD_MS
from telemetry import read_spans

ROOT = Path(__file__).resolve().parents[1]
CONDITION_ORDER = ("none", "tool", "blocking", "lag1", "prefetch50", "hybrid")
PROVIDER_FROM_SEMCONV = {"gcp.vertex_ai": "vertex"}


CHAT_OPS = ("chat", "generate_content", "text_completion")


def span_kind(span: dict) -> str:
    a = span.get("attributes", {})
    op = a.get("gen_ai.operation.name")
    if span["name"] == "trial":
        return "trial"
    if op in CHAT_OPS:
        return f"chat:{a.get('e2.call.purpose', '')}"
    if op == "embeddings":
        return f"embeddings:{a.get('e2.call.purpose', '')}"
    if op == "execute_tool":
        return "execute_tool"
    if span["name"] == "memory.recall":
        return f"recall:{a.get('e2.recall.placement', '')}"
    return span["name"]


def duration_ms(span: dict) -> float:
    return (span["end_unix_nano"] - span["start_unix_nano"]) / 1e6


def _provider(span: dict) -> str:
    name = span.get("attributes", {}).get("gen_ai.provider.name", "")
    return PROVIDER_FROM_SEMCONV.get(name, name)


def _day(span: dict) -> dt.date:
    return dt.datetime.fromtimestamp(span["start_unix_nano"] / 1e9, dt.UTC).date()


def call_cost(span: dict, prices: PriceTable, missing: set[str]) -> float:
    a = span.get("attributes", {})
    model = a.get("gen_ai.response.model") or a.get("gen_ai.request.model", "")
    price = prices.token_price(_provider(span), str(model), _day(span))
    if price is None:
        price = prices.token_price(_provider(span), str(a.get("gen_ai.request.model", "")), _day(span))
    if price is None:
        missing.add(f"{_provider(span)}/{a.get('gen_ai.request.model', '')}")
        return float("nan")
    return token_cost(
        price,
        float(a.get("gen_ai.usage.input_tokens", 0) or 0),
        float(a.get("gen_ai.usage.output_tokens", 0) or 0),
        float(a.get("gen_ai.usage.cache_read.input_tokens", 0) or 0),
    )


def trial_records(spans: list[dict], prices: PriceTable, missing: set[str]) -> tuple[list[dict], dict]:
    """Per-trial totals, and the per-run overhead (memorome indexing)."""
    by_trace: dict[str, list[dict]] = defaultdict(list)
    for span in spans:
        by_trace[span["trace_id"]].append(span)
    trials, overhead = [], {"embed_tokens": 0, "cost_usd": 0.0, "calls": 0}
    for trace_spans in by_trace.values():
        root = next((s for s in trace_spans if s["name"] == "trial"), None)
        rec = {
            "trial_id": (root or {}).get("attributes", {}).get("circumstances.trial_id", ""),
            "chat_calls": 0, "input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0,
            "reasoning_tokens": 0, "embed_calls": 0, "embed_tokens": 0, "cost_usd": 0.0,
            "tokens_missing": 0, "errors": 0,
            "wall_ms": duration_ms(root) if root else float("nan"),
            "path_total_ms": (root or {}).get("attributes", {}).get("e2.path.total_ms", float("nan")),
        }
        for s in trace_spans:
            a = s.get("attributes", {})
            if s.get("status", {}).get("code") == "error":
                rec["errors"] += 1
            op = a.get("gen_ai.operation.name")
            if op in CHAT_OPS:
                rec["chat_calls"] += 1
                if "gen_ai.usage.input_tokens" not in a:
                    rec["tokens_missing"] += 1
                rec["input_tokens"] += int(a.get("gen_ai.usage.input_tokens", 0) or 0)
                rec["output_tokens"] += int(a.get("gen_ai.usage.output_tokens", 0) or 0)
                rec["cached_input_tokens"] += int(a.get("gen_ai.usage.cache_read.input_tokens", 0) or 0)
                rec["reasoning_tokens"] += int(a.get("gen_ai.usage.reasoning.output_tokens", 0) or 0)
                rec["cost_usd"] += call_cost(s, prices, missing)
            elif op == "embeddings":
                tokens = int(a.get("gen_ai.usage.input_tokens", 0) or 0)
                if a.get("e2.call.purpose") == "index":
                    overhead["embed_tokens"] += tokens
                    overhead["cost_usd"] += call_cost(s, prices, missing)
                    overhead["calls"] += 1
                else:
                    rec["embed_calls"] += 1
                    rec["embed_tokens"] += tokens
                    rec["cost_usd"] += call_cost(s, prices, missing)
        if root is not None:
            trials.append(rec)
    return trials, overhead


def _stats(values: list[float]) -> dict:
    v = np.asarray([x for x in values if x == x], dtype=float)  # drop NaN
    if not len(v):
        return {"n": 0}
    return {
        "n": int(len(v)),
        "mean": float(v.mean()),
        "median": float(np.median(v)),
        "p90": float(np.percentile(v, 90)),
        "sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0,
    }


def summarise_condition(spans: list[dict], prices: PriceTable) -> dict:
    missing: set[str] = set()
    trials, overhead = trial_records(spans, prices, missing)
    latency: dict[str, list[float]] = defaultdict(list)
    for span in spans:
        latency[span_kind(span)].append(duration_ms(span))
    models = sorted({
        f"{_provider(s)}/{s['attributes'].get('gen_ai.request.model', '')}"
        for s in spans if s.get("attributes", {}).get("gen_ai.operation.name") in (*CHAT_OPS, "embeddings")
    })
    ollama_calls = [s for s in spans if "ollama.total_duration_ms" in s.get("attributes", {})]
    reloads = [s for s in ollama_calls if s["attributes"].get("ollama.load_duration_ms", 0) > RELOAD_MS]
    per_trial_keys = ("chat_calls", "input_tokens", "output_tokens", "cached_input_tokens",
                      "reasoning_tokens", "embed_tokens", "cost_usd", "wall_ms", "path_total_ms")
    total = lambda k: float(sum(t[k] for t in trials))  # noqa: E731
    starts = [s["start_unix_nano"] for s in spans]
    ends = [s["end_unix_nano"] for s in spans]
    return {
        "trials": len(trials),
        "models": models,
        "latency_ms": {k: {"median": _stats(v)["median"], "p90": _stats(v)["p90"], "n": len(v)}
                       for k, v in sorted(latency.items())},
        "per_trial": {k: _stats([t[k] for t in trials]) for k in per_trial_keys},
        "totals": {
            "chat_calls": int(total("chat_calls")),
            "input_tokens": int(total("input_tokens")),
            "output_tokens": int(total("output_tokens")),
            "cached_input_tokens": int(total("cached_input_tokens")),
            "embed_tokens": int(total("embed_tokens")) + overhead["embed_tokens"],
            "cost_usd": total("cost_usd") + overhead["cost_usd"],
            "wall_s": (max(ends) - min(starts)) / 1e9 if spans else 0.0,
            "errors": int(sum(t["errors"] for t in trials)),
            "chat_calls_without_tokens": int(sum(t["tokens_missing"] for t in trials)),
        },
        "overhead_index": overhead,
        "ollama_model_loads": {
            "calls": len(ollama_calls),
            "calls_with_load": len(reloads),
            "trials_affected": len({s["trace_id"] for s in reloads}),
            "threshold_ms": RELOAD_MS,
        },
        "prices_missing": sorted(missing),
    }


def kodama_spans(path: Path, provider: str = "ollama") -> list[dict]:
    """Spans of a product run (Experiment 3) in this module's schema.

    ``path`` is a ``<condition>.kodama-traces.jsonl`` written by Kodama's eval
    plugin: one line per trial with the session's span dumps
    (``GET /v1/sessions/{id}/traces``). All turns of a trial get one trace id,
    and a ``trial`` root span spans them, so a trial is one trace as in
    Experiment 2. A model call's purpose is the name of its nearest
    ``kodama.*`` ancestor (``kodama.turn``, ``kodama.classifier.advice``, ...).
    ``provider`` fills ``gen_ai.provider.name`` when Kodama did not record it.
    """
    import hashlib

    out: list[dict] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        trace_id = hashlib.sha256(record["trial_id"].encode()).hexdigest()[:32]
        spans = [dict(s) for t in record.get("traces", []) for s in (t.get("spans") or [])]
        by_id = {s.get("span_id"): s for s in spans}
        for s in spans:
            a = dict(s.get("attributes") or {})
            if a.get("gen_ai.operation.name") in (*CHAT_OPS, "embeddings"):
                a.setdefault("gen_ai.provider.name", provider)
                parent, purpose = by_id.get(s.get("parent_span_id")), ""
                while parent is not None and not purpose:
                    if str(parent.get("name", "")).startswith("kodama."):
                        purpose = parent["name"]
                    parent = by_id.get(parent.get("parent_span_id"))
                a.setdefault("e2.call.purpose", purpose)
            out.append({
                "trace_id": trace_id, "span_id": s.get("span_id", ""),
                "parent_span_id": s.get("parent_span_id", ""), "name": s.get("name", ""),
                "kind": "internal", "start_unix_nano": int(s["start_unix_nano"]),
                "end_unix_nano": int(s["end_unix_nano"]),
                "status": {"code": str((s.get("status") or {}).get("code", "unset")).lower()},
                "attributes": a, "events": [],
            })
        if spans:
            out.append({
                "trace_id": trace_id, "span_id": f"trial-{trace_id[:12]}", "parent_span_id": "",
                "name": "trial", "kind": "internal",
                "start_unix_nano": min(int(s["start_unix_nano"]) for s in spans),
                "end_unix_nano": max(int(s["end_unix_nano"]) for s in spans),
                "status": {"code": "unset"},
                "attributes": {"circumstances.trial_id": record["trial_id"],
                               "circumstances.case_id": record.get("case_id", ""),
                               "circumstances.trial.attempt": record.get("attempt", 0),
                               "circumstances.trial.seed": record.get("seed", 0)},
                "events": [],
            })
    return out


def load_run(run_dir: Path) -> dict[str, list[dict]]:
    files = sorted((run_dir / "telemetry").glob("*.spans.jsonl"))
    out = {f.name.removesuffix(".spans.jsonl"): read_spans(f) for f in files}
    for f in sorted((run_dir / "telemetry").glob("*.kodama-traces.jsonl")):
        out[f.name.removesuffix(".kodama-traces.jsonl")] = kodama_spans(f)
    return {c: out[c] for c in sorted(out, key=lambda c: ((CONDITION_ORDER + (c,)).index(c), c))}


def summarise_run(run_dir: Path, prices: PriceTable | None = None) -> dict:
    prices = prices or PriceTable()
    conditions = {c: summarise_condition(spans, prices) for c, spans in load_run(run_dir).items()}
    return {
        "run": run_dir.name,
        "conditions": conditions,
        "run_totals": {
            "trials": sum(c["trials"] for c in conditions.values()),
            "chat_calls": sum(c["totals"]["chat_calls"] for c in conditions.values()),
            "input_tokens": sum(c["totals"]["input_tokens"] for c in conditions.values()),
            "output_tokens": sum(c["totals"]["output_tokens"] for c in conditions.values()),
            "embed_tokens": sum(c["totals"]["embed_tokens"] for c in conditions.values()),
            "cost_usd": sum(c["totals"]["cost_usd"] for c in conditions.values()),
            "wall_s": sum(c["totals"]["wall_s"] for c in conditions.values()),
        },
        "prices": str((ROOT / "pricing" / "prices.yaml").relative_to(ROOT)),
    }


def _f(x: float, digits: int = 0) -> str:
    return "–" if x != x else f"{x:,.{digits}f}"


def _usd(x: float) -> str:
    return "–" if x != x else (f"${x:.4f}" if x < 1 else f"${x:,.2f}")


def markdown(summary: dict) -> str:
    lines = [f"# Telemetry summary: `{summary['run']}`", ""]
    lines += ["Per trial: mean (median). Latency: median / 90th percentile, ms.", ""]
    lines += ["| condition | trials | model calls | tokens in | tokens out | embed tokens | cost / trial | cost (run) | trial ms (p50 / p90) |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, c in summary["conditions"].items():
        p = c["per_trial"]
        def mm(k: str, d: int = 0) -> str:
            s = p[k]
            return "–" if not s.get("n") else f"{_f(s['mean'], d)} ({_f(s['median'], d)})"
        trial = c["latency_ms"].get("trial", {})
        lines.append(
            f"| {name} | {c['trials']} | {mm('chat_calls', 2)} | {mm('input_tokens')} | {mm('output_tokens')} "
            f"| {mm('embed_tokens')} | {_usd(p['cost_usd'].get('mean', float('nan')))} | {_usd(c['totals']['cost_usd'])} "
            f"| {_f(trial.get('median', float('nan')))} / {_f(trial.get('p90', float('nan')))} |"
        )
    t = summary["run_totals"]
    lines += ["", f"Run: {t['trials']} trials, {t['chat_calls']} model calls, {t['input_tokens']:,} tokens in, "
              f"{t['output_tokens']:,} tokens out, {t['embed_tokens']:,} embedding tokens, cost {_usd(t['cost_usd'])}, "
              f"{t['wall_s'] / 60:.1f} min of trial time.", ""]
    lines += ["## Latency per span kind (ms, median / p90, n)", ""]
    kinds = sorted({k for c in summary["conditions"].values() for k in c["latency_ms"]})
    names = list(summary["conditions"])
    lines += ["| span kind | " + " | ".join(names) + " |", "|---|" + "---:|" * len(names)]
    for k in kinds:
        cells = []
        for n in names:
            s = summary["conditions"][n]["latency_ms"].get(k)
            cells.append("" if not s else f"{_f(s['median'])} / {_f(s['p90'])} ({s['n']})")
        lines.append(f"| {k} | " + " | ".join(cells) + " |")
    notes = []
    for n, c in summary["conditions"].items():
        if c["prices_missing"]:
            notes.append(f"- {n}: no price for {', '.join(c['prices_missing'])}; cost shown as –.")
        if c["totals"]["chat_calls_without_tokens"]:
            notes.append(f"- {n}: {c['totals']['chat_calls_without_tokens']} model calls returned no token counts.")
        if c["totals"]["errors"]:
            notes.append(f"- {n}: {c['totals']['errors']} spans ended with an error.")
        loads = c["ollama_model_loads"]
        if loads["calls_with_load"] > len(c["models"]):  # more than the first load of each model
            notes.append(f"- {n}: **{loads['calls_with_load']} of {loads['calls']} Ollama calls loaded a model** "
                         f"(load > {loads['threshold_ms']:.0f} ms) in {loads['trials_affected']} trials; their "
                         "latencies include model loading and are not comparable with the stored runs.")
        oh = c["overhead_index"]
        if oh["calls"]:
            notes.append(f"- {n}: indexing the memorome took {oh['calls']} embedding call(s), "
                         f"{oh['embed_tokens']:,} tokens, {_usd(oh['cost_usd'])} (in the run cost, not per trial).")
    if notes:
        lines += ["", "## Notes", "", *notes]
    lines += ["", f"Prices: `{summary['prices']}` (each entry has its source and the date it was read)."]
    return "\n".join(lines) + "\n"


def write(run_dir: Path) -> dict:
    summary = summarise_run(run_dir)
    (run_dir / "telemetry_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (run_dir / "telemetry_summary.md").write_text(markdown(summary))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="run name under results/, or a path")
    args = parser.parse_args()
    run_dir = Path(args.run) if "/" in args.run else ROOT / "results" / args.run
    summary = write(run_dir)
    print(markdown(summary))


if __name__ == "__main__":
    main()
