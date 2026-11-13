import datetime as dt

import pytest

from pricing import MachinePrice, PriceTable, TokenPrice, machine_cost, token_cost

P = TokenPrice("openai", "m", input_per_mtok=0.20, cached_input_per_mtok=0.02,
               output_per_mtok=1.20, source="s", read_on="2026-11-13")


def test_token_cost_charges_cached_input_at_cached_price():
    # 1M input of which 400k cached, 100k output
    assert token_cost(P, 1_000_000, 100_000, 400_000) == pytest.approx(
        (600_000 * 0.20 + 400_000 * 0.02 + 100_000 * 1.20) / 1e6
    )


def test_token_cost_caps_cached_at_input():
    assert token_cost(P, 1000, 0, 5000) == pytest.approx(1000 * 0.02 / 1e6)


def test_machine_cost_includes_disk_and_spot():
    m = MachinePrice("g4", "eu", on_demand_per_hour=5.0, spot_per_hour=2.0, source="s", read_on="d")
    assert machine_cost(m, 2.0) == pytest.approx(10.0)
    assert machine_cost(m, 2.0, spot=True, disk_gib=100, disk_per_gib_hour=0.001) == pytest.approx(2 * (2.0 + 0.1))


def test_table_lookup_by_date_and_wildcard():
    t = PriceTable()
    before = t.token_price("vertex", "gemini-3.8-flash", dt.date(2026, 12, 31))
    after = t.token_price("vertex", "google/gemini-3.8-flash", dt.date(2027, 1, 1))
    assert before.input_per_mtok == 0.75 and after.input_per_mtok == 1.50
    assert t.token_price("ollama", "gemma4:e4b").output_per_mtok == 0
    # dated response ids map to their base entry
    assert t.token_price("openai", "gpt-5.6-luna-2026-07-30", dt.date(2026, 11, 13)).model == "gpt-5.6-luna"
    assert t.token_price("openai", "unknown-model") is None


def test_every_entry_has_source_and_date():
    data = PriceTable().data
    for section in ("models", "machines", "disks", "cloud_run", "storage"):
        for e in data[section]:
            assert e["source"] and e["read_on"], e


def test_cloud_run_job_price_per_hour():
    m = PriceTable().cloud_run_price("europe-west1", "nvidia-l4", 4, 24)
    assert m.on_demand_per_hour == pytest.approx(3600 * (0.0001867 + 4 * 0.000018 + 24 * 0.000002))
    assert PriceTable().cloud_run_price("europe-west1", "nvidia-h100", 4, 24) is None
