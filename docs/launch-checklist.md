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
- [ ] Replace placeholder assets: symbol library — core ids done (`main`: 35/35
      Mulberry, zero placeholder; `dev`: 34/36 Mulberry + PCS + 2 placeholders),
      ~1,960 more Mulberry concepts staged for review (`docs/symbols.md`). Still
      open: **PWA icons** — placeholder flat-blue squares; a real app-logo source
      is needed (`docs/design/stitch-export-2/` has the logo as a PNG mockup
      only, no SVG — not enough for crisp icons at multiple sizes).
- [ ] **Calming audio licence** — 5 of the 9 loops are synthesized (fine); 4
      (`fire` `forest` `brook` `birds`) are chosic.com downloads the owner has
      asserted are CC0. Confirm the chosic licence for all four before `main` —
      the `birds` file's ID3 still carries a `BurghRecords` copyright tag. If any
      is not usable, swap the source in `scripts/data/calming_sources/` or fall
      back to a synth track. See `frontend/assets/calming/LICENSE.md`.
- [x] **PCS / Boardmaker symbol set** — kept on `dev` only; **stripped from
      `main`** by `supabase/migrations/0029_mainonly_mulberry_symbols_no_pcs.sql`
      + `backend/tests/test_no_pcs_on_main.py` (CI guard). `main` ships 100 %
      Mulberry (CC BY-SA 4.0), 35 core ids, zero placeholder. The strip is
      main-only and regenerated at every promotion — the branches diverge
      permanently, by the owner's decision (2026-09-09). If the repo ever goes
      public, revisit: license Boardmaker or drop it from `dev` too.
- [ ] Final visual styling — two Stitch exports have landed
      (`docs/design/stitch-export/`, `docs/design/stitch-export-2/`). Done:
      tokens, shared components (buttons/badges/tabs/inputs/dialog/icon
      sprite, now 39 glyphs), the AAC board (card medallions, category tabs,
      sentence bar), the PIN inline gate (`pin.inline`), the boot/loading+
      error screen, shared states (offline banner, empty state, celebration
      state), and reading/writing/story-reader. Still open: User-Mode home
      (T1.3), caregiver dashboard (T1.4), AAC card form (T1.5), schedule
      editor (T2.4), calming module (T2.8–10), sign-in/up (T3.1–2), the full
      PIN keypad (`pin.keypad`, `views/pinpad.js` — only `pin.inline` has
      reference art so far) — none of these have reference art from either
      export yet. Both export READMEs' "watch-outs" sections have specifics
      to avoid reintroducing if a future export covers them. Drop dead
      `router.js`.

## Product / ops — outside code

- [ ] **Legal review** of the privacy policy, terms of service, and DPA by a
      lawyer — worldwide product handling minors' data (GDPR + COPPA). Do not
      launch without this. See `docs/privacy.md`.
- [ ] Supabase projects in an **EU region**, one per environment, never shared
- [ ] Set the backend env vars per environment (`docs/deployment.md`), then flip
      `APP_ENV=production` on prod
- [x] Azure Speech account with billing — key live on dev since 2026-09;
      **must be set on prod too before promotion**, `require_production_secrets()`
      now refuses to boot without it
- [ ] Google Gemini API key with billing (https://aistudio.google.com/apikey);
      confirm the current model ids for `GEMINI_CHAT_MODEL` / `GEMINI_IMAGE_MODEL`
- [ ] Billing / subscriptions (Stripe or Paddle) — schema is migration-friendly
      for it but nothing is wired yet
- [ ] Uptime monitoring hitting `/api/health?deep=1` (e.g. a Railway healthcheck
      is already configured; add an external monitor too)
- [ ] Support inbox / process for data-subject requests and account issues
- [ ] Decide the retention windows for your jurisdiction (defaults:
      `RETENTION_WARN_DAYS=540`, `RETENTION_PURGE_DAYS=730`)
