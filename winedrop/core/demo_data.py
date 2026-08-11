"""Exempeldata så hela appen kan demas offline (--demo)."""
from __future__ import annotations

from .schema import Wine, Summary

_WINES = {
    "se": [
        (Wine("se-125303", "se", "Barolo Castiglione", "Vietti", "Rött", "2019",
              "Italien", 399, "SEK", "2026-08-10",
              "https://www.systembolaget.se/produkt/vin/125303/",
              assortment="Tillfälligt sortiment", volume=750, is_news=True),
         Summary(score=91,
                 verdict={"sv": "Klassisk Barolo med finess; kritiker lyfter tydlig körsbärston och lång eftersmak.",
                          "en": "A classic, elegant Barolo; critics highlight cherry notes and a long finish."},
                 taste_notes={"sv": "Körsbär, ros, tjära, fast tannin.", "en": "Cherry, rose, tar, firm tannin."},
                 pairing={"sv": "Vilt, lagrad ost.", "en": "Game, aged cheese."},
                 sources=[{"source": "Vinbanken", "title": "Barolo-provning", "url": "https://vinbanken.se/", "lang": "sv"}])),
        (Wine("se-778120", "se", "Riesling Kabinett", "Dr Loosen", "Vitt", "2022",
              "Tyskland", 189, "SEK", "2026-08-09",
              "https://www.systembolaget.se/produkt/vin/778120/"),
         Summary(score=88,
                 verdict={"sv": "Frisk och mineralisk Riesling med välbalanserad sötma.",
                          "en": "Fresh, mineral Riesling with well-balanced sweetness."},
                 taste_notes={"sv": "Lime, äpple, skiffer.", "en": "Lime, apple, slate."},
                 pairing={"sv": "Asiatiskt, skaldjur.", "en": "Asian food, shellfish."},
                 sources=[{"source": "Allt om Vin", "title": "Tyska pärlor", "url": "https://www.alltomvin.se/", "lang": "sv"}])),
        (Wine("se-244501", "se", "Châteauneuf-du-Pape", "Domaine de la Solitude", "Rött", "2021",
              "Frankrike", 349, "SEK", "2026-08-10",
              "https://www.systembolaget.se/produkt/vin/244501/",
              assortment="Tillfälligt sortiment", volume=750),
         Summary(score=90,
                 verdict={"sv": "Kraftfull men elegant Châteauneuf med mörka bär och örter.",
                          "en": "Powerful yet elegant Châteauneuf with dark berries and herbs."},
                 taste_notes={"sv": "Björnbär, lakrits, garrigue.", "en": "Blackberry, liquorice, garrigue."},
                 pairing={"sv": "Lamm, grytor.", "en": "Lamb, stews."},
                 sources=[{"source": "BKWine", "title": "Rhône-nyheter", "url": "https://www.bkwine.com/", "lang": "sv"}])),
        (Wine("se-660210", "se", "Rioja Reserva", "La Rioja Alta", "Rött", "2017",
              "Spanien", 259, "SEK", "2026-08-09",
              "https://www.systembolaget.se/produkt/vin/660210/"),
         Summary(score=87,
                 verdict={"sv": "Lagrad Rioja med vanilj, läder och mogen frukt.",
                          "en": "Aged Rioja with vanilla, leather and ripe fruit."},
                 taste_notes={"sv": "Körsbär, vanilj, läder.", "en": "Cherry, vanilla, leather."},
                 pairing={"sv": "Grillat kött, tapas.", "en": "Grilled meat, tapas."},
                 sources=[{"source": "Vinbanken", "title": "Rioja-test", "url": "https://vinbanken.se/", "lang": "sv"}])),
        (Wine("se-330144", "se", "Sancerre", "Henri Bourgeois", "Vitt", "2023",
              "Frankrike", 229, "SEK", "2026-08-11",
              "https://www.systembolaget.se/produkt/vin/330144/"),
         Summary(score=85,
                 verdict={"sv": "Krispig Sauvignon Blanc med krusbär och stenig mineralitet.",
                          "en": "Crisp Sauvignon Blanc with gooseberry and stony minerality."},
                 taste_notes={"sv": "Krusbär, citrus, flinta.", "en": "Gooseberry, citrus, flint."},
                 pairing={"sv": "Getost, sallad.", "en": "Goat cheese, salad."},
                 sources=[{"source": "Allt om Vin", "title": "Loire-släpp", "url": "https://www.alltomvin.se/", "lang": "sv"}])),
        (Wine("se-509912", "se", "Prosecco Superiore", "Nino Franco", "Mousserande", "",
              "Italien", 179, "SEK", "2026-08-11",
              "https://www.systembolaget.se/produkt/vin/509912/"),
         Summary(score=None, verdict={}, taste_notes={}, pairing={}, sources=[])),
        (Wine("se-712035", "se", "Grüner Veltliner", "Weingut Bründlmayer", "Vitt", "2023",
              "Österrike", 199, "SEK", "2026-08-08",
              "https://www.systembolaget.se/produkt/vin/712035/",
              assortment="Tillfälligt sortiment", volume=750),
         Summary(score=None, verdict={}, taste_notes={}, pairing={}, sources=[])),
    ],
    "no": [
        (Wine("no-9988", "no", "Chablis 1er Cru", "Louis Michel", "Hvit", "2021",
              "Frankrike", 329, "NOK", "2026-08-10",
              "https://www.vinmonopolet.no/p/9988"),
         Summary(score=90,
                 verdict={"no": "Presis og stram Chablis med tydelig mineralitet.",
                          "en": "Precise, taut Chablis with clear minerality."},
                 taste_notes={"no": "Sitrus, østers, flint.", "en": "Citrus, oyster, flint."},
                 pairing={"no": "Skalldyr, fisk.", "en": "Shellfish, fish."},
                 sources=[{"source": "Aperitif", "title": "Chablis-test", "url": "https://aperitif.no/", "lang": "no"}])),
    ],
    "fi": [],
    "ca": [],
}


def demo_releases(market_code: str):
    return [w for w, _ in _WINES.get(market_code, [])]


def demo_summary(wine_id: str):
    for lst in _WINES.values():
        for w, s in lst:
            if w.id == wine_id:
                return s
    return None
