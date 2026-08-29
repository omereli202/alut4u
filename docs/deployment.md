# Deployment

## Railway

One project — **alut4u** (`069b0afe-82c2-4b30-88a5-6d81bc13799f`), two
environments, branch-driven:

| Environment | Branch | Service | URL |
|---|---|---|---|
| `production` | `main` | `alut4u-web` | https://alut4u-web-production.up.railway.app |
| `dev` | `dev` | `alut4u-web` | https://alut4u-web-dev.up.railway.app |

- Build: root `Dockerfile` (`railway.json` → `builder: DOCKERFILE`).
- Healthcheck: `/api/health`.
- The container listens on `$PORT` (Railway sets `8080`); both service domains
  target port `8080`.
- Push to `dev` → dev deploy. Fast-forward `main` → production deploy.

## Environment variables

Not set yet — the app boots without them and `/api/health` passes, so both
environments deploy green during Phase 0/1 scaffolding.

**Before Phase 1 features work**, set per environment (Railway dashboard or
`railway variables --set K=V --environment <env> --service alut4u-web`):

| Var | dev | production |
|---|---|---|
| `APP_ENV` | `development` | `production` ← only after the Supabase vars below are set; it turns on the required-secrets check |
| `FLASK_SECRET_KEY` | random | random (different) |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_JWT_SECRET` | dev project | prod project |
| `SESSION_TOKEN_ENC_KEY` | Fernet key | Fernet key (different) |
| `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` | — | — |

Full list with descriptions: `.env.example`.

## CLI cheatsheet

```bash
railway environment dev|production      # switch linked env
railway logs -b                         # build logs
railway logs -d                         # deploy/runtime logs
railway status --json                   # project + env + service state
railway variables --environment dev --service alut4u-web
railway redeploy --service alut4u-web --environment dev
```

Note: `railway.json` "Config as Code" is deprecated by Railway (works until
2026-12-01); migrate to `.railway/railway.ts` before then.
