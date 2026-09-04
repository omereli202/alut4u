# Deployment

## Railway

One project — **alut4u** (`069b0afe-82c2-4b30-88a5-6d81bc13799f`), two
environments (`production` ← `main`, `dev` ← `dev`), **two services each**:

| Service | Root dir | Build | Public? | Healthcheck | Watch |
|---|---|---|---|---|---|
| `alut4u-web` (frontend) | `frontend/` | `frontend/Dockerfile` (Caddy) | **yes** — the only public entry point | `/` | `frontend/**` |
| `alut4u-backend` | `backend/` | `backend/Dockerfile` (gunicorn) | **no** — private network only | `/api/health` | `backend/**` |

Public URLs (both point at the **frontend** service):

| Environment | URL |
|---|---|
| `production` | https://alut4u-web-production.up.railway.app |
| `dev` | https://alut4u-web-dev.up.railway.app |

**Why split this way.** Caddy serves the static PWA and reverse-proxies
`/api/*` to `alut4u-backend.railway.internal:8080` over Railway's private
network. The browser only ever talks to one origin, so the HttpOnly session
cookie, the service-worker scope and offline caching all stay same-origin —
no CORS, no `SameSite=None`. The backend has no public domain at all.

- Both containers listen on `$PORT` (Railway sets `8080`).
- Frontend service var: `BACKEND_ORIGIN=http://alut4u-backend.railway.internal:8080`.
- `watchPatterns` mean a `backend/**`-only change redeploys just the backend, and vice-versa.
- No `railway.json` — each service auto-detects the `Dockerfile` in its root dir; healthcheck/root/watch are set on the service (see the GraphQL calls in git history or the dashboard).
- Push to `dev` → dev deploy. Fast-forward `main` → production deploy.

## Local development

`scripts/dev.sh` runs **one** Flask process that serves both the API and the
PWA (`SERVE_FRONTEND=1`) on `:8000` — the split only exists in production. To
exercise the real two-container topology locally:

```bash
docker build -t alut4u-backend ./backend
docker build -t alut4u-frontend ./frontend
docker network create alut4u-net
docker run -d --rm --network alut4u-net --name be -e PORT=8080 alut4u-backend
docker run -d --rm --network alut4u-net -p 8000:8080 \
  -e PORT=8080 -e BACKEND_ORIGIN=http://be:8080 alut4u-frontend
# http://localhost:8000  → PWA, with /api/* proxied to the backend container
```

## Environment variables

Not set yet — the app boots without them and `/api/health` passes, so both
environments deploy green during Phase 0/1 scaffolding.

**Before Phase 1 features work**, set on the **`alut4u-backend`** service per
environment (`railway variable set --service alut4u-backend --environment <env> "K=V"`):

| Var | dev | production |
|---|---|---|
| `APP_ENV` | `development` | `production` ← only after the Supabase vars below are set; it turns on the required-secrets check |
| `FLASK_SECRET_KEY` | random | random (different) |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_JWT_SECRET` | dev project | prod project |
| `SESSION_TOKEN_ENC_KEY` | Fernet key | Fernet key (different) |
| `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` | set ✓ (dev live since 2026-09) | **required** — `require_production_secrets()` now refuses to boot without it, so it must be set *before* promoting to `main` or the deploy healthcheck fails |

Production also: `JSON_LOGS=true`, and (recommended) `SENTRY_DSN`,
`GEMINI_API_KEY` + model ids.

The **`alut4u-web`** service only needs `BACKEND_ORIGIN` (already set).
Full list with descriptions: `.env.example`.

## Scheduled jobs

Add a Railway **cron** service (same repo, root `backend/`, same env as
`alut4u-backend`) running the retention sweep weekly:

```
python ../scripts/retention_purge.py --apply
```

Run it without `--apply` (dry-run) until production has real data. It warns
accounts idle `RETENTION_WARN_DAYS` and deletes accounts idle
`RETENTION_PURGE_DAYS` (GoTrue user + full cascade).

## CLI cheatsheet

```bash
railway environment dev|production                          # switch linked env
railway logs -b --service alut4u-backend                    # build logs
railway logs -d --service alut4u-web                        # deploy/runtime logs
railway status --json                                       # project + env + service state
railway variable list --service alut4u-backend --environment dev
railway redeploy --service alut4u-backend --environment dev
```

Service config (root dir, healthcheck, watch patterns) is set via the Railway
API, not a repo file — see `docs/deployment.md` history / the dashboard.
