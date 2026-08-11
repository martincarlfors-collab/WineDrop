"""Rangordning efter "eftertraktan".

Poängen är avsiktligt enkel och transparent. Den kombinerar signaler som
korrelerar med hur eftertraktat ett vin är:

  * Tillfälligt sortiment / småpartier  → släpps i begränsad mängd, tar snabbt slut
  * Nyhetsflagga                         → aktivt lyft av butiken
  * Liten volym                          → ofta småparti / premium
  * Pris                                 → SVAG signal, bara tiebreak (undvik snoblista)
  * Antal recensioner                    → läggs till i pipelinen efter sökning

Justera vikterna här om du vill ändra vad som räknas som "intressant".
"""
from __future__ import annotations

from .schema import Wine

W_LIMITED = 3.0      # tillfälligt sortiment
W_NEWS = 1.0         # nyhetsflagga
W_SMALL_VOL = 0.5    # liten volym
W_PRICE = 0.5        # svag pris-tiebreak (0..0.5)
W_REVIEW = 0.5       # per recension (max 4 räknas) — läggs till separat


def desirability(wine: Wine) -> float:
    """Förhandspoäng utan nätverk (används för att välja vilka som betygsätts)."""
    s = 0.0
    a = (getattr(wine, "assortment", "") or "").lower()
    if "tillfäll" in a or "small" in a or "limited" in a:
        s += W_LIMITED
    if getattr(wine, "is_news", False):
        s += W_NEWS
    vol = getattr(wine, "volume", None) or 0
    if 0 < vol <= 500:
        s += W_SMALL_VOL
    if wine.price:
        s += min(wine.price, 1000) / 1000 * W_PRICE
    return s


def review_bonus(n_reviews: int) -> float:
    """Extrapoäng för faktisk uppmärksamhet (max 4 recensioner räknas)."""
    return min(n_reviews, 4) * W_REVIEW


def final_score(wine: Wine, n_reviews: int) -> float:
    return desirability(wine) + review_bonus(n_reviews)
