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

## Supabase projects

Two separate projects, **both must be in an EU region** (`CLAUDE.md`'s
non-negotiable #2) — `supabase projects create --region eu-central-1` (or any
`eu-*` except `eu-west-2`, which is UK, not EU). Current refs:

| env | ref | region |
|---|---|---|
| dev | `pqyndzbtmrwsgnknmfdv` | ⚠️ `ap-northeast-1` — pre-dates the EU requirement being enforced, not yet moved (low priority: synthetic data, no compliance exposure) |
| production | `qtuczqiijdhqgpcslvzd` | `eu-central-1` (recreated 2026-09-11) |

**Migrations**: `supabase db push --db-url "postgresql://postgres:<pw>@db.<ref>.supabase.co:5432/postgres"`,
or `supabase link --project-ref <ref>` (prompts for the DB password once,
caches it) then `supabase db push`. Nothing applies these automatically —
`scripts/release.sh` is not wired into either Dockerfile or CI, and neither
Railway environment sets `SUPABASE_DB_URL`. **Always confirm which branch is
checked out first** — the migrations directory differs between `dev` (has
`0012_pcs_symbols.sql`, proprietary, dev-only) and `main` (doesn't); pushing
from the wrong branch ships the PCS set to whichever project you're pointed
at. `supabase migration list` (once linked) shows what's actually applied.

**Auth + Storage config**: `supabase/config.toml`'s `[auth]` and `[storage]`
sections are the source of truth — push them to a project with
`supabase config push --project-ref <ref>` instead of configuring by hand in
the dashboard (both `enable_confirmations = false` and the `media`/`tts`
bucket definitions live there now; hand-configuring once and never scripting
it is exactly how production shipped broken — see the 2026-09 postmortem
below). `site_url` is parameterized as `env(SUPABASE_AUTH_SITE_URL)` — export
the right URL before pushing to a specific project, e.g.
`SUPABASE_AUTH_SITE_URL=https://alut4u-web-production.up.railway.app`.
The password-reset email works the same way, with one deliberate split: the
Hebrew `[auth.email.template.recovery]` code template applies on any
`config push` regardless of SMTP, but `[auth.email.smtp].enabled` ships
**`false`** in `config.toml` on purpose — confirmed empirically that
`enabled = true` with the `SUPABASE_SMTP_*` vars unset does not fall back to
anything, it 500s on every outbound email (GoTrue tries to dial the empty
host). So going live on real SMTP is two manual steps, not one: export
`SUPABASE_SMTP_HOST` / `_USER` / `_PASS` / `_ADMIN_EMAIL` (see `.env.example`)
**and** flip `enabled = true` in `config.toml` before that `config push` —
do this only once a real SMTP provider + verified sending domain exist (see
`docs/launch-checklist.md`). Left at the default, a project still gets the
Hebrew code template, just delivered through Supabase's shared sender
(2 emails/hour — fine to verify the flow works, not production-safe).
`supabase link` and `db query --linked --file <path>` both work through the
Management API (no DB password needed) — useful for one-off corrective SQL
against a linked project.

Both `link` and `config push`/`db push` operate on whatever project the CLI
is currently linked to (`supabase/.temp/project-ref`, gitignored) — **this
repo's working tree is typically shared across sessions**, so relink back to
`dev` when done with a one-off operation against another project.

<details>
<summary>2026-09 postmortem: why production got rebuilt</summary>

The original production project (`gxuulzysjufvtimbyrgm`) was in
`ap-northeast-1`, not EU — a region mismatch discovered only after signup
started failing with `email confirmation is not supported`
(`enable_confirmations` was never pushed to the cloud project; only
`config.toml`'s local-stack default existed). The buckets had the identical
gap days earlier — created by hand, never scripted. Fixing the region meant
recreating the project (Supabase doesn't migrate a project's region), which
surfaced a second issue: a `db push` run from a `dev` checkout applied
`0012_pcs_symbols.sql` to the new prod project before anyone switched to
`main`, briefly putting the proprietary PCS/Boardmaker set in a production
database (never live — no real signups existed yet). Cleaned up by re-running
`main`'s `0029_mainonly_mulberry_symbols_no_pcs.sql` directly against the new
project via `db query --linked`. `config push` closes the actual gap for
both auth and storage going forward.

</details>

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
