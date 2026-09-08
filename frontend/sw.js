/* Service worker.
 *
 * - App shell + bundled symbols: cache-first, versioned (bump SHELL_CACHE).
 * - /api/media/<id>: cache-first in a separate, unversioned cache — the ids are
 *   content-addressed and immutable, so entries never go stale. This is what
 *   makes the AAC board (icons + pre-generated audio) work offline.
 * - Other /api/*: network-only.
 */

const SHELL_CACHE = "shell-v43"; // v43: ui.js — SYMBOLS_VERSION bumped to
// 20260914e; 268 new Mulberry symbols ingested (animals, transport, plants,
// planets, toys) — the symbol *files* changed, so the shell that references
// them must re-fetch (defeats Railway's per-node edge cache).
// v42: calming memory game — a found pair counts
// as 1 (was 0.5), and the "מצאת הכל!" win screen actually fires.
// v41: guided child-setup wizard — walks the
// caregiver through every module editor after creating a child (new
// /js/views/child-setup.js).
// v40: "המשימות שלי" — an 8th module: a personal
// checklist the child ticks off (offline via the outbox), a caregiver editor
// (curate tasks + attach a symbol + daily/one-off + reward size), and a
// PIN-released token reward when every task due today is done. pin-gate.js
// promoted from js/modules/learning/ to js/ (now shared by learning + tasks).
// v39: active-child profile switcher moved from the User Mode home to the
// Caregiver Mode dashboard (new /js/active-child.js).
// v38: "הפתקים שלי" (לוח הקלדה) — a 7th module:
// free-composition notes with 3 block styles (כותרת ראשית / משנה / טקסט), a
// per-child typeface (Rubik / Assistant / Heebo) + size default, an offline
// draft (kv) + coalesced outbox upsert, and a caregiver viewer with TTS /
// share / print / delete.
// v37: social stories — shared unlocked <audio> so the reader speaks page 1 on
// open (was blocked by autoplay policy), plus a caregiver "הקראה אוטומטית"
// toggle (stories_autoplay) and auto-scroll of the story-creation chat.
// v36: "קריאה והקלדה" — level selector per tab,
// ~10 bundled tasks/level, completed tasks don't repeat, tokens released every
// 3 tasks by caregiver PIN, and a caregiver task editor.
// v35: AAC categories nest (אוכל ‹ ארוחת בוקר ‹
// ביצת עין) and carry a picture — the child's board is a drill-down grid with a
// breadcrumb (separator chevron points into the trail), no tab strip; the
// caregiver editor gets a category tree + a category form (picture + parent +
// colour picker) + a per-card category picker; every category gets a distinct
// colour (auto-assigned server-side when not chosen).
// v34: caregiver dashboard — the per-child edit
// buttons and each editor's header now read "ערוך <module>" / "עריכת <module> — <name>".
// v33: schedule — caregiver can save the current
// day as a named default (template) and delete their saved ones.
// v32: rules — PIN-gated "שמרת על הכללים" claim
// button on the child's own rules page; once-a-day guard on the daily bonus.
// v31: schedule — full day list is the landing
// view, tap a row to focus one task, prev/next browse without completing;
// caregiver editor offers a starter-routine template on an empty day. Also
// rules — per-child daily bonus closing line + token history.
// v30: AAC card = full-bleed image + category-
// colour border; text-only cards are the word large; category tab = colour dot
// + name, active one scales up.
// v28: calming — זמזום רגוע louder (matched to
// the beds' RMS + a 220 Hz octave for small speakers), hum.wav regenerated.
// v27: calming — fire/forest/brook/birds are now real CC0 field recordings
// (chosic.com) not synth; drip→birds; .wav regenerated (cache-first here).
// v26: campfire + dripping-water synth loops.
// v25: calming — 5 new sounds, louder waves, one-screen sounds grid, breathing
// circle starts small + grows, spoken phase cues (calming/cues.js).
// v24: story-edit textareas now show their text.
// v23: social-story editor — caregiver text editing, closing "anything else?"
// question, no "מתי:" label.
// v22: social-story editor/reader + app.css — event-timing line and
// character-consistent illustrations.
// v21: ui.js's SYMBOLS_VERSION bumped to 20260914d —
// batches 2-5 landed (720 ids: verbs, body parts, clothes, fruit, vegetables,
// descriptive words). v20: ui.js changed — SYMBOLS_VERSION bumped to
// 20260914c and symbolUrl() now resolves bare `pcs-*` ids and subfoldered
// file_paths (the bundled Boardmaker/PCS set, dev only — see
// scripts/build_pcs_symbols.py). v19: ui.js's SYMBOLS_VERSION bumped to 20260914b —
// the first real Mulberry Symbols batch landed (26 ids swapped from the emoji
// placeholder to real artwork). v18: force-refresh clients stuck on a shell
// cached before the Caddyfile fix that put /css/* and /js/* under
// Cache-Control: no-cache — those clients' shell-v16 install had already
// precached CDN-edge-stale CSS/JS, and nothing about that fix touches sw.js's
// own bytes, so it'd never re-trigger on its own. Bumping this is what makes
// the browser re-run install() through the now-fixed origin path.
const SYMBOL_CACHE = "symbols-v1"; // AAC symbol images — deliberately separate from
// SHELL_CACHE (see symbolUrl()'s ?v= in ui.js): a shell bump must not evict every
// offline-cached symbol just because unrelated JS/CSS changed, and a symbol-set
// regeneration must not force every shell asset to re-download either.
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
  "/js/audio.js",
  "/js/db.js",
  "/js/outbox.js",
  "/js/session.js",
  "/js/active-child.js",
  "/js/ui.js",
  "/js/dialog.js",
  "/js/pin-gate.js",
  "/js/views/auth.js",
  "/js/views/pinpad.js",
  "/js/views/home.js",
  "/js/views/dashboard.js",
  "/js/views/child-setup.js",
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
  "/js/modules/calming/cues.js",
  "/js/modules/calming/memory.js",
  "/js/modules/stories/index.js",
  "/js/modules/stories/reader.js",
  "/js/modules/stories/editor.js",
  "/js/modules/learning/index.js",
  "/js/modules/learning/reading.js",
  "/js/modules/learning/writing.js",
  "/js/modules/learning/editor.js",
  "/js/modules/typing/index.js",
  "/js/modules/typing/editor.js",
  "/js/modules/typing/viewer.js",
  "/js/modules/typing/blocks.js",
  "/js/modules/typing/data.js",
  "/js/modules/typing/export.js",
  "/js/modules/tasks/index.js",
  "/js/modules/tasks/data.js",
  "/js/modules/tasks/editor.js",
  "/manifest.webmanifest",
  "/assets/icon-192.png",
  // Self-hosted Rubik — offline AAC/schedule must still render Hebrew (+ the
  // Latin digits in times, dates and the PIN keypad) in the real typeface.
  "/assets/fonts/rubik-hebrew-400.woff2",
  "/assets/fonts/rubik-hebrew-500.woff2",
  "/assets/fonts/rubik-hebrew-700.woff2",
  "/assets/fonts/rubik-latin-400.woff2",
  "/assets/fonts/rubik-latin-500.woff2",
  "/assets/fonts/rubik-latin-700.woff2",
  "/assets/fonts/rubik-latin-ext-400.woff2",
  "/assets/fonts/rubik-latin-ext-500.woff2",
  "/assets/fonts/rubik-latin-ext-700.woff2",
  // Typing-board alternate faces (Hebrew subset only) — must be precached or an
  // offline note silently falls back to system-ui when the child picks one.
  "/assets/fonts/assistant-hebrew.woff2",
  "/assets/fonts/heebo-hebrew.woff2",
  // Keep this in sync with ui.js's SPRITE_URL — a versioned URL is what
  // actually defeats Railway's CDN edge cache (see ui.js's comment); an
  // unversioned entry here would just precache a *different* URL than the
  // one icon() ever requests.
  "/assets/icons/sprite.svg?v=42",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
      // A transient failure here (one bad fetch during a rolling deploy)
      // used to fail silently — the install would abort with no trace, and
      // since the SW script is otherwise unchanged the browser wouldn't
      // retry until the next real edit. Surface it instead of swallowing it.
      .catch((err) => {
        console.error("[sw] install failed, shell cache may be incomplete:", err);
        throw err;
      }),
  );
});

self.addEventListener("activate", (event) => {
  const keep = new Set([SHELL_CACHE, SYMBOL_CACHE, MEDIA_CACHE, DATA_CACHE]);
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
    /^\/api\/(aac\/board|schedule\/(day|calendar)|typing\/(notes|settings)|tasks\/day)/.test(url.pathname) &&
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

  // AAC symbol images: own cache-first cache (see SYMBOL_CACHE above). The
  // ?v= in every symbolUrl() means a stale entry is simply never looked up
  // again, not that it needs active eviction.
  if (url.pathname.startsWith("/assets/symbols/")) {
    event.respondWith(cacheFirst(request, SYMBOL_CACHE).catch(() => Response.error()));
    return;
  }

  // App shell / static: cache-first, fall back to index.html for navs.
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
