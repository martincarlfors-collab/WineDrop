"""Historik & trender per marknad.

Efter varje körning:
  * sparar en veckosnapshot: site/api/<market>/history/<YYYY-WW>.json
  * beräknar om site/api/<market>/trends.json genom att läsa alla snapshots:
      - snittbetyg och antal per vecka
      - topp-producenter (snittbetyg, antal)

Snapshotfilerna pushas med i git så historiken byggs upp vecka för vecka.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from collections import defaultdict

from . import config
from .schema import Market, Wine, Summary


def _week_id(d: dt.date) -> str:
    iso = d.isocalendar()
    return f"{iso.year}-{iso.week:02d}"


def _read(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def record(market: Market, pairs: list[tuple[Wine, Summary]]) -> None:
    hist_dir = os.path.join(config.API_DIR, market.code, "history")
    os.makedirs(hist_dir, exist_ok=True)
    wk = _week_id(dt.date.today())

    snapshot = {
        "week": wk,
        "market": market.code,
        "wines": [
            {"name": w.name, "producer": w.producer, "score": s.score,
             "price": w.price, "origin_country": w.origin_country,
             "wine_type": w.wine_type}
            for w, s in pairs
        ],
    }
    with open(os.path.join(hist_dir, f"{wk}.json"), "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=2)

    _rebuild_trends(market.code, hist_dir)


def _rebuild_trends(code: str, hist_dir: str) -> None:
    weeks = []
    prod_scores: dict[str, list[int]] = defaultdict(list)
    prod_count: dict[str, int] = defaultdict(int)

    for fn in sorted(os.listdir(hist_dir)):
        if not fn.endswith(".json"):
            continue
        snap = _read(os.path.join(hist_dir, fn), None)
        if not snap:
            continue
        wines = snap.get("wines", [])
        scores = [w["score"] for w in wines if isinstance(w.get("score"), int)]
        weeks.append({
            "week": snap.get("week", fn[:-5]),
            "count": len(wines),
            "avgScore": round(sum(scores) / len(scores), 1) if scores else None,
        })
        for w in wines:
            p = (w.get("producer") or "").strip()
            if not p:
                continue
            prod_count[p] += 1
            if isinstance(w.get("score"), int):
                prod_scores[p].append(w["score"])

    producers = []
    for p, cnt in prod_count.items():
        sc = prod_scores.get(p, [])
        producers.append({
            "name": p, "count": cnt,
            "avgScore": round(sum(sc) / len(sc), 1) if sc else None,
        })
    # sortera: flest släpp, sedan högst snittbetyg
    producers.sort(key=lambda x: (x["count"], x["avgScore"] or 0), reverse=True)

    trends = {"market": code, "weeks": weeks[-26:], "producers": producers[:25]}
    with open(os.path.join(config.API_DIR, code, "trends.json"), "w", encoding="utf-8") as fh:
        json.dump(trends, fh, ensure_ascii=False, indent=2)
