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
- AI (phase 6 only): OpenAI. Structured output enforced by schema, not prompt.
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
supabase/migrations/   numbered SQL, applied by CI via Supabase CLI
docs/
scripts/               release.sh and other CI/deploy helpers
```

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
  Supabase, Azure and OpenAI — no live calls in the test suite.
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

**Phase 0 — scaffolding.** Building repo structure, Flask app factory, config,
health check, CI, deploy config. Feature modules come later; see `docs/roadmap.md`
for phase order (Foundation → AAC → Schedule → Tokens → Calming → AI Stories →
Reading/Writing → Hardening).

## Known blockers (waiting on the user)

- Symbol library licence choice (Mulberry Symbols / CC BY-SA recommended over
  ARASAAC's non-commercial licence).
- Google Stitch screen exports for the AAC board and caregiver dashboard.
- External accounts: GitHub, two Supabase projects (EU), Railway (2 envs),
  Azure Speech.
