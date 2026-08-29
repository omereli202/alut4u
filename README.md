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
./.conda/bin/python -m app            # from ./backend, or:
cd backend && flask --app app run --debug --port 8000
```

Open http://localhost:8000 — Flask serves both the API and the `frontend/`
static app.

## Tests & lint

```bash
cd backend
ruff check .
ruff format --check .
pytest
```

## Deployment

Railway builds from the repo root using `Procfile`. Push to `dev` → deploys to
the dev environment; fast-forward `main` → deploys to production. Migrations in
`supabase/migrations/` are applied by CI (`.github/workflows/ci.yml`) before the
deploy is promoted.

## Repo layout

```
backend/      Flask app (app factory, api/, repositories/, services/, schemas/)
frontend/     PWA — static, served by Flask
supabase/     SQL migrations + seed data
docs/         architecture, schema, accessibility, kiosk setup, privacy, roadmap
```
