// Service worker minimo: serve a rendere l'app installabile, a dare una pagina quando
// si è offline e a non riscaricare a ogni visita gli stessi file di codice.
// Le notizie NON vengono messe in cache: sono generate dal backend e devono restare fresche.
const SHELL_CACHE = "lv-shell-v2";
const ASSET_CACHE = "lv-assets-v2";
const KEEP = [SHELL_CACHE, ASSET_CACHE];
const SHELL = ["/", "/index.html", "/manifest.json", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL_CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => !KEEP.includes(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // le risposte dell'API non vanno mai in cache
  if (url.pathname.startsWith("/api/")) return;

  // navigazioni: rete, e se non c'è rete la shell dalla cache
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).catch(() => caches.match("/index.html")));
    return;
  }

  // build di CRA: i file sotto /static hanno l'hash nel nome, quindi non cambiano mai
  // a parità di URL. Servirli dalla cache toglie un giro di rete a ogni visita
  // successiva; l'aggiornamento in sottofondo copre eventuali file non versionati.
  if (url.pathname.startsWith("/static/")) {
    e.respondWith(
      caches.open(ASSET_CACHE).then(async (cache) => {
        const hit = await cache.match(req);
        const network = fetch(req)
          .then((res) => {
            if (res && res.ok) cache.put(req, res.clone());
            return res;
          })
          .catch(() => hit);
        return hit || network;
      })
    );
    return;
  }

  e.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
});
