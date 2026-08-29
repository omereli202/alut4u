# REST API

Base path `/api`. JSON in/out. Auth is a signed HttpOnly cookie
(`alut4u_sid`) — send `credentials: "include"`; no tokens in JS.

Error shape: `{ "error": "<code>", "detail"?: "<human string>" }`.

Guards: **S** = valid session required · **C** = Caregiver Mode (live PIN
elevation) required.

## Auth & session — `/api/auth`

| Method | Path | Guard | Notes |
|---|---|---|---|
| POST | `/signup` | — | `{email, password, display_name, accept_terms:true}` → 201 + sets cookie, records `terms` consent. Rate-limited. |
| POST | `/login` | — | `{email, password}` → sets cookie. Rate-limited. |
| POST | `/logout` | S | revokes the device session, clears cookie. 204. |
| GET | `/session` | S | `{caregiver_id, mode, elevated_until, onboarding:{needs_pin,needs_terms,voice_consent}}` |
| PUT | `/pin` | S | set PIN. Onboarding: allowed. Changing an existing PIN: needs **C**. Rejects weak PINs. 204. |
| POST | `/pin` | S | verify PIN → grants Caregiver Mode. 429 `pin_locked` after 5 fails (60s→5m→15m). Rate-limited. |
| DELETE | `/pin/elevation` | S | drop back to User Mode. 204. |
| POST | `/terms` | S | `{accept:true}` re-records terms consent (version bump). 204. |
| POST | `/voice-consent` | C | `{accept:true}` → sets `voice_consent_at`, records consent. 204. |
| GET | `/devices` | C | signed-in devices (no token columns). |
| DELETE | `/devices/<id>` | C | revoke a device session. 204. |

## Children & modules — `/api/children`

| Method | Path | Guard | Notes |
|---|---|---|---|
| GET | `` | S | `{children:[…]}` active children (User Mode needs this). |
| POST | `` | C | `{name, consent_basis, birth_date?, avatar_seed?, parental_consent_attested?}`. `professional_with_parental_consent` requires the attestation → records a `professional_attestation` consent row. 201. |
| GET | `/<id>` | S | one child. 404 if not the caregiver's (RLS). |
| PATCH | `/<id>` | C | `{name?, birth_date?, avatar_seed?}`. |
| DELETE | `/<id>` | C | soft delete (`is_active=false`). 204. |
| GET | `/<id>/modules` | S | the 6 `*_enabled` booleans. |
| PUT | `/<id>/modules` | C | partial patch of the 6 booleans. |

## AAC board — `/api/aac`

| Method | Path | Guard | Notes |
|---|---|---|---|
| GET | `/board?child_id=` | S | `{categories:[…], cards:[…]}` — the whole board in one call. |
| POST | `/categories` | C | `{child_id, name, color?}` |
| PATCH | `/categories/<id>` | C | `{name?, color?}` |
| DELETE | `/categories/<id>` | C | cards keep their data, lose the link. |
| PUT | `/categories/order` | C | `{child_id, order:[id,…]}` |
| POST | `/cards` | C | `{child_id, label, tts_text?, category_id?, symbol_id? \| icon_asset_id?}`. Pre-generates TTS. |
| GET | `/cards/<id>` | S | one card. |
| PATCH | `/cards/<id>` | C | any card field + `audio_asset_id`. Regenerates TTS if the spoken text changed and there's no caregiver audio. |
| DELETE | `/cards/<id>` | C | 204 |
| PUT | `/cards/order` | C | `{child_id, order:[id,…]}` |

## Symbols — `/api/symbols`

`GET /api/symbols?q=<hebrew>` → `{symbols:[…]}` (bundled library; empty `q` browses).

## Media — `/api/media`

| Method | Path | Guard | Notes |
|---|---|---|---|
| POST | `` | C | multipart `kind` (`card_icon`/`card_audio`/`schedule_icon`/`rule_audio`), `child_id`, `file`. Images re-encoded; audio needs voice consent. → `{id, url, mime, bytes}` |
| GET | `/<id>` | S | the stable URL. Streams bytes, `Cache-Control: immutable`, sha256 `ETag`, `If-None-Match` → 304. Tenant-scoped (shared TTS-cache assets readable by any session). |

## Tokens, rules & rewards — `/api/tokens`

`token_transactions` is the ledger (source of truth); `token_balances` is a
trigger-maintained total. Redeeming **holds** the tokens immediately; rejecting
a request refunds them.

| Method | Path | Guard | Notes |
|---|---|---|---|
| GET | `/rules?child_id=` | S | behavior rule cards |
| POST/PATCH/DELETE | `/rules[/<id>]` | C | pre-generates TTS from `body` (or `title`); `PUT /rules/order` |
| GET | `/balance?child_id=` | S | `{balance, transactions:[…]}` |
| POST | `/award` | C | `{child_id, amount, reason?}` — negative amount removes tokens |
| GET | `/rewards?child_id=[&all=1]` | S | active only in User Mode; `&all=1` in Caregiver Mode includes inactive |
| POST/PATCH/DELETE | `/rewards[/<id>]` | C | `PUT /rewards/order` |
| POST | `/redeem` | S | `{child_id, reward_id}` — checks balance, creates a pending redemption + a hold transaction |
| GET | `/redemptions?child_id=` | S | that child's redemption history |
| GET | `/queue` | C | all pending redemptions across the caregiver's children |
| POST | `/redemptions/<id>/approve` | C | · | POST | `/redemptions/<id>/reject` | C | refunds |

## Schedule — `/api/schedule`

| Method | Path | Guard | Notes |
|---|---|---|---|
| GET | `/day?child_id=&date=` | S | `{items:[…]}` for that date (ordered). User Mode uses this. |
| POST | `/items` | C | `{child_id, the_date, title, start_time?"HH:MM", symbol_id?\|icon_asset_id?, sort_order?}`. Pre-generates TTS. |
| PATCH | `/items/<id>` | C | any item field; regenerates TTS if `title` changes. |
| DELETE | `/items/<id>` | C | 204 |
| PUT | `/items/order` | C | `{child_id, order:[id,…]}` |
| POST | `/toggle` | S | `{item_id, completed, idempotency_key?}` — mark done/undone. **Idempotent** (the offline outbox replays it). |
| POST | `/copy-day` | C | `{child_id, from_date, to_date}` → `{copied:N}` (completion reset). |
| GET | `/calendar?child_id=&from=&to=` | S | `{events:[…]}` in the date range. |
| POST | `/events` | C | `{child_id, event_date, title, note?, symbol_id?\|icon_asset_id?}` |
| PATCH | `/events/<id>` | C | · | DELETE | `/events/<id>` | C | 204 |

## Board templates — `/api/children/board-templates`

`GET` → `{templates:[{id,name_he,level,description_he}]}` (S). Pass
`board_template_id` to `POST /api/children` to seed the new child's board.

## Social stories — `/api/stories`

| Method | Path | Guard | Notes |
|---|---|---|---|
| POST | `/chat` | C | `{child_id, messages:[{role,content}]}` → `{reply, ready}` — the interview agent |
| POST | `/compose` | C | `{child_id, messages}` → composes the story, generates a per-page illustration + read-aloud audio, saves. Counts against the monthly AI quota (429 `quota_exceeded`). |
| GET | `?child_id=` | S | `{stories:[{id,title,created_at}]}` |
| GET | `/<id>` | S | full story: `{title, protagonist, pages:[{text, image_url, audio_url}]}` |
| DELETE | `/<id>` | C | 204 |

Without an OpenAI key a deterministic stub runs the same flow (3-question
interview → 5-page templated Hebrew story → SVG illustrations).

## Account (GDPR) — `/api/account`

| Method | Path | Guard | Notes |
|---|---|---|---|
| GET | `/export` | C | JSON attachment: caregiver, children, module_settings, consent_records, devices, usage_counters. (Media bundle added in Phase 2.) |
| DELETE | `` | C | `{confirm:"DELETE"}` → deletes the auth user + cascade, clears cookie. 204. |

## Health — `/api/health`

`GET /api/health` → `{status, env, version}`. `?deep=1` also pings Supabase
(503 if unreachable).
