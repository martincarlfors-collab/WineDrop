"""Gemensamt, marknadsoberoende datamodell för WineDrop."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Market:
    code: str          # ISO-ish, t.ex. "se"
    name: str          # engelskt namn, t.ex. "Sweden"
    flag: str          # emoji
    currency: str      # "SEK"
    language: str      # BCP-47-ish, marknadens huvudspråk: "sv"
    retailer: str      # "Systembolaget"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Wine:
    id: str                       # "<market>-<lokalt id>"
    market: str                   # marknadskod
    name: str
    producer: str = ""
    wine_type: str = ""           # Rött / Vitt / Mousserande ...
    vintage: str = ""
    origin_country: str = ""      # vinets ursprungsland
    price: float | None = None
    currency: str = ""
    launch_date: str = ""         # ISO
    url: str = ""
    image: str = ""
    # Signaler för "eftertraktan"-rankning (fylls i av connectorn där de finns)
    assortment: str = ""          # t.ex. "Tillfälligt sortiment"
    volume: float | None = None   # ml (småparti/småflaska = mer eftertraktat)
    is_news: bool = False         # nyhetsflagga

    def query(self) -> str:
        return " ".join(p for p in (self.producer, self.name, self.vintage) if p).strip()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Summary:
    """Betyg 0-100. Textfält är dict språk->text (minst 'en')."""
    verdict: dict[str, str] = field(default_factory=dict)
    score: int | None = None
    taste_notes: dict[str, str] = field(default_factory=dict)
    pairing: dict[str, str] = field(default_factory=dict)
    sources: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def merge(wine: Wine, summary: Summary) -> dict[str, Any]:
    d = wine.to_dict()
    d.update(summary.to_dict())
    return d
