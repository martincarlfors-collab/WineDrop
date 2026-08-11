"""🇫🇮 Finland — Alko via deras öppna prislista (xlsx, uppdateras månadsvis).

Alko publicerar hela sortimentet som en Excel-fil. Vi laddar ner den, hittar
kolumnrubrikerna dynamiskt (de har ändrats historiskt) och plockar viner.

Obs: prislistan har inget tillförlitligt "lanseringsdatum", så "nytt" approximeras
via nyhetskolumnen ("Uutuus") om den finns, annars via diff mot förra körningen
(sparas i .cache/alko_seen.json).
"""
from __future__ import annotations
import io
import json
import os

import requests

from .. import config
from ..schema import Market, Wine
from .base import MarketConnector

PRICE_LIST_URL = (
    "https://www.alko.fi/INTERSHOP/static/WFS/Alko-OnlineShop-Site/-/"
    "Alko-OnlineShop/fi_FI/Alkon%20Hinnasto%20Tekstitiedostona/"
    "alkon-hinnasto-tekstitiedostona.xlsx"
)
SEEN_FILE = os.path.join(config.CACHE_DIR, "alko_seen.json")


def _find_col(headers: list[str], *needles: str) -> int | None:
    for i, h in enumerate(headers):
        hl = str(h).lower()
        if any(n in hl for n in needles):
            return i
    return None


class FinlandConnector(MarketConnector):
    market = Market("fi", "Finland", "🇫🇮", "EUR", "fi", "Alko")
    review_lang = "fi"

    def fetch_new_releases(self, days_back: int) -> list[Wine]:
        try:
            import openpyxl  # lazy: bara Finland behöver det
        except ImportError:
            print("[fi] openpyxl saknas (pip install openpyxl) — hoppar över")
            return []
        try:
            r = requests.get(PRICE_LIST_URL,
                             headers={"User-Agent": config.USER_AGENT},
                             timeout=config.REQUEST_TIMEOUT_SEC)
            r.raise_for_status()
            wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[fi] kunde inte hämta prislistan: {exc}")
            return []

        ws = wb.active
        rows = ws.iter_rows(values_only=True)

        # Hitta rubrikraden (första raden med "hinta"/pris i någon cell)
        headers = None
        for row in rows:
            cells = [str(c) if c is not None else "" for c in row]
            if any("hinta" in c.lower() for c in cells):
                headers = cells
                break
        if not headers:
            print("[fi] hittade ingen rubrikrad"); return []

        c_number = _find_col(headers, "numero")
        c_name = _find_col(headers, "nimi")
        c_producer = _find_col(headers, "valmistaja")
        c_type = _find_col(headers, "tyyppi")
        c_price = _find_col(headers, "hinta")
        c_country = _find_col(headers, "maa", "valmistusmaa")
        c_vintage = _find_col(headers, "vuosikerta")
        c_group = _find_col(headers, "ryhmä", "kategoria")
        c_new = _find_col(headers, "uutuus", "uusi")

        seen = self._load_seen()
        new_seen = set()
        wines: list[Wine] = []

        for row in rows:
            def cell(i):
                return "" if i is None or i >= len(row) or row[i] is None else str(row[i]).strip()

            group = cell(c_group).lower()
            type_ = cell(c_type).lower()
            if "viini" not in group and "viini" not in type_ and "wine" not in type_:
                continue

            number = cell(c_number)
            if not number:
                continue
            new_seen.add(number)

            is_new = False
            if c_new is not None:
                is_new = cell(c_new).lower() in ("kyllä", "x", "1", "true", "uutuus")
            if not is_new and number not in seen and seen:
                is_new = True  # dök upp sedan förra körningen
            if seen and not is_new:
                continue

            wines.append(Wine(
                id=f"fi-{number}",
                market="fi",
                name=cell(c_name),
                producer=cell(c_producer),
                wine_type=cell(c_type),
                vintage=cell(c_vintage),
                origin_country=cell(c_country),
                price=_f(cell(c_price)),
                currency="EUR",
                launch_date="",
                url=f"https://www.alko.fi/tuotteet/{number}/",
            ))

        self._save_seen(new_seen or seen)
        return wines

    # --- diff-minne ---
    def _load_seen(self) -> set[str]:
        try:
            return set(json.load(open(SEEN_FILE)))
        except Exception:
            return set()

    def _save_seen(self, s: set[str]) -> None:
        try:
            json.dump(sorted(s), open(SEEN_FILE, "w"))
        except Exception:
            pass


def _f(v):
    try:
        return float(str(v).replace(",", ".").replace("€", "").strip())
    except (TypeError, ValueError):
        return None
