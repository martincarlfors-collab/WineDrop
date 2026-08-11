"""🇸🇪 Sverige — släpplista från Vintelegrafen (Vinkällaren Grappe).

Vi använder deras publika recensionssidor ENBART för att veta VILKA viner som
släpps i Systembolagets tillfälliga sortiment (namn, producent, årgång, ursprung,
Systembolaget-nummer, släppdatum, pris). Betyg och recensioner tar WineDrop fram
själv via sin egen pipeline — vi återanvänder inte deras poäng eller provningsnoter.

Källa: https://vintelegrafen.se/recensioner  (server-renderad, hämtas utan webbläsare)
Startdatum styrs av SE_SINCE (default 2026-05-01).
"""
from __future__ import annotations
import datetime as dt
import os
import re

import requests
from bs4 import BeautifulSoup

from .. import config
from ..schema import Market, Wine
from .base import MarketConnector

INDEX_URL = "https://vintelegrafen.se/recensioner"
BASE = "https://vintelegrafen.se"
SE_SINCE = os.environ.get("SE_SINCE", "2026-06-01")
# Länk till Systembolaget via produktnummer (sök landar alltid rätt).
SB_URL = "https://www.systembolaget.se/sortiment/?q={}"

_SECTIONS = {
    "mousserande vin": "Mousserande", "vitt torrt vin": "Vitt", "vitt vin": "Vitt",
    "rött vin": "Rött", "rosévin": "Rosé", "rosé vin": "Rosé", "rosévin": "Rosé",
    "sött vin": "Sött", "starkvin": "Starkvin", "spritförstärkt vin": "Starkvin",
}


def _date(s) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _get(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": config.USER_AGENT},
                     timeout=config.REQUEST_TIMEOUT_SEC)
    r.raise_for_status()
    return r.text


def _parse_lines(lines: list[str]) -> list[dict]:
    """Parsa en släppsidas textrader till vin-poster (fakta, inga betyg)."""
    lines = [l.strip() for l in lines if l and l.strip()]
    out: list[dict] = []
    section = ""
    i = 0
    while i < len(lines):
        low = lines[i].lower()
        if low in _SECTIONS:
            section = _SECTIONS[low]
            i += 1
            continue
        m = re.match(r"^\((\d{4,7})\)$", lines[i])   # (produktnummer)
        if not m:
            i += 1
            continue
        nr = m.group(1)
        name_line = lines[i - 1] if i > 0 else ""
        producer = lines[i + 1] if i + 1 < len(lines) else ""
        origin = lines[i + 2] if i + 2 < len(lines) else ""

        vintage, name = "", name_line
        mv = re.match(r"^(\d{4}|NV)\s+(.*)$", name_line)
        if mv:
            vintage = "" if mv.group(1) == "NV" else mv.group(1)
            name = mv.group(2).strip()
        country = origin.split(",")[-1].strip() if origin else ""

        date, price = "", None
        for j in range(i, min(i + 14, len(lines))):
            dm = re.match(r"Lanseringsdatum:\s*(\d{4}-\d{2}-\d{2})", lines[j])
            if dm:
                date = dm.group(1)
            pm = re.match(r"Pris:\s*(\d+)", lines[j])
            if pm:
                price = float(pm.group(1))
            if date and price is not None:
                break

        if name and date:
            out.append({"nr": nr, "name": name, "vintage": vintage,
                        "producer": producer, "country": country,
                        "type": section, "date": date, "price": price})
        i += 3
    return out


def _parse_release(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    art = soup.find("article") or soup.body or soup
    return _parse_lines(art.get_text("\n").split("\n"))


def _to_wine(w: dict) -> Wine:
    return Wine(
        id=f"se-{w['nr']}", market="se", name=w["name"], producer=w["producer"],
        wine_type=w["type"], vintage=w["vintage"], origin_country=w["country"],
        price=w["price"], currency="SEK", launch_date=w["date"],
        url=SB_URL.format(w["nr"]),
        assortment="Tillfälligt sortiment", is_news=True,
    )


class SwedenConnector(MarketConnector):
    market = Market("se", "Sweden", "🇸🇪", "SEK", "sv", "Systembolaget")
    review_lang = "sv"

    def _release_urls(self) -> list[str]:
        soup = BeautifulSoup(_get(INDEX_URL), "html.parser")
        urls: list[str] = []
        for a in soup.select('a[href*="/recensioner/"]'):
            href = a.get("href", "")
            if "/recensioner/" not in href:
                continue
            if href.rstrip("/").endswith("/recensioner"):
                continue
            full = href if href.startswith("http") else BASE + href
            if full not in urls:
                urls.append(full)
        return urls

    def fetch_new_releases(self, days_back: int) -> list[Wine]:
        since = _date(SE_SINCE) or dt.date(2026, 6, 1)
        try:
            urls = self._release_urls()
        except Exception as exc:  # noqa: BLE001
            print(f"[se] kunde inte hämta index: {exc}")
            return []

        by_nr: dict[str, dict] = {}
        for url in urls:
            try:
                found = _parse_release(_get(url))
            except Exception as exc:  # noqa: BLE001
                print(f"[se] hoppar {url}: {exc}")
                continue
            if not found:
                continue
            recent = [w for w in found if _date(w["date"]) and _date(w["date"]) >= since]
            for w in recent:
                by_nr.setdefault(w["nr"], w)   # första (nyaste sidan) vinner
            # Index är nyast-först: om HELA sidan är äldre än startdatum → sluta.
            newest_on_page = max((_date(w["date"]) for w in found if _date(w["date"])),
                                 default=None)
            if newest_on_page and newest_on_page < since:
                break

        wines = [_to_wine(w) for w in by_nr.values()]
        wines.sort(key=lambda x: x.launch_date, reverse=True)
        print(f"[se] {len(wines)} viner från {since.isoformat()} och framåt "
              f"(källa: Vintelegrafen)")
        return wines
