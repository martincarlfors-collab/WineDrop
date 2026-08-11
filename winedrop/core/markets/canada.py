"""🇨🇦 Kanada — LCBO (Ontario) via det nyckelfria lcbostats.com-API:t.

lcbostats.com speglar LCBO:s produktdata som paginerad JSON. Vi hämtar viner,
sorterar på när de lades till/nyast och tar de senaste.

API:t är community-drivet; schemat kan ändras, så vi är defensiva och faller
tillbaka till [] vid fel (appen fungerar ändå).
"""
from __future__ import annotations

import requests

from .. import config
from ..schema import Market, Wine
from .base import MarketConnector

API_URL = "https://lcbostats.com/api/alcohol"


class CanadaConnector(MarketConnector):
    market = Market("ca", "Canada", "🇨🇦", "CAD", "en", "LCBO")
    review_lang = "en"

    def fetch_new_releases(self, days_back: int) -> list[Wine]:
        items: list[dict] = []
        try:
            # Sortera nyast först om API:t stödjer det; annars hämta sida 1.
            r = requests.get(
                API_URL,
                params={"category": "Wine", "sort": "-created_at", "per_page": 100},
                headers={"User-Agent": config.USER_AGENT,
                         "Accept": "application/json"},
                timeout=config.REQUEST_TIMEOUT_SEC,
            )
            r.raise_for_status()
            body = r.json()
        except Exception as exc:  # noqa: BLE001
            print(f"[ca] kunde inte hämta LCBO-data: {exc}")
            return []

        # Paginerat svar: data kan ligga under 'data' eller vara en ren lista
        items = body.get("data", body) if isinstance(body, dict) else body
        if not isinstance(items, list):
            return []

        wines: list[Wine] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            cat = str(it.get("category") or it.get("category_name") or "").lower()
            if "wine" not in cat and it.get("category") is not None:
                continue

            pid = str(it.get("id") or it.get("permanent_id") or it.get("lcbo_id") or "")
            name = str(it.get("title") or it.get("name") or "")
            if not name:
                continue
            price = it.get("price") or it.get("price_in_cents")
            if isinstance(price, (int, float)) and price > 1000:
                price = price / 100.0  # cent -> dollar

            wines.append(Wine(
                id=f"ca-{pid}",
                market="ca",
                name=name,
                producer=str(it.get("producer_name") or it.get("producer") or ""),
                wine_type=str(it.get("varietal") or it.get("secondary_category") or ""),
                vintage=str(it.get("vintage") or "").strip() if it.get("vintage") else "",
                origin_country=str(it.get("origin") or it.get("country") or ""),
                price=_f(price),
                currency="CAD",
                launch_date=str(it.get("created_at") or "")[:10],
                url=str(it.get("url") or (f"https://www.lcbo.com/en/{pid}" if pid else "")),
                image=str(it.get("image_url") or it.get("image_thumb_url") or ""),
            ))

        # Om API:t inte sorterade: sortera på launch_date desc
        wines.sort(key=lambda w: w.launch_date, reverse=True)
        return wines[:100]


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
