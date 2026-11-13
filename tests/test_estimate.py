import pytest

import estimate as e
from pricing import PriceTable


def profile(provider="ollama", model="gemma4:e4b", method="measured", n=20):
    rec = {"chat_calls": 1, "input_tokens": 400.0, "output_tokens": 30.0, "cached_input_tokens": 0,
           "embed_calls": 1, "embed_tokens": 50.0, "wall_ms": 1000.0}
    tool = {**rec, "chat_calls": 2, "input_tokens": 800.0, "output_tokens": 50.0}
    return {"source": "test", "token_method": method, "provider": provider, "model": model,
            "think": False, "index_embed_tokens": 2000,
            "conditions": {"blocking": [dict(rec) for _ in range(n)], "tool": [dict(tool) for _ in range(n)]}}


def plan(**kw):
    base = dict(run="r", conditions=["blocking", "tool"], trials={"blocking": 200, "tool": 200},
                date="2026-11-13")
    return e.Plan(**{**base, **kw})


def test_local_run_spends_nothing_and_does_not_block(capsys):
    est = e.estimate(plan(), profile())
    assert not est["spends_money"]
    assert est["totals"]["cost_usd"] == (0.0, 0.0, 0.0)
    assert est["totals"]["chat_calls"][1] == pytest.approx(200 + 400)
    assert e.confirm(est, yes=False, estimate_only=False) is True  # no prompt
    assert e.confirm(est, yes=False, estimate_only=True) is False


def test_hosted_estimate_arithmetic_and_ceiling():
    est = e.estimate(plan(provider="openai", model="gpt-5.6-luna", embed_provider="openai",
                          embed_model="text-embedding-3-small"), profile())
    assert est["spends_money"] and not est["matched_profile"]
    b = est["conditions"]["blocking"]
    # expected = profile scaled to 200 trials, priced at luna + text-embedding-3-small
    exp = (200 * 400 * 0.20 + 200 * 30 * 1.20 + 200 * 50 * 0.02) / 1e6
    assert b["cost_usd"][1] == pytest.approx(exp)
    # ceiling: every call writes its whole output budget
    assert b["output_tokens"][2] == 200 * 1 * 220
    assert est["conditions"]["tool"]["output_tokens"][2] == 200 * 2 * 220
    low, mid, high = est["totals"]["cost_usd"]
    assert low < mid < high
    # the per-run index embedding (2,000 tokens per condition) is in the total
    index = 2 * 2000 * 0.02 / 1e6
    assert mid == pytest.approx(b["cost_usd"][1] + est["conditions"]["tool"]["cost_usd"][1] + index)


def test_matched_profile_gives_narrow_range():
    est = e.estimate(plan(provider="openai", model="gpt-5.6-luna"), profile("openai", "gpt-5.6-luna"))
    assert est["matched_profile"]
    lo, mid, hi = est["conditions"]["blocking"]["input_tokens"]
    assert mid == pytest.approx(80_000) and lo == pytest.approx(72_000) and hi == pytest.approx(88_000)


def test_machine_cost_and_worst_case():
    m = e.MachineSpec("g4-standard-48", "europe-west1", startup_min=30, teardown_min=6, max_lifetime_h=3,
                      disk_gib=0, duration_factor=(1.0, 1.0, 1.0))
    est = e.estimate(plan(machine=m), profile())
    price = PriceTable().machine_price("g4-standard-48", "europe-west1").on_demand_per_hour
    run_h = 400 * 1.0 / 3600
    assert est["machine"]["hours"][1] == pytest.approx(0.6 + run_h)
    assert est["machine"]["cost_usd"][1] == pytest.approx((0.6 + run_h) * price)
    assert est["machine"]["worst_case_usd"] == pytest.approx(3 * price)
    assert est["spends_money"]


def test_confirm_refuses_without_terminal(monkeypatch, capsys):
    est = e.estimate(plan(provider="openai", model="gpt-5.6-luna"), profile())
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert e.confirm(est, yes=False, estimate_only=False) is False
    assert "--yes" in capsys.readouterr().out
    assert e.confirm(est, yes=True, estimate_only=False) is True


def test_bundle_profile_covers_stored_run():
    p = e.profile_from_bundles(e.ROOT / "results" / "e2")
    assert set(p["conditions"]) == set(e.MAX_CALLS)
    assert all(len(v) == 200 for v in p["conditions"].values())
    assert all(1 <= r["chat_calls"] <= e.MAX_CALLS[c] for c, v in p["conditions"].items() for r in v)


def test_seeds_for_fewer_trials_match_the_full_run():
    from pathlib import Path

    from circumstances.pack import load_pack

    import e2_run

    pack = load_pack(e2_run.ROOT / "pack")
    full = [e2_run.BASE_SEED + n for n in range(sum(c.trials for c in pack.cases.values()))]
    ids = list(pack.cases)
    one = e2_run.seeds_for(pack, None, 1)
    assert len(one) == len(ids)
    assert one == [full[sum(pack.case(c).trials for c in ids[:i])] for i in range(len(ids))]
    assert e2_run.seeds_for(pack, [ids[3]], 2) == full[15:17]
    del Path
