"""Global konfiguration."""
from __future__ import annotations
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, ".cache")
SITE_DIR = os.path.join(BASE_DIR, "site")
API_DIR = os.path.join(SITE_DIR, "api")

for _d in (CACHE_DIR, API_DIR):
    os.makedirs(_d, exist_ok=True)

# Hur nya släpp som räknas (dagar bakåt)
DAYS_BACK = 8

# Sverige: sortimentsfilter. Tomt = ALLA viner som släpps under veckan
# (både fasta och tillfälliga sortimentet). Sätt t.ex. "Tillfälligt sortiment"
# för att bara ta med det tillfälliga sortimentet.
SE_ASSORTMENT = os.environ.get("SE_ASSORTMENT", "")

# Betygssätt bara de N mest eftertraktade vinerna per marknad (LLM-anrop kostar).
# Övriga listas ändå med pris, utan betyg. 0 = betygssätt alla.
SOUGHT_AFTER_TOP_N = int(os.environ.get("SOUGHT_AFTER_TOP_N", "25"))

# Skrapningsartighet
USER_AGENT = "WineDropBot/0.1 (+https://example.com/winedrop; contact@example.com)"
REQUEST_DELAY_SEC = 2.0
REQUEST_JITTER_SEC = 1.0
REQUEST_TIMEOUT_SEC = 20
MAX_REVIEWS_PER_WINE = 5

# LLM
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LLM_MODEL = "claude-sonnet-5"

# Marknadsspecifika nycklar
VINMONOPOLET_KEY = os.environ.get("VINMONOPOLET_KEY", "")

# Datakällor
SYSTEMBOLAGET_MIRROR = (
    "https://raw.githubusercontent.com/AlexGustafsson/"
    "systembolaget-api-data/main/data/assortment.json"
)
VINMONOPOLET_API = "https://apis.vinmonopolet.no/products/v0/details-normal"

# UI-språk som appen stödjer
SUPPORTED_UI_LANGS = ["en", "sv", "no", "fi"]
