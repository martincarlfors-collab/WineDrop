# WineDrop — global arkitektur

En mobilapp som visar veckans nya vinsläpp från olika länders monopol/butiker.
Användaren väljer **marknad** (land) och **språk**, och ser nya släpp med
AI-sammanfattade recensioner.

## Designprinciper

1. **En connector per marknad.** Varje land har sin egen datakälla (API, öppen
   data eller skrapning). Alla implementerar samma `MarketConnector`-interface och
   normaliserar till ett gemensamt schema. Nya länder = ny fil, inget annat ändras.
2. **Backend genererar statisk JSON-API.** Pipelinen kör på schema och skriver
   platta JSON-filer per marknad. De ligger på CDN (GitHub Pages / S3+CloudFront).
   Ingen server att drifta, oändligt skalbart globalt, billigt.
3. **Appen är en tunn klient.** Mobil-PWA som hämtar `markets.json` + vald marknads
   `latest.json`. Ingen backend-anrop i realtid → snabb överallt, funkar offline.
4. **i18n överallt.** Gränssnittet översätts via strängtabeller. Sammanfattningar
   genereras av LLM på **marknadens språk + engelska**, så en besökare alltid har
   engelska som reserv.

## Systemskiss

```
                         SCHEMALAGT VECKOJOBB (per marknad)
   ┌────────────┬────────────┬────────────┬────────────┐
   │  🇸🇪 Sverige │  🇳🇴 Norge   │  🇫🇮 Finland │  🇨🇦 Kanada  │   ← connectors
   │ Systembol. │ Vinmonopol │   Alko     │   LCBO     │
   └─────┬──────┴─────┬──────┴─────┬──────┴─────┬──────┘
         └────────────┴─────┬──────┴────────────┘
                            ▼
                 Normaliserat vinschema
                            ▼
              Recensionssök (per marknadsspråk)
                            ▼
              LLM-sammanfattning (språk + en)
                            ▼
        Statisk JSON-API:  api/markets.json
                           api/<market>/latest.json
                            ▼  (git push → CDN)
                 ┌──────────────────────┐
                 │   📱 WineDrop PWA      │  ← installerbar mobilapp
                 │  marknads- + språkval │
                 │  lista · detalj · off │
                 └──────────────────────┘
```

## Normaliserat schema (`core/schema.py`)

```
Wine:  id, market, name, producer, wine_type, vintage,
       origin_country, price, currency, launch_date, url, image
Summary: verdict{lang→text}, score(0-100), taste_notes{lang→text},
         pairing{lang→text}, sources[]
```

Betyg normaliseras alltid till 0–100 oavsett källans egen skala.

## Marknader i MVP

| Marknad | Källa | Status i MVP | Nyckel krävs |
|---------|-------|--------------|--------------|
| 🇸🇪 Sverige | Systembolaget-datamirror (JSON) | Riktig connector | Nej |
| 🇳🇴 Norge | Vinmonopolet öppna API | Riktig connector | `VINMONOPOLET_KEY` |
| 🇫🇮 Finland | Alko prislista (Excel/öppen data) | Stub + interface | Nej |
| 🇨🇦 Kanada | LCBO | Stub + interface | — |

Stub-connectors implementerar interfacet och returnerar tom lista tills källan
kopplas in — appen fungerar ändå. `--demo` fyller alla marknader med exempeldata.

## JSON-API-kontrakt

`GET api/markets.json`
```json
[{ "code":"se","name":"Sweden","flag":"🇸🇪","currency":"SEK",
   "language":"sv","retailer":"Systembolaget","updated":"2026-08-11" }]
```

`GET api/se/latest.json`
```json
{ "market":"se","week":33,"updated":"2026-08-11",
  "wines":[{ "id":"se-125303","name":"...","producer":"...","score":88,
             "verdict":{"sv":"...","en":"..."}, "sources":[...] }] }
```

## Frontend (PWA)

- **Mobil-först** layout, installeras på hemskärm (manifest + service worker).
- **Offline**: service worker cachar app-skalet och senast hämtade marknad.
- **Marknadsväljare** och **språkväljare** sparas i `localStorage`.
- Vy 1 lista över släpp (betyg, namn, pris), vy 2 detalj med sammanfattning + källänkar.
- Ren vanilla JS → inga byggsteg, laddar direkt.

## Väg till native-app

PWA:n kan wrappas till native utan omskrivning:
- **Expo/React Native** om man vill ha riktig app store-närvaro — återanvänder samma
  JSON-API. Frontend byggs då om i RN men datakontraktet är oförändrat.
- Eller **Capacitor** som paketerar exakt denna PWA till iOS/Android-binärer.

Datalagret (connectors + JSON-API) är identiskt oavsett frontend-val.

## Schemaläggning & drift

- GitHub Actions kör pipelinen per marknad (kan parallelliseras) och pushar `site/`.
- Hemligheter (`ANTHROPIC_API_KEY`, `VINMONOPOLET_KEY`) som repo-secrets.
- Kostnad: 0 kr för hosting (statiskt), endast LLM-anrop kostar.

## Juridik & etik

Samma princip som tidigare: publicera aldrig recensioner ordagrant — bara
AI-sammanfattning + källänk. Respektera varje marknads datakällas villkor
(Systembolaget och Vinmonopolet har egna användarvillkor för sin data).
Följ robots.txt och rate-limita vid skrapning.
