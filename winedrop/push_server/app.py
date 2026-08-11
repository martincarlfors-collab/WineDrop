"""Minimal prenumerations-server för WineDrop push.

Lagrar push-prenumerationer per marknad i en JSON-fil. Kör var som helst
(Fly.io, Render, en liten VPS, eller lokalt). Notissändaren (notify.py) läser
samma fil. För produktion: byt filen mot en riktig databas.

    pip install flask
    python app.py            # lyssnar på :5000
Endpoints:
    POST /subscribe   {subscription, market}
    DELETE /subscribe {endpoint}
    GET  /health
"""
from __future__ import annotations
import json
import os
import threading

from flask import Flask, request, jsonify

STORE = os.environ.get("WD_SUBS_FILE",
                       os.path.join(os.path.dirname(__file__), "subscriptions.json"))
_lock = threading.Lock()
app = Flask(__name__)


def _load() -> list[dict]:
    try:
        return json.load(open(STORE))
    except Exception:
        return []


def _save(rows: list[dict]) -> None:
    json.dump(rows, open(STORE, "w"))


@app.post("/subscribe")
def subscribe():
    body = request.get_json(force=True, silent=True) or {}
    sub = body.get("subscription")
    market = body.get("market", "se")
    if not sub or "endpoint" not in sub:
        return jsonify(error="missing subscription"), 400
    with _lock:
        rows = _load()
        rows = [r for r in rows if r["subscription"]["endpoint"] != sub["endpoint"]]
        rows.append({"subscription": sub, "market": market})
        _save(rows)
    return jsonify(ok=True, count=len(rows))


@app.delete("/subscribe")
def unsubscribe():
    body = request.get_json(force=True, silent=True) or {}
    endpoint = body.get("endpoint")
    with _lock:
        rows = [r for r in _load() if r["subscription"]["endpoint"] != endpoint]
        _save(rows)
    return jsonify(ok=True, count=len(rows))


@app.get("/health")
def health():
    return jsonify(ok=True, subscribers=len(_load()))


if __name__ == "__main__":
    # CORS så PWA:n (annan origin) får posta hit.
    @app.after_request
    def cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "POST, DELETE, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
