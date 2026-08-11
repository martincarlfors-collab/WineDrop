"""🇳🇴 Norge — Vinmonopolet öppna API (kräver prenumerationsnyckel).

Registrera dig på https://api.vinmonopolet.no och sätt VINMONOPOLET_KEY.
Utan nyckel returnerar connectorn [] (appen fungerar ändå).
"""
from __future__ import annotations

import requests

from .. import config
from ..schema import Market, Wine
from .base import MarketConnector


class NorwayConnector(MarketConnector):
    market = Market("no", "Norway", "🇳🇴", "NOK", "no", "Vinmonopolet")
    review_lang = "no"

    def fetch_new_releases(self, days_back: int) -> list[Wine]:
        if not config.VINMONOPOLET_KEY:
            print("[no] VINMONOPOLET_KEY saknas — hoppar över (registrera på api.vinmonopolet.no)")
            return []

        wines: list[Wine] = []
        try:
            # API:t paginerar; vi hämtar nya viner (isGoodFor/nyhet-flagga varierar,
            # här filtrerar vi på lanseringsdatum efter hämtning).
            resp = requests.get(
                config.VINMONOPOLET_API,
                headers={
                    "Ocp-Apim-Subscription-Key": config.VINMONOPOLET_KEY,
                    "User-Agent": config.USER_AGENT,
                },
                params={"maxResults": 200},
                timeout=config.REQUEST_TIMEOUT_SEC,
            )
            resp.raise_for_status()
            items = resp.json()
        except Exception as exc:  # noqa: BLE001
            print(f"[no] kunde inte hämta data: {exc}")
            return []

        if isinstance(items, dict):
            items = items.get("products") or items.get("results") or []

        for it in items:
            basic = it.get("basic", it) if isinstance(it, dict) else {}
            if "vin" not in str(basic.get("mainCategory", "")).lower() \
               and "wine" not in str(basic.get("mainCategory", "")).lower():
                continue
            launch = str(it.get("prices", [{}])[0].get("validFrom", ""))[:10] \
                if it.get("prices") else ""
            if launch and not self._recent(launch, days_back):
                continue

            pid = str(basic.get("productId") or it.get("code") or "")
            wines.append(Wine(
                id=f"no-{pid}",
                market="no",
                name=str(basic.get("productShortName") or basic.get("productLongName") or ""),
                producer=str(it.get("logistics", {}).get("manufacturerName", "")),
                wine_type=str(basic.get("subCategory", "")),
                vintage=str(basic.get("vintage") or "").strip(),
                origin_country=str(it.get("origins", {}).get("origin", {}).get("country", "")),
                price=_f(basic.get("price")),
                currency="NOK",
                launch_date=launch,
                url=f"https://www.vinmonopolet.no/p/{pid}" if pid else "",
                image=str(it.get("images", [{}])[0].get("url", "")) if it.get("images") else "",
            ))
        wines.sort(key=lambda w: w.launch_date, reverse=True)
        return wines


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
