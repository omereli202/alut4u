-- AAC module (Phase 2): the communication grid.
--
-- Per-child: aac_categories, aac_cards.
-- Global read-only: symbols (bundled pictogram library), board_templates
-- (starter boards offered at child creation).

-- ---------------------------------------------------------------------------
-- symbols — bundled pictogram library. Global, read-only for any signed-in
-- caregiver. Seeded from scripts/build_symbols.py output.
-- ---------------------------------------------------------------------------
create table symbols (
  id         text primary key,              -- stable slug, e.g. 'eat'
  file_path  text not null,                 -- under frontend/assets/symbols/
  label_he   text not null,
  keywords_he text[] not null default '{}',
  licence    text not null,
  source     text not null,
  created_at timestamptz not null default now()
);

-- Full-text-ish search over the Hebrew keyword array.
create index symbols_keywords_gin on symbols using gin (keywords_he);

alter table symbols enable row level security;
create policy symbols_read on symbols for select to authenticated using (true);

-- ---------------------------------------------------------------------------
-- board_templates — starter boards. Global, read-only.
-- spec: { "categories": [ { "name", "color", "cards": [
--          { "label", "tts_text"?, "symbol_id"?, "grid_order" } ] } ] }
-- ---------------------------------------------------------------------------
create table board_templates (
  id             text primary key,
  name_he        text not null,
  level          integer not null,          -- 1 = first words … 3 = full grid
  description_he text,
  spec           jsonb not null,
  created_at     timestamptz not null default now()
);

alter table board_templates enable row level security;
create policy board_templates_read on board_templates for select to authenticated using (true);

-- ---------------------------------------------------------------------------
-- aac_categories — per child. Tabs on the board.
-- ---------------------------------------------------------------------------
create table aac_categories (
  id         uuid primary key default gen_random_uuid(),
  child_id   uuid not null references children (id) on delete cascade,
  name       text not null,
  color      text,
  sort_order integer not null default 0,
  created_at timestamptz not null default now()
);

create index aac_categories_child_idx on aac_categories (child_id);

alter table aac_categories enable row level security;
create policy aac_categories_owner_all on aac_categories for all
  using (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  )
  with check (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  );

-- ---------------------------------------------------------------------------
-- aac_cards — per child. One tile on the board.
--
-- Visual: at most one of symbol_id (bundled library) or icon_asset_id
-- (caregiver upload). A text-only card (neither) is allowed.
-- Audio priority at tap time: audio_asset_id (caregiver upload/recording) →
-- tts_asset_id (pre-generated on save) → nothing.
-- ---------------------------------------------------------------------------
create table aac_cards (
  id            uuid primary key default gen_random_uuid(),
  child_id      uuid not null references children (id) on delete cascade,
  category_id   uuid references aac_categories (id) on delete set null,
  label         text not null,
  tts_text      text,                         -- spoken text; defaults to label
  symbol_id     text references symbols (id) on delete set null,
  icon_asset_id uuid references media_assets (id) on delete set null,
  audio_asset_id uuid references media_assets (id) on delete set null,
  tts_asset_id  uuid references media_assets (id) on delete set null,
  grid_order    integer not null default 0,
  created_at    timestamptz not null default now(),
  constraint aac_card_one_visual check (
    (symbol_id is not null)::int + (icon_asset_id is not null)::int <= 1
  )
);

create index aac_cards_child_idx on aac_cards (child_id);
create index aac_cards_category_idx on aac_cards (category_id);

alter table aac_cards enable row level security;
create policy aac_cards_owner_all on aac_cards for all
  using (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  )
  with check (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  );

-- media_assets already exists (Phase 1). Grants for the new tables come from
-- the default-privileges rule in 0003, but be explicit for authenticated:
grant select, insert, update, delete on aac_categories, aac_cards to authenticated;
grant select on symbols, board_templates to authenticated;
