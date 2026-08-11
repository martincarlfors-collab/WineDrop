"""Recensionsinsamling via riktig webbsökning.

Flöde per vin:
  1. Sök på webben (Brave/DDG) efter "<producent> <vin> <årgång> recension".
  2. Ranka träffar mot en lista av kända recensionsdomäner per språk.
  3. Hämta topp-sidorna (robots.txt + rate limit + cache) och extrahera brödtext.
  4. Returnera korta utdrag som LLM-steget sammanfattar.

Robustare än fasta CSS-selektorer: nya sajter fångas automatiskt via sökningen.
"""
from __future__ import annotations
import hashlib
import os
import random
import re
import time
import urllib.parse
import urllib.robotparser as robotparser
from dataclasses import dataclass, asdict
from typing import Any

import requests
from bs4 import BeautifulSoup

from . import config
from .schema import Wine
from .search import web_search

# Ord som läggs till söktermen per språk + kända recensionsdomäner att prioritera.
LANG_PROFILE: dict[str, dict[str, Any]] = {
    "sv": {"term": "vin recension",
           "domains": ["vinbanken.se", "alltomvin.se", "bkwine.com", "livetsgoda.se"]},
    "no": {"term": "vin anmeldelse",
           "domains": ["aperitif.no", "vinforum.no"]},
    "fi": {"term": "viini arvostelu",
           "domains": ["viinilehti.fi", "viini-lehti.fi"]},
    "en": {"term": "wine review",
           "domains": ["decanter.com", "winespectator.com", "jancisrobinson.com",
                       "vinous.com", "wineenthusiast.com"]},
}


@dataclass
class ReviewSnippet:
    source: str
    title: str
    url: str
    excerpt: str
    lang: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_last: dict[str, float] = {}
_robots: dict[str, Any] = {}


def _domain(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.replace("www.", "")


def _allowed(url: str) -> bool:
    dom = urllib.parse.urlparse(url).netloc
    if dom not in _robots:
        rp = robotparser.RobotFileParser()
        rp.set_url(f"https://{dom}/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None
        _robots[dom] = rp
    rp = _robots[dom]
    return True if rp is None else rp.can_fetch(config.USER_AGENT, url)


def _throttle(url: str) -> None:
    dom = urllib.parse.urlparse(url).netloc
    wait = config.REQUEST_DELAY_SEC - (time.time() - _last.get(dom, 0))
    if wait > 0:
        time.sleep(wait + random.uniform(0, config.REQUEST_JITTER_SEC))
    _last[dom] = time.time()


def _fetch(url: str) -> str | None:
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    path = os.path.join(config.CACHE_DIR, f"{key}.html")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    if not _allowed(url):
        return None
    _throttle(url)
    try:
        r = requests.get(url, headers={"User-Agent": config.USER_AGENT},
                         timeout=config.REQUEST_TIMEOUT_SEC)
        if r.status_code != 200:
            return None
        html = r.text
    except requests.RequestException:
        return None
    open(path, "w", encoding="utf-8").write(html)
    return html


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    node = soup.find("article") or soup.find("main") or soup.body or soup
    text = re.sub(r"\s+", " ", node.get_text(" ", strip=True))
    return text[:600]


def _rank(hits, domains: list[str]):
    """Kända recensionsdomäner först, i övrigt sökordningen."""
    known = [h for h in hits if _domain(h.url) in domains]
    other = [h for h in hits if _domain(h.url) not in domains]
    return known + other


def fetch_reviews(wine: Wine, lang: str) -> list[ReviewSnippet]:
    profile = LANG_PROFILE.get(lang, LANG_PROFILE["en"])
    query = f"{wine.query()} {profile['term']}"
    hits = web_search(query, count=8, lang=lang)
    hits = _rank(hits, profile["domains"])

    out: list[ReviewSnippet] = []
    for h in hits:
        if not h.url:
            continue
        html = _fetch(h.url)
        excerpt = _extract_text(html) if html else (h.snippet or "")
        if not excerpt:
            continue
        out.append(ReviewSnippet(
            source=_domain(h.url) or "web",
            title=h.title or wine.name,
            url=h.url,
            excerpt=excerpt,
            lang=lang,
        ))
        if len(out) >= config.MAX_REVIEWS_PER_WINE:
            break
    return out
