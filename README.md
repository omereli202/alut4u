# alut4u — AAC & Support Platform

Accessible communication and daily-support platform for children on the autism
spectrum and their caregivers. Hebrew, RTL, offline-capable PWA.

- **User Mode** — simplified, high-contrast interface the child uses on a
  locked-down tablet. Shows only the modules the caregiver has enabled.
- **Caregiver Mode** — PIN-protected dashboard for configuring modules, editing
  AAC cards, managing schedules, tokens and (later) AI social stories.

## Status

Phase 0 — scaffolding. See `docs/roadmap.md` for the full phase plan and
`docs/architecture.md` for how the pieces fit together.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | HTML5 / CSS3 / vanilla ES modules, PWA (service worker + IndexedDB) |
| Backend | Python 3.12 + Flask, REST under `/api` |
| Data | Supabase (Postgres + Auth + Storage), EU region, RLS-enforced |
| Voice | Azure Speech `he-IL` neural TTS + caregiver recordings |
| AI (phase 6) | OpenAI — social-story agent + image generation |
| Hosting | Railway — `dev` env ← `dev` branch, `production` env ← `main` branch |

## Local development

```bash
# 1. Python env (a local conda env already exists at ./.conda)
./.conda/bin/pip install -e "backend[dev]"

# 2. Environment
cp .env.example .env         # fill in Supabase + Azure values

# 3. Run
./scripts/dev.sh                       # one Flask process, API + PWA on :8000
```

Open http://localhost:8000. Locally one Flask process serves both the API and
the `frontend/` PWA (`SERVE_FRONTEND=1`). **In production these are two Railway
services** — a Caddy frontend that reverse-proxies `/api/*` to a private
backend. See `docs/deployment.md`.

## Tests & lint

```bash
cd backend
ruff check .
ruff format --check .
pytest
```

## Deployment

Railway project `alut4u`, two environments by branch (`dev` → dev,
`main` → production). Each environment runs two services: `alut4u-web` (Caddy —
static PWA + `/api/*` proxy, the only public one) and `alut4u-backend`
(Flask, private). Each builds from its own `Dockerfile`
(`frontend/`, `backend/`). Migrations in `supabase/migrations/` are applied by
CI. Full details: `docs/deployment.md`.

## Repo layout

```
backend/      Flask app (app factory, api/, repositories/, services/, schemas/)
frontend/     PWA — static, served by Flask
supabase/     SQL migrations + seed data
docs/         architecture, schema, accessibility, kiosk setup, privacy, roadmap
```
