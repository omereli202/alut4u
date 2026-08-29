/* Service worker.
 *
 * - App shell + bundled symbols: cache-first, versioned (bump SHELL_CACHE).
 * - /api/media/<id>: cache-first in a separate, unversioned cache — the ids are
 *   content-addressed and immutable, so entries never go stale. This is what
 *   makes the AAC board (icons + pre-generated audio) work offline.
 * - Other /api/*: network-only.
 */

const SHELL_CACHE = "shell-v7";
const MEDIA_CACHE = "media-v1";
const DATA_CACHE = "data-v1"; // last-known board / day, for offline reads

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
  "/js/modules/aac/board.js",
  "/js/modules/aac/sentence-bar.js",
  "/js/modules/aac/speech.js",
  "/js/modules/aac/editor.js",
  "/js/modules/aac/symbol-picker.js",
  "/js/modules/aac/recorder.js",
  "/js/modules/schedule/index.js",
  "/js/modules/schedule/data.js",
  "/js/modules/schedule/focus.js",
  "/js/modules/schedule/day-list.js",
  "/js/modules/schedule/calendar.js",
  "/js/modules/schedule/editor.js",
  "/js/modules/rules/index.js",
  "/js/modules/rules/data.js",
  "/js/modules/rules/editor.js",
  "/js/modules/calming/index.js",
  "/js/modules/calming/sounds.js",
  "/js/modules/calming/breathing.js",
  "/js/modules/calming/memory.js",
  "/js/modules/stories/index.js",
  "/js/modules/stories/reader.js",
  "/js/modules/stories/editor.js",
  "/manifest.webmanifest",
  "/assets/icon-192.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  const keep = new Set([SHELL_CACHE, MEDIA_CACHE, DATA_CACHE]);
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => !keep.has(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

function cacheFirst(request, cacheName) {
  return caches.open(cacheName).then((cache) =>
    cache.match(request).then(
      (hit) =>
        hit ||
        fetch(request).then((res) => {
          if (res.ok || res.status === 304) cache.put(request, res.clone());
          return res;
        }),
    ),
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  if (url.pathname.startsWith("/api/media/")) {
    event.respondWith(cacheFirst(request, MEDIA_CACHE).catch(() => Response.error()));
    return;
  }

  // Read-only board/day/calendar: network-first, fall back to the last copy so
  // the child still sees today's schedule and board offline.
  if (
    /^\/api\/(aac\/board|schedule\/(day|calendar))/.test(url.pathname) &&
    request.method === "GET"
  ) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) caches.open(DATA_CACHE).then((c) => c.put(request, res.clone()));
          return res;
        })
        .catch(() => caches.open(DATA_CACHE).then((c) => c.match(request))),
    );
    return;
  }

  if (url.pathname.startsWith("/api/")) return; // network-only

  // App shell / static / symbols: cache-first, fall back to index.html for navs.
  event.respondWith(
    caches.match(request).then(
      (hit) =>
        hit ||
        fetch(request)
          .then((res) => {
            const copy = res.clone();
            caches.open(SHELL_CACHE).then((c) => c.put(request, copy));
            return res;
          })
          .catch(() => (request.mode === "navigate" ? caches.match("/index.html") : Response.error())),
    ),
  );
});
