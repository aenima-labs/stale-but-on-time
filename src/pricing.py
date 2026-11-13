"""Price table lookups and cost arithmetic (prices in ``pricing/prices.yaml``)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PRICES = ROOT / "pricing" / "prices.yaml"


@dataclass(frozen=True)
class TokenPrice:
    provider: str
    model: str
    input_per_mtok: float
    cached_input_per_mtok: float
    output_per_mtok: float
    source: str
    read_on: str


@dataclass(frozen=True)
class MachinePrice:
    machine_type: str
    region: str
    on_demand_per_hour: float
    spot_per_hour: float
    source: str
    read_on: str


def _date(value: object) -> dt.date | None:
    if value is None:
        return None
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value))


def _valid(entry: dict, on: dt.date) -> bool:
    start, end = _date(entry.get("valid_from")), _date(entry.get("valid_until"))
    return (start is None or start <= on) and (end is None or on <= end)


class PriceTable:
    def __init__(self, path: Path = PRICES) -> None:
        self.data = yaml.safe_load(path.read_text())

    def token_price(self, provider: str, model: str, on: dt.date | None = None) -> TokenPrice | None:
        """The entry for (provider, model) valid on ``on``; ``model: "*"`` matches any model.

        A model id with a ``google/`` prefix or a dated suffix the provider
        returns (``gpt-5.6-luna-2026-07-30``) matches its base entry.
        """
        on = on or dt.date.today()
        candidates = [e for e in self.data["models"] if e["provider"] == provider and _valid(e, on)]
        bare = model.removeprefix("google/")
        for entry in candidates:
            if entry["model"] == bare:
                return _token(entry)
        for entry in sorted(candidates, key=lambda e: -len(e["model"])):
            if entry["model"] != "*" and bare.startswith(entry["model"] + "-"):
                return _token(entry)
        for entry in candidates:
            if entry["model"] == "*":
                return _token(entry)
        return None

    def machine_price(self, machine_type: str, region: str) -> MachinePrice | None:
        for e in self.data.get("machines", []):
            if e["machine_type"] == machine_type and e["region"] == region:
                return MachinePrice(
                    e["machine_type"], e["region"], float(e["on_demand_per_hour"]),
                    float(e["spot_per_hour"]), e["source"], str(e["read_on"]),
                )
        return None

    def disk_price_per_gib_hour(self, disk_type: str, region: str) -> float | None:
        for e in self.data.get("disks", []):
            if e["disk_type"] == disk_type and e["region"] == region:
                return float(e["per_gib_hour"])
        return None


def _token(e: dict) -> TokenPrice:
    return TokenPrice(
        e["provider"], e["model"], float(e["input_per_mtok"]), float(e["cached_input_per_mtok"]),
        float(e["output_per_mtok"]), e["source"], str(e["read_on"]),
    )


def token_cost(price: TokenPrice, input_tokens: float, output_tokens: float,
               cached_input_tokens: float = 0.0) -> float:
    """USD for one call or a sum of calls.

    ``input_tokens`` includes the cached ones (the OpenTelemetry GenAI
    convention, which ``providers.py`` follows for every provider); they are
    charged at the cached price and the rest at the input price.
    """
    cached = min(max(cached_input_tokens, 0.0), input_tokens)
    return (
        (input_tokens - cached) * price.input_per_mtok
        + cached * price.cached_input_per_mtok
        + output_tokens * price.output_per_mtok
    ) / 1e6


def machine_cost(price: MachinePrice, hours: float, *, spot: bool = False,
                 disk_gib: float = 0.0, disk_per_gib_hour: float = 0.0) -> float:
    hourly = price.spot_per_hour if spot else price.on_demand_per_hour
    return hours * (hourly + disk_gib * disk_per_gib_hour)
