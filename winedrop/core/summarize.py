"""Flerspråkig LLM-sammanfattning per vin.

Output: betyg 0-100 + text på marknadens språk OCH engelska (reserv).
Utan API-nyckel/recensioner returneras en tom men giltig Summary.
"""
from __future__ import annotations
import json

from . import config
from .schema import Wine, Summary
from .reviews import ReviewSnippet

_PROMPT = """You are a wine editor. Below are excerpts from wine reviews of ONE wine.
Summarise the critics' consensus. Output BOTH the market language ("{lang}") and English.

Wine: {name} ({producer}, {vintage}, {country})

Review excerpts (source | title | excerpt):
{snippets}

Reply with ONLY valid JSON:
{{
  "score": <integer 0-100, or null if no basis>,
  "verdict": {{ "{lang}": "2-3 sentences", "en": "2-3 sentences" }},
  "taste_notes": {{ "{lang}": "short", "en": "short" }},
  "pairing": {{ "{lang}": "pairs with...", "en": "pairs with..." }}
}}
Do not invent a score without support; use null then."""


def _empty(snippets: list[ReviewSnippet], lang: str) -> Summary:
    msg_en = (f"{len(snippets)} source(s) found. Set ANTHROPIC_API_KEY for an AI summary."
              if snippets else "No reviews found yet.")
    return Summary(
        verdict={"en": msg_en, lang: msg_en},
        score=None, taste_notes={}, pairing={},
        sources=[s.to_dict() for s in snippets],
    )


def summarize(wine: Wine, snippets: list[ReviewSnippet], lang: str) -> Summary:
    if not config.ANTHROPIC_API_KEY or not snippets:
        return _empty(snippets, lang)
    try:
        from anthropic import Anthropic
    except ImportError:
        return _empty(snippets, lang)

    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    snippet_text = "\n".join(f"- {s.source} | {s.title} | {s.excerpt}" for s in snippets)
    prompt = _PROMPT.format(lang=lang, name=wine.name, producer=wine.producer,
                            vintage=wine.vintage, country=wine.origin_country,
                            snippets=snippet_text)
    try:
        msg = client.messages.create(
            model=config.LLM_MODEL, max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception as exc:  # noqa: BLE001
        s = _empty(snippets, lang)
        s.verdict = {"en": f"Could not summarise ({exc.__class__.__name__})."}
        return s

    return Summary(
        verdict=_d(data.get("verdict")),
        score=_score(data.get("score")),
        taste_notes=_d(data.get("taste_notes")),
        pairing=_d(data.get("pairing")),
        sources=[s.to_dict() for s in snippets],
    )


def _d(v) -> dict[str, str]:
    return {str(k): str(val) for k, val in v.items()} if isinstance(v, dict) else {}


def _score(v):
    try:
        return max(0, min(100, int(v)))
    except (TypeError, ValueError):
        return None
