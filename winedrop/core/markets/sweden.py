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


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _section_for(table) -> str:
    """Närmaste föregående rubrik som matchar en vintyp (för bottle-färg/filter)."""
    def is_sec(tag):
        return tag.name in ("h1", "h2", "h3", "h4", "h5", "p", "strong") \
            and _norm(tag.get_text()).lower() in _SECTIONS
    prev = table.find_previous(is_sec)
    return _SECTIONS.get(_norm(prev.get_text()).lower(), "") if prev else ""


def _parse_release(html: str) -> list[dict]:
    """Parsa en släppsidas vin-tabeller till poster (fakta, inga betyg).

    Varje vin ligger i en <table class="vinlista"> med:
      <h4>årgång + namn</h4> <p>(produktnummer)</p>
      <td class="subheader" colspan=2>producent</td>
      <td class="origin">ursprung</td>
      ... rader "Lanseringsdatum:" och "Pris:" längre ner.
    """
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    for table in soup.select("table.vinlista"):
        ttext = table.get_text(" ", strip=True)
        mnr = re.search(r"\((\d{4,7})\)", ttext)
        if not mnr:
            continue
        nr = mnr.group(1)

        h4 = table.find("h4")
        header = _norm(h4.get_text()) if h4 else ""
        vintage, name = "", header
        mv = re.match(r"^(\d{4}|NV)\s+(.*)$", header)
        if mv:
            vintage = "" if mv.group(1) == "NV" else mv.group(1)
            name = mv.group(2).strip()

        prod_el = table.select_one("td.subheader[colspan='2']")
        producer = _norm(prod_el.get_text()) if prod_el else ""
        origin_el = table.select_one("td.origin")
        origin = _norm(origin_el.get_text()) if origin_el else ""
        country = origin.split(",")[-1].strip() if origin else ""

        md = re.search(r"Lanseringsdatum:\s*(\d{4}-\d{2}-\d{2})", ttext)
        mp = re.search(r"Pris:\s*(\d+)", ttext)
        date = md.group(1) if md else ""
        price = float(mp.group(1)) if mp else None

        if name and date:
            out.append({"nr": nr, "name": name, "vintage": vintage,
                        "producer": producer, "country": country,
                        "type": _section_for(table), "date": date, "price": price})
    return out


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
