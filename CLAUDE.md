# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

An accessible AAC (Augmentative & Alternative Communication) and daily-support
platform for children on the autism spectrum and their caregivers. Hebrew-only,
RTL, offline-capable PWA. Intended to become a public product serving families
worldwide (Hebrew speakers).

Two faces:
- **User Mode** — what the child uses on a locked-down (kiosk) tablet. Only shows
  modules the caregiver enabled. High-contrast, large touch targets, no clutter.
- **Caregiver Mode** — behind a 4-digit PIN. Configure modules, edit AAC cards,
  manage schedules and tokens, run the AI story agent (phase 6).

Full plan: `docs/roadmap.md`. Architecture: `docs/architecture.md`. Schema:
`docs/schema.md`.

## Non-negotiable constraints

These came from explicit product decisions. Do not "improve" past them without
asking.

1. **The browser never holds a Supabase key.** All data access goes
   browser → Flask → Supabase. `frontend/` talks only to `/api/*`.
2. **RLS is the tenancy boundary, not app code.** Every request builds a
   Supabase client authenticated as the caregiver's JWT. The service-role key is
   used only for the narrow, explicitly-listed system operations in
   `app/services/supabase_client.py`. Every child-scoped table has an RLS policy
   through `children.caregiver_id = auth.uid()`.
3. **Hebrew only, RTL.** No i18n layer, no `t()` wrappers. Strings are Hebrew
   literals. CSS uses logical properties (`margin-inline-start`, not
   `margin-left`). `dir="rtl"` on `<html>`.
4. **Do not store family photos or the child's speech audio.** Server-side.
   Ever. Caregiver voice recordings ARE allowed but only after
   `caregivers.voice_consent_at` is set — the recording UI stays disabled until
   then.
5. **No Whisper / STT.** Reading practice is caregiver-marks-pass/fail. No audio
   recorded or transmitted for the child.
6. **Offline-first for AAC + schedule.** TTS audio is pre-generated on save (not
   synthesized at tap time). Media is served via stable `/api/media/<asset_id>`
   URLs so the service worker can cache them (Supabase signed URLs rotate and
   must not be cached).
7. **PIN is argon2-hashed, verified server-side only, never in a response body.**
   No default PIN — onboarding forces the caregiver to set one.
8. **Consent is a record, not a boolean.** Writes to `consent_records` with
   `terms_version`, timestamp, and context.

## Tech stack

- Backend: Python 3.12, Flask 3, gunicorn. REST under `/api`. `pydantic` for
  request/response schemas, `pydantic-settings` for config.
- Data: Supabase (Postgres + Auth + Storage), **EU region**.
- Voice: Azure Speech `he-IL` neural TTS (`he-IL-HilaNeural` default) +
  caregiver recordings via browser `MediaRecorder`.
- AI (phase 6 only): Google Gemini. Structured output enforced by schema, not
  prompt.
- Frontend: vanilla ES modules, no framework, no build step. PWA (service
  worker + IndexedDB outbox).
- Hosting: Railway. `dev` branch → dev environment, `main` branch → production.
  Two **separate** Supabase projects — never share one between environments.

## Repo layout

```
backend/app/
  __init__.py        app factory (create_app)
  config.py          Settings (env-driven)
  auth/              sessions, PIN, device revocation
  api/               blueprints: health, children, modules, aac, media, account
  repositories/      ALL database access lives here — tenancy-enforced.
                     No raw Supabase queries in api/ routes.
  services/
    supabase_client.py   per-request user client + narrow service client
    tts/                 provider interface + azure_he.py adapter
    storage.py           Supabase Storage wrapper
    quotas.py            per-caregiver monthly usage enforcement
  schemas/           pydantic models
frontend/
  index.html  manifest.webmanifest  sw.js
  css/        tokens.css (design tokens) + base + components
  js/         app, router, api, db (IndexedDB), outbox
  js/modes/   user/  caregiver/
  js/modules/ aac/  (schedule/, rules/, calming/, stories/, reading/ later)
backend/Dockerfile     backend image (gunicorn, API only)
frontend/Dockerfile    frontend image (Caddy: static PWA + /api/* proxy)
frontend/Caddyfile     static serving + reverse_proxy to the backend
supabase/migrations/   numbered SQL, applied by CI via Supabase CLI
docs/
scripts/               dev.sh (one-process local), release.sh (CI migrations)
```

## Deployment

Railway project `alut4u`, two environments by branch (`dev`→`dev` env,
`main`→`production` env). **Each environment has two services:**

- `alut4u-web` — Caddy. Serves `frontend/` and reverse-proxies `/api/*` to the
  backend over Railway's private network. **The only public service.**
- `alut4u-backend` — gunicorn/Flask, API only, **no public domain**. Env
  `SERVE_FRONTEND=0`.

The browser sees one origin, so cookie auth + PWA + offline stay same-origin.
Locally, `scripts/dev.sh` collapses both into one Flask process
(`SERVE_FRONTEND=1`) — the split is production-only. Full details +
env-var checklist: `docs/deployment.md`.

`railway` CLI is authed locally: `railway environment <name>` switches env,
`railway logs -d/-b --service <svc>` for logs.

## Conventions

- **Database access only through `app/repositories/`.** A repository function
  takes the caller's identity and never trusts a caller-supplied
  `caregiver_id`/`child_id` without checking ownership. If you find a raw query
  in a route, that's a bug to fix, not a pattern to copy.
- **New tables need an RLS policy in the same migration.** A migration that adds
  a child-scoped table without `ENABLE ROW LEVEL SECURITY` + policy is
  incomplete.
- **Blueprints** are registered in `app/__init__.py`. One blueprint per resource,
  URL prefix `/api/<resource>`.
- **Config**: add a field to `Settings` in `config.py` and to `.env.example`.
  Never read `os.environ` directly outside `config.py`.
- **Frontend**: no new dependencies without discussion. No bundler. Keep modules
  small and single-purpose. All network calls go through `js/api.js`.
- **Secrets** never in code, tests, or fixtures. Tests use fakes/mocks for
  Supabase, Azure and Gemini — no live calls in the test suite.
- **Commits**: conventional-commit style (`feat:`, `fix:`, `chore:`, `docs:`).
  Work on a branch, never commit straight to `main`.

## Commands

```bash
# install (local conda env lives at ./.conda)
./.conda/bin/pip install -e "backend[dev]"

# run (serves API + frontend on :8000)
cd backend && ./../.conda/bin/flask --app app run --debug --port 8000

# lint + format check + tests — run before every commit
cd backend && ../.conda/bin/ruff check . && ../.conda/bin/ruff format --check . && ../.conda/bin/pytest

# new migration
supabase migration new <name>          # then edit supabase/migrations/*.sql
supabase db push                       # apply to the linked project
```

## Testing priorities

- **Cross-tenant isolation test is mandatory and must stay green.** Caregiver A
  must get 403/404 on every child-scoped endpoint for caregiver B's `child_id`.
- PIN: lockout escalation, elevation expiry, `pin_hash` never serialized.
- Offline (manual, real tablet): load board → airplane mode → tap cards → audio
  plays → build sentence → speaks → reconnect → outbox flushes without dupes.
- Accessibility: axe-core in CI; manual keyboard-only + 200% zoom +
  `prefers-reduced-motion` + 60px touch targets in User Mode.

## Current phase

**Phases 0–8 all built on `dev`.** All 6 feature modules (AAC, Schedule, Tokens
& rewards, Calming, AI stories, Reading & writing) are live in the User-Mode
home tiles and the caregiver dashboard. Hardening done (quotas, logging,
security headers, retention script, load test). `docs/roadmap.md` has the
per-phase detail; `docs/launch-checklist.md` has what's left before promotion.

`main` is still at Phase 1 — **nothing is promoted to production**; wait for the
user to say so (see the branch-promotion memory).

## Backend layout notes (post Phase 8)

- `services/quotas.py` — per-caregiver monthly caps, checked via the service
  role (no request context). TTS degrades silently on over-quota; image gen
  hard-fails 429.
- `services/ai/` — story agent: Gemini adapter (`gemini_story.py`, four
  structured-output calls + `gemini-2.5-flash-image`) + deterministic stub (no
  key).
- `services/retention.py` + `scripts/retention_purge.py` — inactivity sweep.
- `observability.py` — request IDs, JSON logs, Sentry, security headers.
- `services/hebrew.py` — lenient Hebrew compare for writing practice.

## Known blockers (waiting on the user)

- Symbol library — two sets now bundled:
  - Mulberry Symbols (CC BY-SA 4.0), ingested in batches (`docs/symbols.md`);
    34/36 core ids done. **This is the only set cleared for production.**
  - PCS / Boardmaker (`scripts/build_pcs_symbols.py`, ~4,560 symbols): a
    proprietary set imported from the owner's PowerPoint, bundled for **`dev`
    only**. `scripts/release.sh` blocks its migration on production. Still
    blocking `main` promotion — needs a Boardmaker licence or removal. See
    `frontend/assets/symbols/pcs/LICENSE.md`.
  Calming audio and PWA icons are still placeholders.
- Google Stitch screen exports (final visual styling). Brief is ready:
  `docs/design.md` (per-screen prompts + design system + post-export pipeline).
- Cloud Supabase (EU) + Azure Speech + Google Gemini keys — everything runs on
  stubs/local until these exist.
- Legal review before launch (minors' data, worldwide) — `docs/privacy.md`.
