# Roadmap

The authoritative phase plan. Mirrors the approved implementation plan.

## Locked decisions

| Area | Decision |
|---|---|
| Language | Hebrew only, RTL. No i18n layer. |
| Tenancy | 1 caregiver → many children. |
| Data path | Everything through Flask. Browser holds no Supabase key. |
| Offline | PWA. AAC + schedule work with no network. |
| Design | Google Stitch generates screens → converted to RTL + accessible components. |
| Voice | Azure Speech `he-IL` neural TTS + caregiver recordings. No cloning. |
| Device | Kiosk-style shared tablet. One sign-in, no session expiry, PIN → Caregiver Mode. |
| Market | Worldwide (Hebrew speakers). GDPR + COPPA in scope. |
| Icons | Bundled symbol library + caregiver uploads. |
| First run | Starter board templates (2–3 levels). |
| Notifications | In-app queue only. |
| Billing | Not in MVP; schema stays migration-friendly for it. |

## Cut from the original spec (privacy)

- **Photo memory/puzzle games** — cut. Calming Zone uses a non-personal library.
- **Whisper reading verification** — cut. Reading practice is caregiver
  marks-pass/fail; no child audio recorded or transmitted.
- **Kept, consent-gated:** caregiver voice recordings (needs `voice_consent_at`).
- **Kept:** behavior/progress history (token log, completions, verdicts).

## Phases

| # | Name | Outcome |
|---|---|---|
| 0 | Scaffolding | ✅ Repo, Flask factory, config, health check, CI, deploy config. |
| 1 | Foundation | ✅ Auth via Flask, device sessions + revocation, PIN + lockout, children CRUD, module toggles, all RLS + cross-tenant test, versioned consent flow, account export + hard-delete, rate limiting, usage counters, caregiver UI (onboarding / dashboard / PIN gate). Media pipeline deferred to Phase 2 (nothing to store yet). **← current** |
| 2 | AAC → **first release** | Grid 2×2–5×5, sentence bar, tap-to-speak (pre-generated audio), categories, symbol library w/ Hebrew search, card editor, starter templates, Azure TTS w/ hash cache, media pipeline (`/api/media/<id>`), full offline. |
| 3 | Schedule | Daily list, "where are we now" focus view + checkmark, read-day-aloud, monthly calendar, offline completion via outbox. |
| 4 | Tokens & rewards | `token_transactions` source of truth, caregiver awards, reward store, redemption → pending → in-app approval queue. |
| 5 | Calming zone | Audio player (no autoplay/flashing), generic sensory puzzles from bundled images. |
| 6 | AI social stories | OpenAI interview agent, schema-enforced JSON, per-page image gen, reader in User Mode. |
| 7 | Reading & writing | Graded texts, read-aloud, caregiver pass/fail (no STT), writing w/ Hebrew spell-check, auto token award. |
| 8 | Hardening & launch | AI quotas enforced, monitoring, load test, retention purge, a11y audit, legal review, billing. |

## Blockers (owner: user)

1. Symbol library licence — Mulberry Symbols (CC BY-SA) recommended over ARASAAC (non-commercial).
2. Google Stitch exports — AAC board, sentence bar, caregiver dashboard, card editor.
3. Confirm market = Hebrew speakers globally (not multi-language).
4. Accounts: GitHub, 2× Supabase (EU region), Railway (2 envs), Azure Speech.
5. Legal review before public launch (minors' data, worldwide).
