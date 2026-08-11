"""🇸🇪 Sverige — Systembolaget via community-datamirror."""
from __future__ import annotations

import requests

from .. import config
from ..schema import Market, Wine
from .base import MarketConnector


class SwedenConnector(MarketConnector):
    market = Market("se", "Sweden", "🇸🇪", "SEK", "sv", "Systembolaget")
    review_lang = "sv"

    def fetch_new_releases(self, days_back: int) -> list[Wine]:
        try:
            resp = requests.get(
                config.SYSTEMBOLAGET_MIRROR,
                headers={"User-Agent": config.USER_AGENT},
                timeout=config.REQUEST_TIMEOUT_SEC,
            )
            resp.raise_for_status()
            products = resp.json()
        except Exception as exc:  # noqa: BLE001
            print(f"[se] kunde inte hämta data: {exc}")
            return []

        if isinstance(products, dict):
            products = products.get("products") or products.get("data") or []

        assortment_filter = (config.SE_ASSORTMENT or "").lower()
        wines: list[Wine] = []
        for p in products:
            if "vin" not in str(p.get("categoryLevel1", "")).lower():
                continue
            # Sortimentsfilter är valfritt. Tomt = ALLA viner (både fasta
            # sortimentet och tillfälliga sortimentet) som släpps under veckan.
            if assortment_filter and \
               assortment_filter not in str(p.get("assortmentText", "")).lower():
                continue
            launch = str(p.get("productLaunchDate", ""))[:10]
            if not self._recent(launch, days_back):
                continue

            pnr = str(p.get("productNumber") or p.get("productId") or "")
            name = " ".join(
                s for s in (p.get("productNameBold"), p.get("productNameThin")) if s
            ).strip()
            wines.append(Wine(
                id=f"se-{pnr}",
                market="se",
                name=name,
                producer=str(p.get("producerName", "")).strip(),
                wine_type=str(p.get("categoryLevel2", "")).strip(),
                vintage=str(p.get("vintage") or "").strip(),
                origin_country=str(p.get("country", "")).strip(),
                price=_f(p.get("price")),
                currency="SEK",
                launch_date=launch,
                url=f"https://www.systembolaget.se/produkt/vin/{pnr}/" if pnr else "",
                image=_first_image(p),
                assortment=str(p.get("assortmentText", "")).strip(),
                volume=_f(p.get("volume")),
                is_news=bool(p.get("isNews")),
            ))
        wines.sort(key=lambda w: w.launch_date, reverse=True)
        return wines


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _first_image(p: dict) -> str:
    imgs = p.get("images") or []
    if imgs and isinstance(imgs, list):
        return str(imgs[0].get("imageUrl", ""))
    return ""
