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
| GET | `/board?child_id=` | S | `{categories:[…], cards:[…]}` — the whole board in one call. Categories nest: each has `parent_id` (null = top level) + its own `symbol_id`/`icon_asset_id`. |
| POST | `/categories` | C | `{child_id, name, color?, parent_id?, symbol_id? \| icon_asset_id?}`. `color` auto-assigned from a palette (first unused on the board) when omitted. `422 bad_parent` (parent not this child's), `too_deep` (would exceed 4 levels). |
| PATCH | `/categories/<id>` | C | `{name?, color?, parent_id?, symbol_id? \| icon_asset_id?}`. Re-parenting: `422 bad_parent` / `category_cycle` / `too_deep`. |
| DELETE | `/categories/<id>` | C | sub-categories float up to the top level; the category's cards keep their data, lose the link. |
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
| GET | `/settings?child_id=[&on=YYYY-MM-DD]` | S | `{daily_bonus, bonus_tts_asset_id, bonus_text, bonus_granted_today}` — the child-facing closing line; `daily_bonus` 0 = off; `bonus_granted_today` is null unless `on` (the caller's local date) is given |
| PUT | `/settings` | C | `{child_id, daily_bonus}` (0–100) — pre-generates TTS for the fixed sentence when > 0 |
| POST | `/rules/bonus` | C | `{child_id, on}` (caller's local date) — grants `daily_bonus` once per (child, day); `kind=rules_bonus`. 409 `bonus_disabled` (bonus is 0) / `bonus_already_granted`. Used by the caregiver editor **and** the PIN-gated button on the child's rules page |
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
| GET | `/templates` | C | `{templates:[{id,name_he,description_he,owned}]}` — bundled routines + the caregiver's saved ones (`owned:true`). |
| POST | `/apply-template` | C | `{child_id, template_id, the_date}` → `{created:N, items:[…]}`. Appends after any tasks already on that date. |
| POST | `/save-template` | C | `{child_id, the_date, name_he}` → `{id, name_he}` (201). Snapshots that day as a private template; 422 `empty_day`, 409 `template_limit` (20). |
| DELETE | `/templates/<id>` | C | 204. Own saved templates only; 403 `cannot_delete_bundled`. |
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
| POST | `/chat` | C | `{child_id, messages:[{role,content}]}` → `{reply, ready, slots}` — the interviewer agent; `slots` is the five collected facts (protagonist / situation / goal / sensory / triggers), `ready` flips when all five are set |
| POST | `/compose` | C | `{child_id, messages}` → runs the writer → SLP-reviewer → illustrator crew and saves the reviewed **text + read-aloud audio immediately** (no images yet). 429 `quota_exceeded` on the monthly LLM cap. |
| POST | `/<id>/illustrate` | C | `{page_index?}` → generates one page's illustration (next pending page if `page_index` omitted). 409 `already_illustrated`, 429 `quota_exceeded` on the image cap (the text story is unaffected). → `{page_index, image_url, art}` |
| GET | `?child_id=` | S | `{stories:[{id, title, art:{total,illustrated,pending_pages}, created_at}]}` |
| GET | `/<id>` | S | full story: `{title, protagonist, situation, goal, review_notes, art, pages:[{text, sentence_type, image_url, audio_url}]}` |
| DELETE | `/<id>` | C | 204 |

Composing returns fast; the caller then drives `/illustrate` once per page. The
real adapter is Google Gemini (`gemini-3.6-flash` for the crew, `gemini-2.5-flash-image`
for pages — the latter needs a billed account). Without a `GEMINI_API_KEY` a
deterministic stub runs the same shape
(five-slot interview → 5-page templated Hebrew story with sentence-type tags +
canned review → SVG illustrations).

## Account (GDPR) — `/api/account`

| Method | Path | Guard | Notes |
|---|---|---|---|
| GET | `/export` | C | JSON attachment: caregiver, children, module_settings, consent_records, devices, usage_counters. (Media bundle added in Phase 2.) |
| DELETE | `` | C | `{confirm:"DELETE"}` → deletes the auth user + cascade, clears cookie. 204. |

## Health — `/api/health`

`GET /api/health` → `{status, env, version}`. `?deep=1` also pings Supabase
(503 if unreachable).

## Reading & typing ("קריאה והקלדה") — `/api/learning`

Level-based (1–3). Content is bundled (global) + caregiver-authored per child.
A completed task never reappears. Tokens are **not** per task — every 3 completed
tasks in the same `(kind, level)` is a milestone worth 3 tokens, released only
by the caregiver's PIN (`POST /claim`, caregiver mode).

`progress` shape: `{completed, toward_next: completed%3, unclaimed: completed//3 - claimed}`.

| Method | Path | Guard | Notes |
|---|---|---|---|
| GET | `/reading?child_id=&level=` | S | `{tasks:[…not completed, each w/ `audio_url`], progress}` |
| GET | `/writing?child_id=&level=` | S | `{tasks:[…not completed, `hint` only], progress}` |
| POST | `/reading/<id>/done` | S | `{child_id}` — self-mark a text read → `{progress}` |
| POST | `/writing/attempt` | S | `{child_id, prompt_id, submitted}` — lenient Hebrew match; correct → completes the task → `{correct, target?, progress}` |
| POST | `/claim` | C | `{child_id, kind, level}` — releases `3 × unclaimed` tokens; 409 `nothing_to_claim` |
| GET | `/tasks?child_id=&kind=&level=` | C | editor list — every task (incl. bundled + completed), each with `owned` |
| POST | `/reading` `/writing` | C | `{child_id, level, title/body}` / `{child_id, level, hint, target}` — caregiver-authored (reading pre-generates TTS) |
| DELETE | `/reading/<id>` `/writing/<id>` | C | own child rows only (RLS); 204 |
| GET | `/progress?child_id=` | S | `{levels:[{kind, level, completed, toward_next, unclaimed}]}` |

## Typing board ("הפתקים שלי" / לוח הקלדה) — `/api/typing`

Free-composition notes for a child who already types. No target, no scoring, no
tokens, no PIN. A note is `{title, blocks}` where `blocks` is an array of
`{t: "h1"|"h2"|"p", s: "<plain text>"}` (never HTML), plus a `font_family`
(`rubik`|`assistant`|`heebo`) and `font_scale` (`sm`|`md`|`lg`|`xl`) recording
how it was written.

Saves are an **upsert on a client-generated `note_id`** so the offline outbox
(POST-only, no response) can replay them; a monotonic `rev` makes a stale replay
a no-op (the server returns the stored row, still `200`, so the queue drains).
There is deliberately **no `PUT /notes/<id>`** for that reason. The client PK
means a note id could collide with another tenant's — the route checks child
ownership and a raw conflict surfaces as `409 note_id_conflict`.

Limits: `title` ≤ 120, ≤ 200 blocks, ≤ 2000 chars/block, ≤ 20 000 total; `/speak`
input ≤ 1500 (`422 text_too_long_for_speech`).

| Method | Path | Guard | Notes |
|---|---|---|---|
| GET | `/notes?child_id=` | S | `{notes:[{id, title, preview, rev, font_family, font_scale, updated_at}]}` — no `blocks` |
| GET | `/notes/<id>` | S | full note + `audio_url` (null unless `/speak` has run) |
| POST | `/notes` | S | `{child_id, note_id, title, blocks, rev, font_family?, font_scale?}` → `{id, rev, updated_at}` (upsert) |
| DELETE | `/notes/<id>` | S | child or caregiver (product decision); audit-logged; 204 |
| POST | `/notes/<id>/speak` | S | `{child_id}` — on-demand TTS, cached on `sha256(text)`; `{audio_url}` or `{audio_url: null}` |
| GET | `/settings?child_id=` | S | `{font_family, font_scale}` — per-child default for a new note (defaults if no row) |
| PUT | `/settings` | S | `{child_id, font_family?, font_scale?}` → merged row |

## המשימות שלי (My Tasks) — `/api/tasks`

A personal checklist the child ticks off. Each task is `{title, symbol_id?,
recurrence}` where `recurrence` is `daily` (back to not-done each day) or `once`
(stays visible while unfinished or finished today; gone from tomorrow). "Done"
is a single `completed_on` date — the daily reset needs no cron.

Finishing every task due today earns `reward_tokens` (0–20, default 1, per-child)
**once per local date**, released by the caregiver's PIN (`POST /claim` after an
inline PIN gate) — same shape as the rules daily bonus / learning milestone. The
token ledger entry has `kind: "tasks"`.

`/toggle` is the User-Mode write and goes through the offline outbox: the caller
sends `the_date`, the server sets `completed_on` to it (or null), idempotently.

| Method | Path | Guard | Notes |
|---|---|---|---|
| GET | `/day?child_id=&date=` | S | `{items:[{…, is_done}], reward_tokens, reward_claimed, all_done}` — tasks due that date. User Mode uses this. |
| POST | `/toggle` | S | `{task_id, the_date, completed, idempotency_key?}` → the updated item. **Idempotent** (offline outbox replays it). |
| GET | `/items?child_id=` | C | `{items:[…], reward_tokens}` — the full list, including one-off tasks finished on an earlier day. |
| POST | `/items` | C | `{child_id, title, symbol_id?, recurrence?"daily"\|"once", sort_order?}`. Pre-generates TTS. |
| PATCH | `/items/<id>` | C | any field; regenerates TTS if `title` changes. |
| DELETE | `/items/<id>` | C | 204 |
| PUT | `/items/order` | C | `{child_id, order:[id,…]}` |
| PUT | `/settings` | C | `{child_id, reward_tokens}` → `{reward_tokens}` |
| POST | `/claim` | C | `{child_id, the_date}` → `{tokens_awarded, balance}` (201). 409 `tasks_incomplete`, 409 `reward_already_granted`. |
