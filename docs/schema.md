# Database schema

Source of truth is `supabase/migrations/`. This doc is the map.

## Conventions

- UUID PKs (`gen_random_uuid()`), `timestamptz` everywhere (never
  `timestamp`), `created_at` on every row.
- **Every child-scoped table: `ENABLE ROW LEVEL SECURITY` + a policy resolving
  ownership through `children.caregiver_id = auth.uid()`, in the same migration
  that creates the table.** CI fails the build otherwise.
- Free-text foreign keys are a bug. Categories, symbols etc. get real tables.

## Foundation (migration 0001)

| Table | Purpose | RLS |
|---|---|---|
| `caregivers` | The account. 1:1 with `auth.users`. Holds `pin_hash`, consent timestamps. | self only |
| `children` | Subject of care. `caregiver_id` FK, `consent_basis`. | owner (all) |
| `module_settings` | Per-child module on/off (7 `*_enabled` cols). Auto-created by trigger. | via child owner |
| `consent_records` | Append-only: what was consented to, version, when, context. | owner (select); insert via backend |
| `device_sessions` | One per signed-in device. Encrypted refresh token. Revocable. | owner (select/update) |
| `media_assets` | Pointers to Storage objects. `child_id` null for shared TTS cache. | owner (select) |
| `usage_counters` | `(caregiver_id, period 'YYYY-MM')` → tts_chars / image_count / llm_tokens. | owner (select) |
| `audit_log` | Sensitive actions. | none — service role only |

Enums: `consent_basis`, `media_kind`.

## AAC (migration 0002, Phase 2)

| Table | Purpose |
|---|---|
| `aac_categories` | `child_id` FK, name, color, sort_order; `parent_id` self-FK (`ON DELETE SET NULL` — nesting, capped at 4 levels in the API); **either** `symbol_id` **or** `icon_asset_id` (CHECK). |
| `aac_cards` | `child_id`, `category_id`, label, `tts_text`, `grid_order`; **either** `symbol_id` **or** `icon_asset_id` (CHECK), optional `audio_asset_id`. |
| `symbols` | Global read-only. Bundled library: slug, file_path, `keywords_he text[]`, licence, source. Not child-scoped. `file_path` is `<id>.svg` (flat, no subfolders) for the Mulberry set; the dev-only PCS/Boardmaker set (`pcs-NNNN` ids) uses `pcs/<id>.png`. `ui.js`'s `symbolUrl()` resolves both. |
| `board_templates` | Global. Starter boards: `name_he`, `level`, `cards jsonb`. |

## Later phases (designed, not built)

`schedule_templates` (migration 0017; `caregiver_id` added in 0019) — starter
daily routines (`name_he`, `description_he`, `sort_order`, `spec jsonb` of
`{tasks:[{title, start_time?, symbol_id?}]}`), applied to a date via `POST
/api/schedule/apply-template`. RLS is **"global OR mine"**: `caregiver_id` NULL =
bundled (readable by all, seeded in migrations), a set `caregiver_id` = a
template the caregiver saved from one of their days (`POST
/api/schedule/save-template`), private to them and included in their account
export. A new shape for this repo — elsewhere shared rows are served via the
service role.

`rules_settings` (migration 0016, `last_bonus_date` added in 0018) — per-child
rules-module config: `daily_bonus` (0–100, 0 = off), its pre-generated
`bonus_tts_asset_id`, and `last_bonus_date` (the once-a-day guard for
`POST /api/tokens/rules/bonus`, keyed on the caller's local date). Drives the
child-facing closing line under the rules list; no row = the default (off).

`reading_texts` / `writing_prompts` (migration 0009; `child_id`/`created_by`/
`tts_asset_id` added in 0022) — graded "קריאה והקלדה" content: `child_id` NULL =
bundled global, a value = caregiver-authored for that child (RLS). `learning_completions`
(0022, PK `child_id`+`task_id`) is the "done" marker — a completed task never
reappears. `learning_reward_claims` (0022, PK `child_id`+`kind`+`level`) counts
how many 3-task milestones have been paid (each worth 3 tokens, released by
caregiver PIN). `learning_attempts` still logs every try.

`typing_notes` / `typing_settings` (migration 0023) — the "הפתקים שלי" typing
board (7th `module_settings` column `typing_board_enabled`). `typing_notes.id`
is **client-generated** (the offline outbox needs it before the row exists);
every save is an upsert gated by a monotonic `rev`. `blocks` is a jsonb array of
`{t, s}` (3 styles, plain text, never HTML). `font_family`/`font_scale` on the
note record how it was written; `typing_settings` (per-child, PK `child_id`,
like `rules_settings`) is only the default for a new note — no row = defaults.
Both are in the account export; erasure is FK cascade.

`schedule_items`, `calendar_events`, `behavior_rules`, `token_transactions`
(source of truth) + `token_balances` (materialized), `rewards`,
`reward_redemptions` (`status` for the approval queue), `social_stories`,
`calming_media`.
