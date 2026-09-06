-- AAC #3 — categories can nest (אוכל ‹ ארוחת בוקר ‹ ביצת עין) and carry their
-- own picture, so the child's board becomes a drill-down grid instead of a
-- flat tab strip.
--
-- parent_id ON DELETE SET NULL: deleting a category floats its sub-categories
-- up to the top level rather than cascading them away (its direct cards already
-- go category_id = null via the existing FK). Depth is capped at 4 levels in
-- the API, not here.
--
-- Numbering: 0016–0019 belong to the rules/schedule branch (not yet merged to
-- dev); this is the next free number reserved for the AAC branch.

alter table aac_categories
  add column if not exists parent_id     uuid references aac_categories (id) on delete set null,
  add column if not exists symbol_id     text references symbols (id)        on delete set null,
  add column if not exists icon_asset_id uuid references media_assets (id)   on delete set null;

create index if not exists aac_categories_parent_idx on aac_categories (parent_id);

-- Same rule as aac_cards: at most one of a bundled symbol or an uploaded icon.
alter table aac_categories add constraint aac_categories_one_visual check (
  (symbol_id is not null)::int + (icon_asset_id is not null)::int <= 1
);
