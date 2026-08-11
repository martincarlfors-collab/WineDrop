# WineDrop push-notiser

Web Push för PWA:n. Tre delar:

1. **`site/push.js` + `sw.js`** — klienten prenumererar och service workern visar notisen.
2. **`push_server/app.py`** — liten server som lagrar prenumerationer (Flask).
3. **`notify.py`** — skickar notiser efter varje pipeline-körning till marknader med nya släpp.

## Setup (en gång)

```bash
pip install cryptography flask pywebpush

# 1) Generera VAPID-nycklar
python push_server/gen_vapid.py
```

Lägg **publika** nyckeln i `site/config.js`:

```js
window.WD_PUSH = {
  publicKey: "<VAPID_PUBLIC>",
  subscribeUrl: "https://din-server.example/subscribe",
};
```

Sätt hemligheterna där notify.py körs (t.ex. GitHub Secrets):

```
VAPID_PUBLIC=<...>
VAPID_PRIVATE=<...>
VAPID_SUBJECT=mailto:du@example.com
```

## Kör prenumerations-servern

```bash
python push_server/app.py       # POST/DELETE /subscribe, GET /health
```

Deploya den var som helst med en beständig disk (Fly.io, Render, Railway, VPS).
För riktig skala: byt `subscriptions.json` mot Postgres/Redis.

## Flöde

```
Användare trycker 🔔 → push.js prenumererar → POST /subscribe (lagras per marknad)
Veckojobb: run.py → notify.py jämför antal → webpush till marknader med nya släpp
Telefonen får notis även när appen är stängd (via service worker).
```

## Varför en liten server behövs

Statisk hosting kan inte ta emot eller lagra prenumerationer eller skicka push.
Servern är avsiktligt minimal — allt annat i WineDrop är serverlöst. Vill du
hålla allt serverlöst kan `app.py` bytas mot en Cloudflare Worker + KV med samma
två endpoints.
