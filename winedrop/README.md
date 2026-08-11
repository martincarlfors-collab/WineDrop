# 🍷 WineDrop

En global mobilapp (PWA) som visar veckans nya vinsläpp från olika länders
monopol/butiker. Användaren väljer **marknad** och **språk** och ser nya släpp med
AI-sammanfattade recensioner. Se [`ARCHITECTURE.md`](ARCHITECTURE.md) för designen.

## Funktioner

- **Senaste** — nya släpp för vald marknad, med AI-sammanfattning och betyg.
- **Utforska** — flera marknader samtidigt, filter för typ/land och sortering.
- **Trender** — snittbetyg per vecka och topp-producenter (byggs upp över tid).
- **Push-notiser** när din marknad får nya släpp (se `push_server/README.md`).
- **Native** — paketera till iOS/Android med Capacitor (se `NATIVE.md`).

## Två delar

1. **Backend** (`core/` + `run.py`) — en connector per land hämtar nya släpp,
   samlar recensioner, sammanfattar med Claude och skriver en statisk JSON-API.
2. **App** (`site/`) — installerbar mobil-PWA som läser JSON-API:n. Ingen server.

## Snabbstart

```bash
pip install -r requirements.txt

# 1) Generera API med exempeldata (offline, ingen nyckel behövs):
python run.py --demo

# 2) Servera appen lokalt:
cd site && python -m http.server 8000
# öppna http://localhost:8000 i mobilläge i webbläsaren
```

Skarp körning:

```bash
export ANTHROPIC_API_KEY=sk-...        # AI-sammanfattningar
export VINMONOPOLET_KEY=...            # Norge (registrera på api.vinmonopolet.no)
python run.py                          # alla marknader
python run.py --market se --limit 10   # bara Sverige, max 10
```

## Lägga till en ny marknad

1. Skapa `core/markets/<land>.py` med en klass som ärver `MarketConnector`
   och implementerar `fetch_new_releases()` → lista av normaliserade `Wine`.
2. Registrera den i `core/markets/__init__.py` (`ALL_CONNECTORS`).
3. Lägg ev. recensionskällor för språket i `core/reviews.py` (`SOURCES_BY_LANG`).

Inget annat behöver ändras — appen plockar upp marknaden automatiskt via `markets.json`.

## Marknader nu

| Marknad | Källa | Status |
|---------|-------|--------|
| 🇸🇪 Sverige | Systembolaget-datamirror | Riktig |
| 🇳🇴 Norge | Vinmonopolet öppna API | Riktig (kräver nyckel) |
| 🇫🇮 Finland | Alko | Stub (interface klart) |
| 🇨🇦 Kanada | LCBO | Stub (interface klart) |

## Publicering

Push till GitHub. `.github/workflows/weekly.yml` kör pipelinen varje måndag och
publicerar `site/` till GitHub Pages — globalt via CDN. Lägg `ANTHROPIC_API_KEY`
och `VINMONOPOLET_KEY` som repo-secrets.

## Till native-app

PWA:n kan paketeras till iOS/Android med **Capacitor** (samma kod), eller byggas
om i **Expo/React Native** mot samma JSON-API. Datalagret är oförändrat.

## Juridik

Publicerar aldrig recensioner ordagrant — bara AI-sammanfattning + källänk.
Respekterar robots.txt och varje datakällas villkor.
