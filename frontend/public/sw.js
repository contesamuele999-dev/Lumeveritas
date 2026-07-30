// Service worker minimo: serve solo a rendere l'app installabile e a dare una
// pagina quando si è offline. Le notizie NON vengono messe in cache: sono generate
// dal backend e devono restare fresche.
const CACHE = "lv-shell-v1";
const SHELL = ["/", "/index.html", "/manifest.json", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  // navigazioni: rete, e se non c'è rete la shell dalla cache
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).catch(() => caches.match("/index.html")));
    return;
  }
  e.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
});
