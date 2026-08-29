/* Service worker — Phase 0 shell.
 *
 * App shell: cache-first with a versioned cache (bump CACHE_VERSION on deploy).
 * API: network-only for now. Phase 2 adds:
 *   - /api/media/<id>  -> cache-first, long-lived (stable URLs, immutable assets)
 *   - offline outbox replay on 'sync'
 */

const CACHE_VERSION = "shell-v2";
const SHELL = [
  "/",
  "/index.html",
  "/css/tokens.css",
  "/css/base.css",
  "/css/components/app.css",
  "/js/app.js",
  "/js/api.js",
  "/js/db.js",
  "/js/outbox.js",
  "/js/session.js",
  "/js/ui.js",
  "/js/views/auth.js",
  "/js/views/pinpad.js",
  "/js/views/home.js",
  "/js/views/dashboard.js",
  "/manifest.webmanifest",
  "/assets/icon-192.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // API: straight to network for now.
  if (url.pathname.startsWith("/api/")) return;

  // App shell / static: cache-first, fall back to network, then to index.html
  // for navigations so the installed app opens offline.
  event.respondWith(
    caches.match(request).then(
      (hit) =>
        hit ||
        fetch(request)
          .then((res) => {
            const copy = res.clone();
            caches.open(CACHE_VERSION).then((c) => c.put(request, copy));
            return res;
          })
          .catch(() => {
            if (request.mode === "navigate") return caches.match("/index.html");
            return Response.error();
          }),
    ),
  );
});
