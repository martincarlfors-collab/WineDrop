"""WineDrop-pipeline: kör alla marknader och generera JSON-API.

Kör från winedrop/-mappen:
    python run.py                 # skarpt, alla marknader
    python run.py --demo          # exempeldata (offline)
    python run.py --market se     # bara en marknad
    python run.py --limit 5       # max 5 vin per marknad
"""
from __future__ import annotations
import argparse
import sys

from core import config
from core.markets import ALL_CONNECTORS, get_connector
from core.reviews import fetch_reviews
from core.summarize import summarize
from core.schema import Summary
from core import build_api, demo_data, history, rank


def process_market(conn, limit: int, demo: bool):
    m = conn.market
    if demo:
        wines = demo_data.demo_releases(m.code)
        pairs = [(w, demo_data.demo_summary(w.id) or Summary()) for w in wines]
        pairs.sort(key=lambda p: rank.desirability(p[0]), reverse=True)
        return pairs

    wines = conn.fetch_new_releases(config.DAYS_BACK)
    # Rangordna efter eftertraktan; betygsätt bara de mest eftertraktade.
    wines.sort(key=rank.desirability, reverse=True)
    if limit:
        wines = wines[:limit]

    top_n = config.SOUGHT_AFTER_TOP_N or len(wines)
    scored = []
    for i, w in enumerate(wines, 1):
        if i <= top_n:
            print(f"  [{m.code}] betygsätter {i}/{min(top_n, len(wines))} {w.name}", flush=True)
            reviews = fetch_reviews(w, conn.review_lang)
            summ = summarize(w, reviews, conn.review_lang)
            nrev = len(reviews)
        else:
            summ = Summary()      # listas med pris, utan betyg
            nrev = 0
        scored.append((rank.final_score(w, nrev), w, summ))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [(w, s) for _, w, s in scored]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="WineDrop pipeline")
    ap.add_argument("--demo", action="store_true", help="använd exempeldata offline")
    ap.add_argument("--market", help="kör bara denna marknadskod")
    ap.add_argument("--limit", type=int, default=0, help="max vin per marknad")
    args = ap.parse_args(argv)

    connectors = ([get_connector(args.market)] if args.market
                  else list(ALL_CONNECTORS))
    connectors = [c for c in connectors if c]
    if not connectors:
        print("Ingen giltig marknad."); return 1

    counts: dict[str, int] = {}
    markets = []
    for conn in connectors:
        print(f"Marknad: {conn.market.flag} {conn.market.name}", flush=True)
        pairs = process_market(conn, args.limit, args.demo)
        build_api.write_market(conn.market, pairs)
        history.record(conn.market, pairs)
        counts[conn.market.code] = len(pairs)
        markets.append(conn.market)

    # markets.json ska alltid lista ALLA marknader (även de utan släpp)
    all_markets = [c.market for c in ALL_CONNECTORS]
    build_api.write_index(all_markets, counts)

    total = sum(counts.values())
    print(f"Klart. {total} vin över {len(counts)} marknad(er). API i site/api/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
