-- "המשימות שלי" (My Tasks) — a personal checklist the child ticks off, with a
-- token reward for clearing the whole list.
--
-- Distinct from the schedule ("סדר יום"): no times, no calendar, no templates —
-- just a short list of chores/goals the caregiver curates, each with a symbol.
-- Finishing every task due today earns a configurable number of tokens,
-- released only when the caregiver enters their PIN (same pattern as the rules
-- daily bonus and the learning milestone).
--
-- "Done" is a single date column, not a completions table:
--   * completed_on = <the child's local date> -> done for that day
--   * a 'daily' task with completed_on < today reads as not-done again, so the
--     daily reset needs no cron and no sweep
--   * a 'once' task stays visible while completed_on is null OR = today (it
--     shows ticked for the rest of the day it was finished) and disappears
--     from tomorrow on
-- The child's completion write is set-to-value (never an increment), so the
-- offline outbox can replay it safely.

alter table module_settings
  add column tasks_enabled boolean not null default true;

-- ---------------------------------------------------------------------------
-- task_items — one task on the child's list.
-- ---------------------------------------------------------------------------
create table task_items (
  id           uuid primary key default gen_random_uuid(),
  child_id     uuid not null references children (id) on delete cascade,
  title        text not null check (char_length(title) between 1 and 80),
  symbol_id    text references symbols (id) on delete set null,
  tts_asset_id uuid references media_assets (id) on delete set null,
  recurrence   text not null default 'daily' check (recurrence in ('daily', 'once')),
  sort_order   integer not null default 0,
  completed_on date,                     -- the child's local date of the tick; null = not done
  created_at   timestamptz not null default now()
);

create index task_items_child_idx on task_items (child_id, sort_order);

alter table task_items enable row level security;

create policy task_items_owner_all on task_items for all
  using (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  )
  with check (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  );

grant select, insert, update, delete on task_items to authenticated;

-- ---------------------------------------------------------------------------
-- task_settings — per-child reward config. No row -> defaults (precedent:
-- rules_settings, migration 0016 + 0018). last_reward_date is the once-a-day
-- guard for POST /api/tasks/claim, keyed on the caller's local date.
-- ---------------------------------------------------------------------------
create table task_settings (
  child_id         uuid primary key references children (id) on delete cascade,
  reward_tokens    integer not null default 1 check (reward_tokens between 0 and 20),
  last_reward_date date,
  updated_at       timestamptz not null default now()
);

alter table task_settings enable row level security;

create policy task_settings_owner_all on task_settings for all
  using (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  )
  with check (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  );

grant select, insert, update, delete on task_settings to authenticated;
