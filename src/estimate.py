"""Estimate a run before it starts, and compare the estimate with what happened.

An estimate needs a *profile*: per condition, one record per trial with model
calls, tokens in and out, embedding tokens and wall time. Two sources:

- ``telemetry``: the spans of an earlier run (``results/<run>/telemetry``),
  measured token counts. A pilot of a few trials is such a run.
- ``bundles``: the sealed bundles of a run without telemetry (the stored
  ``results/e2``). The prompt of every call is rebuilt exactly from the pack,
  the fixture and the recorded retrievals; tokens are counted as characters / 4,
  which is a rule of thumb for English text and is given a wide range.

The estimate scales the profile to the planned number of trials. When the
profile comes from the same provider and model with measured tokens, the range
is the sampling spread (at least ±10%). Otherwise the range is wide and its top
is a hard ceiling: every trial makes the most calls its condition allows and
every call writes its whole output budget.

Spend is the sum of model calls at the prices in ``pricing/prices.yaml`` and,
for a cloud machine, the machine for start-up, the run and teardown. The worst
case for a machine is its hard maximum lifetime.
"""

from __future__ import annotations

import datetime as dt
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from pricing import PriceTable, machine_cost, token_cost
from telemetry_summary import load_run, summarise_run, trial_records

ROOT = Path(__file__).resolve().parents[1]
MAX_CALLS = {"none": 1, "tool": 2, "blocking": 1, "lag1": 1, "prefetch50": 1, "hybrid": 2}
RECALLS_MAX = {"none": 0, "tool": 1, "blocking": 1, "lag1": 1, "prefetch50": 1, "hybrid": 2}
CHARS_PER_TOKEN = 4.0
# Assumed per-call latency of a hosted chat model when no profile of it exists (s).
HOSTED_CALL_S = (0.5, 1.2, 3.0)


@dataclass
class MachineSpec:
    machine_type: str
    region: str
    spot: bool = False
    disk_gib: int = 200
    disk_type: str = "hyperdisk-balanced"
    startup_min: float = 20.0  # boot, driver check, Ollama install, model pulls
    teardown_min: float = 5.0  # copy results back, destroy
    max_lifetime_h: float = 4.0  # the machine deletes itself after this, whatever happens
    # Run duration on the machine relative to the profile's wall time (low, expected, high).
    duration_factor: tuple[float, float, float] = (0.25, 0.5, 1.0)


@dataclass
class Plan:
    run: str
    conditions: list[str]
    trials: dict[str, int]
    provider: str = "ollama"
    model: str = "gemma4:e4b"
    embed_provider: str = "ollama"
    embed_model: str = "nomic-embed-text"
    think: bool = False
    machine: MachineSpec | None = None
    date: str = field(default_factory=lambda: dt.date.today().isoformat())

    @property
    def max_tokens(self) -> int:
        return 2048 if self.think else 220

    @property
    def hosted(self) -> bool:
        return self.provider != "ollama" or self.embed_provider != "ollama"


# --------------------------------------------------------------- profiles -----


def profile_from_telemetry(run_dir: Path) -> dict:
    prices = PriceTable()
    spans = load_run(run_dir)
    conditions, index_tokens, meta = {}, 0, {}
    for condition, condition_spans in spans.items():
        records, overhead = trial_records(condition_spans, prices, set())
        conditions[condition] = records
        index_tokens = max(index_tokens, overhead["embed_tokens"])
        for s in condition_spans:
            a = s.get("attributes", {})
            if a.get("gen_ai.operation.name") == "chat":
                meta.setdefault("provider", {"gcp.vertex_ai": "vertex"}.get(a["gen_ai.provider.name"], a["gen_ai.provider.name"]))
                meta.setdefault("model", a.get("gen_ai.request.model", ""))
                meta.setdefault("think", bool(a.get("e2.request.think", False)))
    return {
        "source": f"telemetry of results/{run_dir.name}",
        "token_method": "measured",
        "provider": meta.get("provider", ""),
        "model": meta.get("model", ""),
        "think": meta.get("think", False),
        "index_embed_tokens": index_tokens,
        "conditions": conditions,
    }


def profile_from_bundles(run_dir: Path, counter=None, counter_name: str = "") -> dict:
    """Rebuild every call's prompt from a sealed run and count its tokens.

    Without ``counter``, input tokens are characters / 4. With ``counter`` (a
    function from a ``providers.ChatRequest`` to the provider's exact input-token
    count, e.g. Anthropic's free count_tokens endpoint), every distinct prompt is
    counted exactly, system prompt and tool definitions included. Output tokens
    stay characters / 4 of the stored replies: what a different model writes is
    not known before it runs.
    """
    from providers import ChatRequest
    from circumstances.pack import load_pack
    from subject import (
        NO_MEMORIES_SEARCH, REPLY_FORMAT, RULES, SEARCH_TOOL, STALE_MEMORIES_SEARCH,
        ambience, first_half,
    )

    cache: dict[str, int] = {}

    def count(request) -> int:
        key = json.dumps([request.system, request.messages, bool(request.tool)])
        if key not in cache:
            cache[key] = int(counter(request))
        return cache[key]

    pack = load_pack(ROOT / "pack")
    fixture = json.loads((ROOT / "fixtures" / "tessaly-v1.json").read_text())
    notes = fixture["memorome"]
    rules = RULES.format(**fixture["persona"])
    tool_chars = len(json.dumps(SEARCH_TOOL))
    msg_overhead = 4 * 4  # role markers per message, in characters (≈4 tokens each)

    def block(pages: list[str]) -> str:
        if not pages:
            return "MEMORIES\n(no memories are loaded for this turn)"
        return "MEMORIES\n" + "\n".join(f"- {notes[p]}" for p in pages)

    run_meta = json.loads(next((run_dir / "none").glob("*/run.json")).read_text()) if (run_dir / "none").exists() else {}
    conditions: dict[str, list[dict]] = {}
    for cdir in sorted(p for p in run_dir.iterdir() if p.is_dir() and p.name in MAX_CALLS):
        bundle = next(p for p in cdir.iterdir() if p.is_dir())
        records = []
        for path in sorted((bundle / "trials").glob("*.json")):
            trial = json.loads(path.read_text())
            case = pack.case(trial["case_id"])
            history = case.fixture.config["history"]
            user = case.actions[0].content
            said = [t["content"] for t in history]
            events = trial["trajectory"]["events"]
            met = {e["name"]: e["value"] for e in events if e["kind"] == "metric"}
            pages = next((e["components"]["recall"] for e in events if e["kind"] == "context_snapshot"), [])
            reply = next((e["content"] for e in reversed(events)
                          if e["kind"] == "message" and e["role"] == "assistant"), "")
            calls_made = int(met.get("path.llm_calls", 1))
            searches = [e["arguments"].get("query", "") for e in events if e["kind"] == "tool_call"]
            base = sum(len(t) for t in said) + len(user) + msg_overhead
            messages = [*history, {"role": "user", "content": user}]
            in_chars, out_chars, calls, counted = 0, 0, 0, 0
            name = cdir.name
            reply_out = len(json.dumps({"reply": reply, "abstained": False}))
            if name in ("tool", "hybrid"):
                offer = NO_MEMORIES_SEARCH if name == "tool" else block(pages) + "\n\n" + STALE_MEMORIES_SEARCH
                system = rules + "\n" + offer + "\n\n" + REPLY_FORMAT
                in_chars += len(system) + tool_chars + base
                if counter:
                    counted += count(ChatRequest(system, messages, SEARCH_TOOL, 0.7, 0, 220, False))
                calls += 1
                out_chars += (len(searches[0]) + 40) if searches else (reply_out if calls_made == 1 else 40)
            if not (name in ("tool", "hybrid") and calls_made == 1):
                system = rules + "\n" + block(pages) + "\n\n" + REPLY_FORMAT
                in_chars += len(system) + base
                if counter:
                    counted += count(ChatRequest(system, messages, None, 0.7, 0, 220, False))
                out_chars += reply_out
                calls += 1
            queries = {
                "none": [], "tool": searches,
                "blocking": [ambience([*said, user])],
                "lag1": [ambience(said)],
                "prefetch50": [ambience([*said, first_half(user)])],
                "hybrid": [ambience(said), *searches],
            }[name]
            started = dt.datetime.fromisoformat(trial["trajectory"]["started_at"])
            finished = dt.datetime.fromisoformat(trial["trajectory"]["finished_at"])
            records.append({
                "chat_calls": calls,
                "input_tokens": counted if counter else in_chars / CHARS_PER_TOKEN,
                "output_tokens": out_chars / CHARS_PER_TOKEN,
                "cached_input_tokens": 0,
                "embed_calls": len(queries),
                "embed_tokens": sum(len("search_query: " + q) for q in queries) / CHARS_PER_TOKEN,
                "wall_ms": (finished - started).total_seconds() * 1000,
            })
        conditions[cdir.name] = records
    lock = run_meta.get("lock", {}) if isinstance(run_meta, dict) else {}
    if counter:
        print(f"counted {len(cache)} distinct prompts with {counter_name}", flush=True)
    return {
        "source": (f"sealed bundles of results/{run_dir.name} (prompts rebuilt; input tokens counted by "
                   f"{counter_name}, output tokens = characters / 4)" if counter else
                   f"sealed bundles of results/{run_dir.name} (prompts rebuilt, tokens = characters / 4)"),
        "token_method": f"counted:{counter_name}" if counter else "chars/4",
        "provider": "ollama",
        "model": (lock.get("models") or {}).get("chat", ""),
        "think": False,
        "index_embed_tokens": sum(len("search_document: " + t) for t in notes.values()) / CHARS_PER_TOKEN,
        "conditions": conditions,
    }


def load_profile(name_or_path: str) -> dict:
    run_dir = Path(name_or_path) if "/" in name_or_path else ROOT / "results" / name_or_path
    if (run_dir / "telemetry").is_dir() and any((run_dir / "telemetry").glob("*.spans.jsonl")):
        return profile_from_telemetry(run_dir)
    return profile_from_bundles(run_dir)


# --------------------------------------------------------------- estimate -----


def _mean_sd(records: list[dict], key: str) -> tuple[float, float]:
    v = np.asarray([r[key] for r in records if r[key] == r[key]], dtype=float)
    if not len(v):
        return 0.0, 0.0
    return float(v.mean()), float(v.std(ddof=1)) if len(v) > 1 else 0.0


def _range(n: int, mean: float, sd: float) -> tuple[float, float, float]:
    exp = n * mean
    spread = max(0.10 * exp, 1.96 * sd * math.sqrt(n))
    return max(0.0, exp - spread), exp, exp + spread


def estimate(plan: Plan, profile: dict, prices: PriceTable | None = None) -> dict:
    prices = prices or PriceTable()
    on = dt.date.fromisoformat(plan.date)
    chat_price = prices.token_price(plan.provider, plan.model, on)
    embed_price = prices.token_price(plan.embed_provider, plan.embed_model, on)
    matched = (profile["token_method"] == "measured" and profile["provider"] == plan.provider
               and profile["model"] == plan.model and bool(profile.get("think")) == plan.think)
    notes = []
    if chat_price is None:
        notes.append(f"No price for {plan.provider}/{plan.model} on {plan.date}: chat cost unknown.")
    if embed_price is None:
        notes.append(f"No price for {plan.embed_provider}/{plan.embed_model} on {plan.date}: embedding cost unknown.")
    if not matched:
        notes.append(
            f"The profile ({profile['source']}; {profile['provider']}/{profile['model']}) is not a measured "
            f"profile of {plan.provider}/{plan.model}: the range is wide and its top assumes every trial makes "
            f"the most calls its condition allows and every call writes all {plan.max_tokens} output tokens."
        )
    counted_for_plan = profile["token_method"] == f"counted:{plan.provider}/{plan.model}"
    all_records = [r for recs in profile["conditions"].values() for r in recs]
    rows, totals = {}, {k: [0.0, 0.0, 0.0] for k in
                        ("chat_calls", "input_tokens", "output_tokens", "embed_tokens", "cost_usd", "duration_s")}
    for condition in plan.conditions:
        n = plan.trials[condition]
        records = profile["conditions"].get(condition)
        if not records:
            notes.append(f"{condition}: not in the profile; the average of the other conditions is used.")
            records = all_records
        calls_m, calls_sd = _mean_sd(records, "chat_calls")
        in_m, in_sd = _mean_sd(records, "input_tokens")
        out_m, out_sd = _mean_sd(records, "output_tokens")
        emb_m, emb_sd = _mean_sd(records, "embed_tokens")
        wall_m, wall_sd = _mean_sd(records, "wall_ms")
        if matched:
            calls = _range(n, calls_m, calls_sd)
            tin = _range(n, in_m, in_sd)
            tout = _range(n, out_m, out_sd)
            emb = _range(n, emb_m, emb_sd)
        else:
            calls = (n * 1.0, n * calls_m, n * MAX_CALLS[condition])
            per_call_in = in_m / calls_m if calls_m else 0.0
            if counted_for_plan:
                # Exact per prompt; the spread is only in how many calls the model makes.
                tin = (0.95 * per_call_in * calls[0], n * in_m, 1.05 * per_call_in * calls[2])
            else:
                tin = (0.75 * per_call_in * calls[0], n * in_m, 1.33 * per_call_in * calls[2])
            tout = (0.5 * n * out_m, n * out_m, calls[2] * plan.max_tokens)
            emb_per = emb_m / max(_mean_sd(records, "embed_calls")[0], 1e-9) if emb_m else 0.0
            emb = (0.75 * n * emb_m, n * emb_m, 1.33 * emb_per * n * RECALLS_MAX[condition])
        cost = []
        for i in range(3):
            c = 0.0
            if chat_price is not None:
                c += token_cost(chat_price, tin[i], tout[i])
            else:
                c = float("nan")
            if embed_price is not None:
                c += token_cost(embed_price, emb[i], 0.0)
            cost.append(c)
        # Duration.
        if matched and plan.machine is None:
            dur = tuple(x / 1000 for x in _range(n, wall_m, wall_sd))
        elif plan.provider != "ollama":
            local_s = 0.15 * RECALLS_MAX[condition]  # local retrieval, embedding included
            dur = tuple(calls[i] * HOSTED_CALL_S[i] + n * local_s for i in range(3))
        else:
            f = plan.machine.duration_factor if plan.machine else (0.8, 1.0, 1.5)
            dur = tuple(n * wall_m / 1000 * f[i] for i in range(3))
        rows[condition] = {
            "trials": n,
            "chat_calls": calls, "input_tokens": tin, "output_tokens": tout, "embed_tokens": emb,
            "cost_usd": tuple(cost), "duration_s": dur,
        }
        for k in totals:
            for i in range(3):
                totals[k][i] += rows[condition][k][i]
    # Indexing the memorome: once per condition.
    index = profile.get("index_embed_tokens", 0) * len(plan.conditions)
    if embed_price is not None:
        for i in range(3):
            totals["cost_usd"][i] += token_cost(embed_price, index, 0.0)
    totals["embed_tokens"] = [x + index for x in totals["embed_tokens"]]
    if plan.provider != "ollama" and not matched:
        notes.append(f"Duration assumes {HOSTED_CALL_S[0]}–{HOSTED_CALL_S[2]} s per hosted model call "
                     f"(expected {HOSTED_CALL_S[1]} s); no measured profile of this provider yet.")
    machine = None
    if plan.machine is not None:
        m = plan.machine
        mprice = prices.machine_price(m.machine_type, m.region)
        disk = prices.disk_price_per_gib_hour(m.disk_type, m.region) or 0.0
        if mprice is None:
            notes.append(f"No price for machine {m.machine_type} in {m.region}.")
        else:
            overhead_h = (m.startup_min + m.teardown_min) / 60
            hours = [overhead_h + totals["duration_s"][i] / 3600 for i in range(3)]
            cost = [machine_cost(mprice, h, spot=m.spot, disk_gib=m.disk_gib, disk_per_gib_hour=disk) for h in hours]
            worst = machine_cost(mprice, m.max_lifetime_h, spot=m.spot, disk_gib=m.disk_gib, disk_per_gib_hour=disk)
            machine = {
                "machine_type": m.machine_type, "region": m.region, "spot": m.spot,
                "hourly_usd": mprice.spot_per_hour if m.spot else mprice.on_demand_per_hour,
                "disk": f"{m.disk_gib} GiB {m.disk_type}",
                "startup_min": m.startup_min, "teardown_min": m.teardown_min,
                "hours": tuple(hours), "cost_usd": tuple(cost),
                "max_lifetime_h": m.max_lifetime_h, "worst_case_usd": worst,
                "price_source": mprice.source, "price_read_on": mprice.read_on,
            }
            if any(h > m.max_lifetime_h for h in hours):
                notes.append(f"The upper duration ({hours[2]:.1f} h) exceeds the machine's maximum lifetime "
                             f"({m.max_lifetime_h} h): the run would be cut off.")
            for i in range(3):
                totals["cost_usd"][i] += cost[i]
    spend = totals["cost_usd"][2]
    return {
        "plan": {**asdict(plan), "machine": asdict(plan.machine) if plan.machine else None},
        "profile": {k: profile[k] for k in ("source", "token_method", "provider", "model")},
        "matched_profile": matched,
        "prices": {
            "chat": asdict(chat_price) if chat_price else None,
            "embed": asdict(embed_price) if embed_price else None,
        },
        "conditions": rows,
        "totals": {k: tuple(v) for k, v in totals.items()},
        "machine": machine,
        "spends_money": bool(plan.hosted or plan.machine is not None) and (spend != spend or spend > 0),
        "notes": notes,
    }


def _r(t: tuple, fmt: str = "{:,.0f}") -> str:
    lo, exp, hi = t
    if exp != exp:
        return "unknown"
    return f"{fmt.format(exp)} [{fmt.format(lo)}–{fmt.format(hi)}]"


def _usd(t: tuple) -> str:
    return _r(t, "${:,.4f}") if t[2] < 1 else _r(t, "${:,.2f}")


def _dur(t: tuple) -> str:
    def f(s: float) -> str:
        return f"{s / 3600:.1f} h" if s >= 5400 else f"{s / 60:.0f} min" if s >= 120 else f"{s:.0f} s"
    return f"{f(t[1])} [{f(t[0])}–{f(t[2])}]"


def markdown(est: dict) -> str:
    p = est["plan"]
    lines = [f"# Estimate: `{p['run']}`", "",
             f"- Chat model: {p['provider']}/{p['model']}{' (reasoning on)' if p['think'] else ''}; "
             f"embeddings: {p['embed_provider']}/{p['embed_model']}",
             f"- Trials: {sum(p['trials'].values())} in {len(p['conditions'])} condition(s)",
             f"- Profile: {est['profile']['source']}",
             f"- Prices on {p['date']}: chat "
             + (f"${est['prices']['chat']['input_per_mtok']}/${est['prices']['chat']['output_per_mtok']} per M in/out "
                f"({est['prices']['chat']['source']}, read {est['prices']['chat']['read_on']})" if est["prices"]["chat"] else "unknown"),
             "", "Expected [low–high]. The high end of a wide range is a ceiling, not a likely value.", "",
             "| condition | trials | model calls | tokens in | tokens out | embed tokens | model spend | duration |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for c, r in est["conditions"].items():
        lines.append(f"| {c} | {r['trials']} | {_r(r['chat_calls'])} | {_r(r['input_tokens'])} | {_r(r['output_tokens'])} "
                     f"| {_r(r['embed_tokens'])} | {_usd(r['cost_usd'])} | {_dur(r['duration_s'])} |")
    t = est["totals"]
    lines.append(f"| **total** | {sum(p['trials'].values())} | {_r(t['chat_calls'])} | {_r(t['input_tokens'])} "
                 f"| {_r(t['output_tokens'])} | {_r(t['embed_tokens'])} | {_usd(t['cost_usd'])} | {_dur(t['duration_s'])} |")
    m = est["machine"]
    if m:
        lines += ["", f"Machine: {m['machine_type']} in {m['region']} ({'spot' if m['spot'] else 'on-demand'}, "
                  f"${m['hourly_usd']:.2f}/h, {m['disk']}), start-up {m['startup_min']:.0f} min + run + teardown "
                  f"{m['teardown_min']:.0f} min = {_r(m['hours'], '{:.1f}')} h → {_usd(m['cost_usd'])} "
                  f"(included in the total). Hard maximum lifetime {m['max_lifetime_h']} h: worst case "
                  f"${m['worst_case_usd']:.2f}. Price: {m['price_source']}, read {m['price_read_on']}."]
    lines += ["", f"**Total spend: {_usd(t['cost_usd'])}**" if est["spends_money"] else "**No spend** (local models, local machine)."]
    if est["notes"]:
        lines += ["", "Notes:", *[f"- {n}" for n in est["notes"]]]
    return "\n".join(lines) + "\n"


def write_estimate(est: dict, run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "estimate.json").write_text(json.dumps(est, indent=2, default=list) + "\n")
    (run_dir / "estimate.md").write_text(markdown(est))


def confirm(est: dict, *, yes: bool, estimate_only: bool) -> bool:
    """Print the estimate; return True if the run should start."""
    print(markdown(est), flush=True)
    if estimate_only:
        print("--estimate-only: stopping before the run.")
        return False
    if not est["spends_money"] or yes:
        return True
    import sys

    if not sys.stdin.isatty():
        print("This run spends money and there is no terminal to confirm on. Re-run with --yes to proceed.")
        return False
    answer = input(f"Start this run? Expected spend {_usd(est['totals']['cost_usd'])}. [y/N] ").strip().lower()
    return answer in ("y", "yes")


# ---------------------------------------------------------- after the run -----


def compare(run_dir: Path) -> str:
    """Write actual.json and estimate_vs_actual.md beside the estimate."""
    est = json.loads((run_dir / "estimate.json").read_text())
    summary = summarise_run(run_dir)
    actual = {
        c: {
            "trials": s["trials"],
            "chat_calls": s["totals"]["chat_calls"],
            "input_tokens": s["totals"]["input_tokens"],
            "output_tokens": s["totals"]["output_tokens"],
            "embed_tokens": s["totals"]["embed_tokens"] - s["overhead_index"]["embed_tokens"],
            "cost_usd": s["totals"]["cost_usd"],
            "duration_s": s["totals"]["wall_s"],
        }
        for c, s in summary["conditions"].items()
    }
    if est.get("machine") and (run_dir / "machine.json").exists():
        actual["machine"] = json.loads((run_dir / "machine.json").read_text())
    (run_dir / "actual.json").write_text(json.dumps(actual, indent=2) + "\n")
    lines = [f"# Estimate and actual: `{run_dir.name}`", "",
             "Estimate as expected [low–high]; actual from the run's telemetry. "
             "⚠ marks an actual outside the estimated range.", "",
             "| condition | quantity | estimate | actual |", "|---|---|---:|---:|"]
    for c, row in est["conditions"].items():
        a = actual.get(c)
        for k in ("trials", "chat_calls", "input_tokens", "output_tokens", "embed_tokens", "cost_usd", "duration_s"):
            e = row[k]
            if a is None:
                av = "not run"
            else:
                v = a[k]
                av = (f"${v:.4f}" if k == "cost_usd" else _dur((v, v, v)).split(" [")[0] if k == "duration_s"
                      else f"{v:,.0f}")
                if isinstance(e, list) and not (e[0] <= v <= e[2] or e[1] != e[1]):
                    av = "⚠ " + av
            ev = (str(e) if not isinstance(e, list) else _usd(tuple(e)) if k == "cost_usd"
                  else _dur(tuple(e)) if k == "duration_s" else _r(tuple(e)))
            lines.append(f"| {c} | {k} | {ev} | {av} |")
    if "machine" in actual:
        m = actual["machine"]
        lines += ["", f"Machine: estimated {_usd(tuple(est['machine']['cost_usd']))} for "
                  f"{_r(tuple(est['machine']['hours']), '{:.2f}')} h; actual {m.get('hours', float('nan')):.2f} h → "
                  f"${m.get('cost_usd', float('nan')):.2f} (from the job's own start and delete times)."]
    text = "\n".join(lines) + "\n"
    (run_dir / "estimate_vs_actual.md").write_text(text)
    return text
