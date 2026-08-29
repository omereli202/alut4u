-- AI social stories (Phase 6).
--
-- A caregiver is interviewed by an agent; the agent composes a structured story
-- (pages of text + an illustration each). The illustration media_assets rows are
-- child-scoped like any other upload.

create table social_stories (
  id          uuid primary key default gen_random_uuid(),
  child_id    uuid not null references children (id) on delete cascade,
  title       text not null,
  protagonist text,
  situation   text,
  goal        text,
  pages       jsonb not null,     -- [ { "text": "...", "image_asset_id": "uuid"|null } ]
  created_by  uuid references caregivers (id) on delete set null,
  created_at  timestamptz not null default now()
);

create index social_stories_child_idx on social_stories (child_id, created_at desc);

alter table social_stories enable row level security;
create policy social_stories_owner_all on social_stories for all
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

grant select, insert, update, delete on social_stories to authenticated;

-- media_kind gains 'story_image'.
alter type media_kind add value if not exists 'story_image';
