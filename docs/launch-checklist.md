# Launch checklist

What has to be true before `main` is promoted and the product is opened to real
families. Grouped by owner.

## Engineering — done in code

- [x] RLS on every table + an automated cross-tenant isolation test (Phase 1)
- [x] Auth: server-side GoTrue, encrypted tokens at rest, argon2 PIN + lockout,
      per-device revocation
- [x] GDPR: versioned consent records, `/api/account/export`, hard delete
- [x] AI/TTS monthly quotas enforced (`services/quotas.py`) — TTS degrades
      silently, image generation hard-fails 429
- [x] Rate limiting on auth, media upload, and the AI endpoints
- [x] Structured JSON logs + `X-Request-Id` on every response; optional Sentry
      via `SENTRY_DSN`
- [x] Security headers: CSP / HSTS / X-Frame-Options / Permissions-Policy (Caddy
      for the origin, Flask for the API)
- [x] Retention sweep: `scripts/retention_purge.py` (warn at 18 mo idle, purge
      at 24) — **must be scheduled** (see below)
- [x] Load-test script: `scripts/loadtest.py`
- [x] CI: lint, ruff-format, `pip-audit`, RLS assertion, full pytest against a
      real Supabase, both Docker images + split-topology smoke, security-header
      check, axe accessibility check on the auth screen

## Engineering — before promotion

- [ ] Run `scripts/loadtest.py` against the **dev Railway** deployment; confirm
      p95 < 400 ms on the read paths under expected concurrency
- [ ] Schedule the retention sweep — a Railway cron service running
      `python scripts/retention_purge.py --apply` weekly (dev: `--apply` off /
      dry-run only until there is real data)
- [ ] Manual accessibility pass on a real tablet: keyboard-only, 200 % zoom,
      VoiceOver (iPadOS), `prefers-reduced-motion`, 60 px touch targets in User
      Mode, contrast on the final Stitch palette
- [ ] Real-device airplane-mode test of AAC board + schedule (offline)
- [ ] Kiosk test: iPadOS Guided Access / Android Screen Pinning per
      `docs/kiosk-setup.md`
- [ ] Point `SENTRY_DSN` at a real project; verify an error surfaces there
- [ ] Replace placeholder assets: symbol library (licensed set — Mulberry
      Symbols / CC BY-SA recommended), calming audio loops, PWA icons
- [ ] Final visual styling — the Stitch export landed
      (`docs/design/stitch-export/`) and the foundation pass is done: tokens,
      shared components (buttons/badges/tabs/inputs), the icon sprite (24
      emoji controls → SVG, `scripts/build_icons.py`), and the `dialog`
      component (native `<dialog>`, replaces all 6 `confirm()`/`prompt()`
      sites). Still open: a per-screen layout pass for the ~24 screens the
      export didn't cover (home, dashboard, auth, PIN pad, calming, stories,
      reading/writing — see the export README's "not exported" list) and the
      export's internal inconsistencies flagged in that README's "watch-outs"
      section; the unified `pin` component (keypad + inline); drop dead
      `router.js`.

## Product / ops — outside code

- [ ] **Legal review** of the privacy policy, terms of service, and DPA by a
      lawyer — worldwide product handling minors' data (GDPR + COPPA). Do not
      launch without this. See `docs/privacy.md`.
- [ ] Supabase projects in an **EU region**, one per environment, never shared
- [ ] Set the backend env vars per environment (`docs/deployment.md`), then flip
      `APP_ENV=production` on prod
- [ ] OpenAI + Azure Speech accounts with billing; confirm the current model ids
      for `OPENAI_CHAT_MODEL` / `OPENAI_IMAGE_MODEL`
- [ ] Billing / subscriptions (Stripe or Paddle) — schema is migration-friendly
      for it but nothing is wired yet
- [ ] Uptime monitoring hitting `/api/health?deep=1` (e.g. a Railway healthcheck
      is already configured; add an external monitor too)
- [ ] Support inbox / process for data-subject requests and account issues
- [ ] Decide the retention windows for your jurisdiction (defaults:
      `RETENTION_WARN_DAYS=540`, `RETENTION_PURGE_DAYS=730`)
