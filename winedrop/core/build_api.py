"""Skriver den statiska JSON-API:n som appen läser."""
from __future__ import annotations
import datetime as dt
import json
import os

from . import config
from .schema import Market, Wine, Summary, merge


def _write(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def write_market(market: Market, wines_with_summaries: list[tuple[Wine, Summary]]) -> None:
    today = dt.date.today()
    payload = {
        "market": market.code,
        "week": today.isocalendar().week,
        "updated": today.isoformat(),
        "wines": [merge(w, s) for w, s in wines_with_summaries],
    }
    _write(os.path.join(config.API_DIR, market.code, "latest.json"), payload)


def write_index(markets: list[Market], counts: dict[str, int]) -> None:
    today = dt.date.today().isoformat()
    data = []
    for m in markets:
        d = m.to_dict()
        d["updated"] = today
        d["count"] = counts.get(m.code, 0)
        data.append(d)
    _write(os.path.join(config.API_DIR, "markets.json"), data)
