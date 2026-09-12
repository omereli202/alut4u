-- "Take a picture" everywhere a symbol picker exists: task_items was the one
-- card-like table missing an upload option (aac_cards, aac_categories,
-- schedule_items, calendar_events, behavior_rules and rewards all already
-- have icon_asset_id — 0004, 0006, 0007, 0020). Same rule as the others: at
-- most one of a bundled symbol or an uploaded icon.

alter table task_items
  add column if not exists icon_asset_id uuid references media_assets (id) on delete set null;

alter table task_items add constraint task_items_one_visual check (
  (symbol_id is not null)::int + (icon_asset_id is not null)::int <= 1
);

-- No RLS/grant changes: task_items_owner_all (0025) is `for all` on the whole
-- table and the grant is table-level, so the new column is already covered.
