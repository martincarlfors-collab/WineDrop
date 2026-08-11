"""Pluggbar webbsökning för att hitta recensioner.

Providers (i prioordning):
  1. Brave Search API   — sätt BRAVE_API_KEY (gratis nivå finns). Robust.
  2. DuckDuckGo (HTML)  — ingen nyckel, men mer skör; används som fallback.

Returnerar en lista av SearchHit (titel, url, snippet). Kastar aldrig uppåt.
"""
from __future__ import annotations
import os
import time
import urllib.parse
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from . import config

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
BRAVE_IMAGE_ENDPOINT = "https://api.search.brave.com/res/v1/images/search"

# Brave gratisnivå tillåter ~1 anrop/sekund — vänta mellan alla Brave-anrop.
_last_brave = [0.0]


def _brave_wait() -> None:
    gap = 1.1 - (time.time() - _last_brave[0])
    if gap > 0:
        time.sleep(gap)
    _last_brave[0] = time.time()


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str


def image_search(query: str, lang: str = "en") -> str:
    """Hitta en bild-URL för ett vin via Brave Image Search. Tom sträng vid miss."""
    if not BRAVE_API_KEY:
        return ""
    _brave_wait()
    try:
        r = requests.get(
            BRAVE_IMAGE_ENDPOINT,
            headers={"X-Subscription-Token": BRAVE_API_KEY,
                     "Accept": "application/json"},
            params={"q": query, "count": 3, "safesearch": "off", "search_lang": lang},
            timeout=config.REQUEST_TIMEOUT_SEC,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
    except Exception as exc:  # noqa: BLE001
        print(f"    bildsök misslyckades: {exc}")
        return ""
    for res in results:
        thumb = (res.get("thumbnail") or {}).get("src")
        if thumb:
            return thumb
        url = (res.get("properties") or {}).get("url") or res.get("url")
        if url:
            return url
    return ""


def _brave(query: str, count: int, lang: str) -> list[SearchHit]:
    _brave_wait()
    try:
        r = requests.get(
            BRAVE_ENDPOINT,
            headers={"X-Subscription-Token": BRAVE_API_KEY,
                     "Accept": "application/json"},
            params={"q": query, "count": count,
                    "search_lang": lang, "safesearch": "off"},
            timeout=config.REQUEST_TIMEOUT_SEC,
        )
        r.raise_for_status()
        results = (r.json().get("web") or {}).get("results", [])
    except Exception as exc:  # noqa: BLE001
        print(f"    brave-sök misslyckades: {exc}")
        return []
    return [SearchHit(h.get("title", ""), h.get("url", ""),
                      h.get("description", "")) for h in results][:count]


def _ddg(query: str, count: int) -> list[SearchHit]:
    """DuckDuckGo HTML-endpoint. Ingen nyckel; skör men fungerar ofta."""
    try:
        r = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.REQUEST_TIMEOUT_SEC,
        )
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
    except requests.RequestException:
        return []
    hits: list[SearchHit] = []
    for res in soup.select(".result"):
        a = res.select_one(".result__a")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        # DDG lindar länken; plocka ut riktig url om möjligt
        q = urllib.parse.urlparse(href).query
        real = urllib.parse.parse_qs(q).get("uddg", [href])[0]
        snip = res.select_one(".result__snippet")
        hits.append(SearchHit(a.get_text(strip=True), real,
                              snip.get_text(" ", strip=True) if snip else ""))
        if len(hits) >= count:
            break
    return hits


def web_search(query: str, count: int = 5, lang: str = "en") -> list[SearchHit]:
    if BRAVE_API_KEY:
        hits = _brave(query, count, lang)
        if hits:
            return hits
    return _ddg(query, count)


def provider_name() -> str:
    return "Brave" if BRAVE_API_KEY else "DuckDuckGo"
