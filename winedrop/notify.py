"""Skicka push-notiser efter en pipeline-körning.

Jämför nya släpp-antal mot förra körningen (site/api/<market>/latest.json vs
.cache/last_counts.json) och notifierar prenumeranter på de marknader som fått
nya släpp. Körs sist i veckojobbet, efter run.py.

Kräver VAPID-nycklar (samma publika nyckel som i site/config.js):
    export VAPID_PUBLIC=...   VAPID_PRIVATE=...   VAPID_SUBJECT=mailto:you@example.com
    pip install pywebpush

    python notify.py
"""
from __future__ import annotations
import json
import os

from core import config

SUBS_FILE = os.environ.get("WD_SUBS_FILE",
                           os.path.join(config.BASE_DIR, "push_server", "subscriptions.json"))
COUNTS_FILE = os.path.join(config.CACHE_DIR, "last_counts.json")

VAPID_PUBLIC = os.environ.get("VAPID_PUBLIC", "")
VAPID_PRIVATE = os.environ.get("VAPID_PRIVATE", "")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:admin@example.com")


def _read_json(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def _current_counts() -> dict[str, int]:
    counts = {}
    api = config.API_DIR
    for market in os.listdir(api):
        latest = os.path.join(api, market, "latest.json")
        if os.path.isfile(latest):
            counts[market] = len(_read_json(latest, {}).get("wines", []))
    return counts


def _market_name(code: str) -> str:
    markets = _read_json(os.path.join(config.API_DIR, "markets.json"), [])
    for m in markets:
        if m.get("code") == code:
            return f'{m.get("flag","")} {m.get("name",code)}'
    return code


def _producers_this_week(code: str) -> list[str]:
    latest = _read_json(os.path.join(config.API_DIR, code, "latest.json"), {})
    return [str(w.get("producer", "")).strip() for w in latest.get("wines", [])
            if w.get("producer")]


def main() -> int:
    if not (VAPID_PUBLIC and VAPID_PRIVATE):
        print("VAPID-nycklar saknas — hoppar över notiser."); return 0
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        print("pywebpush saknas (pip install pywebpush) — hoppar över."); return 0

    current = _current_counts()
    previous = _read_json(COUNTS_FILE, {})
    # Marknader med FLER släpp än förra körningen = något nytt
    changed = {m: c for m, c in current.items() if c > previous.get(m, 0)}
    json.dump(current, open(COUNTS_FILE, "w"))

    # Producenter per marknad denna vecka (för bevakningsmatchning)
    prod_by_market = {m: [p.lower() for p in _producers_this_week(m)] for m in current}

    subs = _read_json(SUBS_FILE, [])
    sent, dead = 0, []
    for row in subs:
        market = row.get("market")
        watch = [w.lower() for w in row.get("watch", [])]
        # Matcha bevakade producenter mot veckans släpp i användarens marknad
        matched = [w for w in watch if w in prod_by_market.get(market, [])]

        market_has_new = market in changed
        if not market_has_new and not matched:
            continue

        if matched:
            body = f"New release from {matched[0].title()} in {_market_name(market)}"
        else:
            body = f"{changed[market]} new release(s) in {_market_name(market)}"
        payload = json.dumps({
            "title": "🍷 WineDrop",
            "body": body,
            "url": "./index.html",
            "tag": f"wd-{market}",
        })
        try:
            webpush(
                subscription_info=row["subscription"],
                data=payload,
                vapid_private_key=VAPID_PRIVATE,
                vapid_claims={"sub": VAPID_SUBJECT},
            )
            sent += 1
        except WebPushException as e:
            # 404/410 = död prenumeration, städa bort
            if e.response is not None and e.response.status_code in (404, 410):
                dead.append(row["subscription"]["endpoint"])

    if dead:
        subs = [r for r in subs if r["subscription"]["endpoint"] not in dead]
        json.dump(subs, open(SUBS_FILE, "w"))

    print(f"Skickade {sent} notis(er) över {len(changed)} marknad(er); rensade {len(dead)} döda.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
