// WineDrop service worker — cachar app-skalet och senast hämtade marknad.
const CACHE = "winedrop-v11";
const SHELL = [
  "./", "./index.html", "./styles.css", "./app.js", "./i18n.js",
  "./config.js", "./push.js", "./manifest.webmanifest", "./icon.svg",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// --- Push-notiser ---
self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data && e.data.text() }; }
  const title = d.title || "🍷 WineDrop";
  const opts = {
    body: d.body || "New wine releases are out.",
    icon: "./icon.svg",
    badge: "./icon.svg",
    data: { url: d.url || "./index.html" },
    tag: d.tag || "winedrop",
  };
  e.waitUntil(self.registration.showNotification(title, opts));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "./index.html";
  e.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((cs) => {
      for (const c of cs) if ("focus" in c) return c.focus();
      return self.clients.openWindow(url);
    })
  );
});

// Nätverk först för API (färsk data), cache-fallback offline.
// Cache först för skalet (snabb start).
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  const isApi = url.pathname.includes("/api/");
  if (isApi) {
    e.respondWith(
      fetch(e.request).then((r) => {
        const copy = r.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return r;
      }).catch(() => caches.match(e.request))
    );
  } else {
    e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
  }
});
