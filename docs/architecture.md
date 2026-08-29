# Architecture

## Request flow

```
Tablet (PWA — vanilla ES modules, service worker, IndexedDB)
   │  HttpOnly signed session cookie (session id only — no tokens in JS)
   ▼
Flask  (one Railway service: serves /api AND the static frontend/)
   │  per-request Supabase client carrying the caregiver's JWT
   ▼
Supabase — Postgres (RLS enforced) + Storage (private buckets)
   │
   └── Azure Speech (Hebrew TTS)   ·   OpenAI (Phase 6, stories)
```

One service, one deploy. Flask serving the static app is the simplest thing that
works for a solo developer and removes a cross-origin surface.

## Auth & session

The device is a kiosk and the browser must never hold a key, so we do **not**
use `supabase-js` in the client.

1. Flask calls Supabase Auth (GoTrue) server-side for sign-up / sign-in / reset.
2. On success Flask inserts a `device_sessions` row and sets a signed
   `HttpOnly; Secure; SameSite=Lax` cookie containing only the session id.
3. The Supabase **refresh token is stored encrypted** (Fernet,
   `SESSION_TOKEN_ENC_KEY`) in that row. Flask refreshes the access token
   transparently. Sessions are effectively indefinite and individually
   revocable — a lost tablet can be killed from another device.
4. **Every request builds a Supabase client authenticated as that caregiver's
   JWT.** Postgres RLS is therefore the real tenancy boundary, not application
   `WHERE` clauses.

### service-role usage

`app/services/supabase_client.py` exposes `service_client(operation)`, which
raises unless `operation` is in `ALLOWED_SERVICE_OPERATIONS` (sign-up, GDPR
erasure, TTS-cache writes, symbol-library reads, retention purge, board-template
seeding). Any new use is a security review.

## Caregiver Mode (PIN)

- `caregivers.pin_hash` — argon2. Never returned by any endpoint.
- `POST /api/auth/pin` — server-side verify, escalating lockout
  (5 fails → 60s → 5m → 15m), attempts logged to `audit_log`.
- Success grants a time-boxed elevation on the session (15-min idle timeout)
  that auto-drops back to User Mode.
- No default PIN — onboarding forces one.

## Offline

- **Stable media URLs.** Supabase signed URLs rotate → uncacheable. All media is
  fetched via `/api/media/<asset_id>`; Flask authorizes then streams/redirects.
  The service worker caches that stable key.
- **Pre-generated TTS.** On card save, Flask synthesizes and stores the audio
  immediately. Tap-to-speak plays a cached file — nothing is synthesized live,
  so speech works offline.
- **Shared TTS cache** keyed by `sha256(voice|rate|fmt|text)` — dedupes across
  all children; the main cost lever.
- **Outbox.** Schedule completions / token events / usage pings queue in
  IndexedDB with an idempotency key and flush in order on reconnect; the server
  dedupes.
- AI features are online-only with an explicit offline state.

## Frontend build

No bundler, no framework. `css/tokens.css` is the one place to restyle. Google
Stitch output goes through three passes before use: RTL conversion (logical
properties, `dir="rtl"`), token extraction, accessibility (focus rings, ARIA,
≥60px targets in User Mode, contrast, reduced-motion, no autoplay/flashing).

## Layout

See `CLAUDE.md` for the annotated directory tree and conventions.
