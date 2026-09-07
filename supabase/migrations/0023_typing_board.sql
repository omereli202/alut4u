-- Typing board ("לוח הקלדה") — free composition + saved notes ("פתקים").
--
-- For a child who already communicates by typing. Distinct from
-- reading_texts / writing_prompts: no target, no scoring, no tokens, no
-- levels — the child just writes, titles it, and saves it to show a parent
-- or therapist later.
--
-- `typing_notes.id` has a default but is normally CLIENT-generated: writes go
-- through the IndexedDB outbox, which is POST-only and returns no response to
-- the caller, so the client must know the id before the row exists. Every save
-- is an upsert on that id, gated by a monotonic client `rev` — a replayed queue
-- entry is a no-op and an out-of-order replay never clobbers newer text.

alter table module_settings
  add column typing_board_enabled boolean not null default true;

-- ---------------------------------------------------------------------------
-- typing_notes — one saved note.
--   blocks: [{"t":"h1"|"h2"|"p", "s":"<plain text>"}, ...] — never HTML.
--   font_family / font_scale record how THIS note was written, so it reads
--     back the same way months later (typing_settings is only the new-note
--     default).
-- ---------------------------------------------------------------------------
create table typing_notes (
  id            uuid primary key default gen_random_uuid(),
  child_id      uuid not null references children (id) on delete cascade,
  title         text not null default '' check (char_length(title) <= 120),
  blocks        jsonb not null default '[]'::jsonb
                  check (jsonb_typeof(blocks) = 'array'
                         and jsonb_array_length(blocks) <= 200),
  rev           integer not null default 1 check (rev >= 1),
  font_family   text not null default 'rubik'
                  check (font_family in ('rubik', 'assistant', 'heebo')),
  font_scale    text not null default 'md'
                  check (font_scale in ('sm', 'md', 'lg', 'xl')),
  tts_asset_id  uuid references media_assets (id) on delete set null,
  tts_text_hash text,                    -- sha256 of the text the audio was made from
  created_by    uuid references caregivers (id) on delete set null,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index typing_notes_child_idx on typing_notes (child_id, updated_at desc);

alter table typing_notes enable row level security;

create policy typing_notes_owner_all on typing_notes for all
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

grant select, insert, update, delete on typing_notes to authenticated;

-- ---------------------------------------------------------------------------
-- typing_settings — per-child default typeface + size for a NEW note
-- (precedent: rules_settings, migration 0016). Enum KEYS, never raw CSS — the
-- client maps a key through a frozen allow-list to a font stack, so nothing
-- user-supplied reaches a style attribute. No row -> defaults.
-- ---------------------------------------------------------------------------
create table typing_settings (
  child_id    uuid primary key references children (id) on delete cascade,
  font_family text not null default 'rubik' check (font_family in ('rubik', 'assistant', 'heebo')),
  font_scale  text not null default 'md'    check (font_scale  in ('sm', 'md', 'lg', 'xl')),
  updated_at  timestamptz not null default now()
);

alter table typing_settings enable row level security;

create policy typing_settings_owner_all on typing_settings for all
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

grant select, insert, update, delete on typing_settings to authenticated;
