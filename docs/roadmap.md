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
| 1 | Foundation | ✅ Auth via Flask, device sessions + revocation, PIN + lockout, children CRUD, module toggles, all RLS + cross-tenant test, versioned consent flow, account export + hard-delete, rate limiting, usage counters, caregiver UI (onboarding / dashboard / PIN gate). |
| 2 | AAC → **first release** | ✅ Grid 2–5 cols + sentence bar + tap-to-speak (pre-generated audio, offline via SW media cache), categories, bundled symbol library (**Mulberry Symbols swap in progress** — 26/36 core ids live, see blocker 1) w/ Hebrew search, card editor (symbol / icon-upload / audio-upload / record), 3 starter templates, `/api/media/<id>` pipeline, TTS hash cache. Azure adapter written; **real he-IL neural voice live on dev since 2026-09** (silent stub still used wherever no key is configured, e.g. local dev/CI). |
| 3 | Schedule | ✅ Daily list, "where are we now" focus view + big checkmark, read-the-day-aloud, monthly calendar, schedule editor, offline task completion via the outbox. |
| 4 | Tokens & rewards | ✅ Behavior rule cards, token ledger + trigger balance, caregiver awards, reward store, redemption → held → approval queue + dashboard badge; reject refunds. |
| 5 | Calming zone | ✅ Sound player (4 bundled ambient loops — **placeholder** procedural WAVs), guided-breathing circle (reduced-motion aware), calm memory game from the symbol set. Purely client-side; no autoplay, no flashing. |
| 6 | AI social stories | ✅ Caregiver chats with a five-slot interviewer agent → a writer → SLP-reviewer → illustrator crew composes a structured, reviewed story JSON. Compose saves the **reviewed text + read-aloud immediately**; illustrations fill in afterwards one page per request (`/illustrate`), so it never blocks on the image model. Child reads it in User Mode (page-turner). Gemini adapter written (four structured-output calls + `gemini-2.5-flash-image`, models env-configurable); **deterministic stub** runs the same shape without a key. LLM usage checked at compose, images metered per page. |
| 7 | Reading & writing | ✅ Bundled graded Hebrew reading texts (3 levels, w/ generated read-aloud); caregiver marks pass/fail via an inline PIN gate → auto-awards tokens (no STT). Writing practice: copy/spell a target, lenient Hebrew check server-side (niqqud / final-forms / punctuation ignored) → self-serve token on success. |
| 8 | Hardening & launch | ✅ *(code parts)* AI/TTS quotas enforced everywhere (TTS degrades silently, images hard-fail), atomic usage RPC, structured JSON logs + `X-Request-Id` + optional Sentry, CSP/HSTS/security headers (Caddy + Flask), retention sweep script (18mo warn / 24mo purge), load-test script, CI adds pip-audit + security-header + axe checks. Remaining are non-code: legal review, billing, prod keys, real-device a11y/offline — see `docs/launch-checklist.md`. **← current** |

## Blockers (owner: user)

1. **Symbol library — in progress.** Mulberry Symbols (CC BY-SA 4.0) licensed
   and being ingested via `scripts/mulberry_manifest.py` +
   `scripts/build_symbols.py`: of the 36 core-vocabulary ids, 26 now ship real
   Mulberry artwork (`0011_mulberry_symbols.sql`), 10 keep the original emoji
   placeholder where no adequate Mulberry equivalent exists (reviewed by hand
   via a published Artifact, not auto-picked). ~2,955 more Mulberry concepts
   are staged in the manifest as `pending`, to be labeled in Hebrew and
   reviewed in batches — see `docs/symbols.md`.
2. **Cloud Supabase + Azure Speech keys** — set on the Railway `alut4u-backend`
   service per env (`docs/deployment.md`). Both live on **dev** since
   2026-09; **prod is still unset**, and `require_production_secrets()` now
   refuses to boot without an Azure key, so this must happen before promotion.
3. Google Stitch exports — replace the plain Phase 1/2 UI styling.
4. Confirm market = Hebrew speakers globally (not multi-language).
5. Real-device offline test of the AAC board (airplane mode).
6. Legal review before public launch (minors' data, worldwide).
