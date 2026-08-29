-- Schedule module (Phase 3): the daily routine + a monthly calendar.
--
-- schedule_items are date-specific (build today, copy to another day). The
-- "where are we now" focus view walks the incomplete items in order.
-- calendar_events are one-off appointments shown on a month grid.

-- ---------------------------------------------------------------------------
-- schedule_items — one row per task on a given day.
--   visual: symbol_id (bundled) OR icon_asset_id (upload), like AAC cards.
--   tts_asset_id: pre-generated audio of the title (read-the-day-aloud).
-- ---------------------------------------------------------------------------
create table schedule_items (
  id            uuid primary key default gen_random_uuid(),
  child_id      uuid not null references children (id) on delete cascade,
  the_date      date not null,
  title         text not null,
  start_time    time,
  symbol_id     text references symbols (id) on delete set null,
  icon_asset_id uuid references media_assets (id) on delete set null,
  tts_asset_id  uuid references media_assets (id) on delete set null,
  sort_order    integer not null default 0,
  is_completed  boolean not null default false,
  completed_at  timestamptz,
  created_at    timestamptz not null default now(),
  constraint schedule_item_one_visual check (
    (symbol_id is not null)::int + (icon_asset_id is not null)::int <= 1
  )
);

create index schedule_items_child_date_idx on schedule_items (child_id, the_date);

alter table schedule_items enable row level security;
create policy schedule_items_owner_all on schedule_items for all
  using (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  )
  with check (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  );

-- ---------------------------------------------------------------------------
-- calendar_events — one-off dated events (appointments, birthdays).
-- ---------------------------------------------------------------------------
create table calendar_events (
  id            uuid primary key default gen_random_uuid(),
  child_id      uuid not null references children (id) on delete cascade,
  event_date    date not null,
  title         text not null,
  note          text,
  symbol_id     text references symbols (id) on delete set null,
  icon_asset_id uuid references media_assets (id) on delete set null,
  created_at    timestamptz not null default now(),
  constraint calendar_event_one_visual check (
    (symbol_id is not null)::int + (icon_asset_id is not null)::int <= 1
  )
);

create index calendar_events_child_date_idx on calendar_events (child_id, event_date);

alter table calendar_events enable row level security;
create policy calendar_events_owner_all on calendar_events for all
  using (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  )
  with check (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  );

grant select, insert, update, delete on schedule_items, calendar_events to authenticated;
