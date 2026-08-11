// WineDrop push-prenumeration (Web Push).
// Konfigureras via window.WD_PUSH i config.js: { publicKey, subscribeUrl }.
(function () {
  const cfg = window.WD_PUSH || {};
  const btn = document.getElementById("bellBtn");
  if (!btn) return;

  const supported = "serviceWorker" in navigator && "PushManager" in window;
  if (!supported || !cfg.publicKey || !cfg.subscribeUrl) {
    btn.hidden = true; // push ej konfigurerat -> dölj knappen
    return;
  }

  function urlB64ToUint8(base64) {
    const pad = "=".repeat((4 - (base64.length % 4)) % 4);
    const b64 = (base64 + pad).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(b64);
    return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
  }

  async function currentSub() {
    const reg = await navigator.serviceWorker.ready;
    return reg.pushManager.getSubscription();
  }

  async function refreshUI() {
    const sub = await currentSub();
    btn.textContent = sub ? "🔔" : "🔕";
    btn.title = sub ? "Notiser på" : "Notiser av";
  }

  function postSub(sub) {
    const market = localStorage.getItem("wd_market") || "se";
    const watch = JSON.parse(localStorage.getItem("wd_watch") || "[]");
    return fetch(cfg.subscribeUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subscription: sub, market, watch }),
    });
  }

  async function subscribe() {
    const perm = await Notification.requestPermission();
    if (perm !== "granted") return;
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlB64ToUint8(cfg.publicKey),
    });
    await postSub(sub);
    await refreshUI();
  }

  // Anropas av app.js när marknad/bevakningslista ändras.
  window.WD_syncSubscription = async function () {
    const sub = await currentSub();
    if (sub) await postSub(sub);
  };

  async function unsubscribe() {
    const sub = await currentSub();
    if (sub) {
      // meddela servern (best effort) och avsluta lokalt
      fetch(cfg.subscribeUrl, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint: sub.endpoint }),
      }).catch(() => {});
      await sub.unsubscribe();
    }
    await refreshUI();
  }

  btn.hidden = false;
  btn.onclick = async () => {
    const sub = await currentSub();
    if (sub) await unsubscribe();
    else await subscribe();
  };
  refreshUI();
})();
