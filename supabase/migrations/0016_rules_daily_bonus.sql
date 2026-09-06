-- Rules module: a per-child "daily bonus" the caregiver sets.
--
-- User Mode shows a fixed closing line at the bottom of the rules list
-- ("אם שמרת על הכללים, בסוף היום תקבל X אסימונים") and the read-aloud button
-- speaks it after the rules. The caregiver grants the bonus by hand at the end
-- of the day (a normal POST /api/tokens/award behind a confirm dialog) — nothing
-- here awards tokens automatically.
--
-- daily_bonus = 0 means "off": the line is hidden and not spoken. That's the
-- default, so existing children are unaffected. No row -> the same default.

create table rules_settings (
  child_id           uuid primary key references children (id) on delete cascade,
  daily_bonus        integer not null default 0 check (daily_bonus between 0 and 100),
  bonus_tts_asset_id uuid references media_assets (id) on delete set null,  -- generated from the fixed sentence
  updated_at         timestamptz not null default now()
);

alter table rules_settings enable row level security;

create policy rules_settings_owner_all on rules_settings for all
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

grant select, insert, update, delete on rules_settings to authenticated;
