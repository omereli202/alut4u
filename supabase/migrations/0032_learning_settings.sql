-- Per-child level settings for "קריאה והקלדה" (Reading & Writing) — the
-- caregiver now sets which level the child works at, separately for reading
-- and writing (level was previously a fully general, caller-supplied
-- parameter with no persisted per-child value at all — the child freely
-- picked their own level via always-enabled tabs). No row = level 1/1,
-- identical to today's default behaviour for every existing child.
--
-- Same shape as rules_settings (0016) / typing_settings (0023) /
-- task_settings (0025): a small per-child settings table, PK child_id,
-- RLS via child ownership.
create table learning_settings (
  child_id      uuid primary key references children (id) on delete cascade,
  reading_level integer not null default 1 check (reading_level between 1 and 3),
  writing_level integer not null default 1 check (writing_level between 1 and 3),
  updated_at    timestamptz not null default now()
);

alter table learning_settings enable row level security;

create policy learning_settings_owner_all on learning_settings for all
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

grant select, insert, update, delete on learning_settings to authenticated;
