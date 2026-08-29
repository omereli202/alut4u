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
| 2 | AAC → **first release** | ✅ Grid 2–5 cols + sentence bar + tap-to-speak (pre-generated audio, offline via SW media cache), categories, bundled symbol library (**placeholder emoji set** — swap for Mulberry) w/ Hebrew search, card editor (symbol / icon-upload / audio-upload / record), 3 starter templates, `/api/media/<id>` pipeline, TTS hash cache. Azure adapter written; **silent stub** runs until an Azure key is set. |
| 3 | Schedule | ✅ Daily list, "where are we now" focus view + big checkmark, read-the-day-aloud, monthly calendar, schedule editor, offline task completion via the outbox. |
| 4 | Tokens & rewards | ✅ Behavior rule cards, token ledger + trigger balance, caregiver awards, reward store, redemption → held → approval queue + dashboard badge; reject refunds. |
| 5 | Calming zone | ✅ Sound player (4 bundled ambient loops — **placeholder** procedural WAVs), guided-breathing circle (reduced-motion aware), calm memory game from the symbol set. Purely client-side; no autoplay, no flashing. |
| 6 | AI social stories | ✅ Caregiver chats with an interview agent → structured story JSON → per-page illustration + pre-generated read-aloud → saved; child reads it in User Mode (page-turner). OpenAI adapter written (models env-configurable); **deterministic stub** runs without a key. AI usage counts against monthly quotas. **← current** |
| 7 | Reading & writing | Graded texts, read-aloud, caregiver pass/fail (no STT), writing w/ Hebrew spell-check, auto token award. |
| 8 | Hardening & launch | AI quotas enforced, monitoring, load test, retention purge, a11y audit, legal review, billing. |

## Blockers (owner: user)

1. **Symbol library licence** — the shipped set is placeholder emoji SVGs.
   Mulberry Symbols (CC BY-SA) recommended over ARASAAC (non-commercial). When
   licensed: drop real SVGs into `frontend/assets/symbols/` (same ids), add a
   migration updating `symbols`, re-run `scripts/build_symbols.py`.
2. **Cloud Supabase + Azure Speech keys** — set on the Railway `alut4u-backend`
   service per env (`docs/deployment.md`). Until then prod/dev run as
   `env: development` with no backend features, and TTS uses the silent stub.
3. Google Stitch exports — replace the plain Phase 1/2 UI styling.
4. Confirm market = Hebrew speakers globally (not multi-language).
5. Real-device offline test of the AAC board (airplane mode).
6. Legal review before public launch (minors' data, worldwide).
