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
| `module_settings` | Per-child module on/off. Auto-created by trigger. | via child owner |
| `consent_records` | Append-only: what was consented to, version, when, context. | owner (select); insert via backend |
| `device_sessions` | One per signed-in device. Encrypted refresh token. Revocable. | owner (select/update) |
| `media_assets` | Pointers to Storage objects. `child_id` null for shared TTS cache. | owner (select) |
| `usage_counters` | `(caregiver_id, period 'YYYY-MM')` → tts_chars / image_count / llm_tokens. | owner (select) |
| `audit_log` | Sensitive actions. | none — service role only |

Enums: `consent_basis`, `media_kind`.

## AAC (migration 0002, Phase 2)

| Table | Purpose |
|---|---|
| `aac_categories` | `child_id` FK, name, color, sort_order. |
| `aac_cards` | `child_id`, `category_id`, label, `tts_text`, `grid_order`; **either** `symbol_id` **or** `icon_asset_id` (CHECK), optional `audio_asset_id`. |
| `symbols` | Global read-only. Bundled library: slug, file_path, `keywords_he text[]`, licence, source. Not child-scoped. `file_path` is `<id>.svg` (flat, no subfolders) for the Mulberry set; the dev-only PCS/Boardmaker set (`pcs-NNNN` ids) uses `pcs/<id>.png`. `ui.js`'s `symbolUrl()` resolves both. |
| `board_templates` | Global. Starter boards: `name_he`, `level`, `cards jsonb`. |

## Later phases (designed, not built)

`schedule_items`, `calendar_events`, `behavior_rules`, `token_transactions`
(source of truth) + `token_balances` (materialized), `rewards`,
`reward_redemptions` (`status` for the approval queue), `social_stories`,
`reading_exercises`, `reading_attempts`, `calming_media`.
