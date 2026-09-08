-- "בוא נצייר" (Let's paint) — a blank drawing page and a colouring page.
--
-- Two modes share one table: a blank white page, and a colouring page built
-- from a bundled Mulberry symbol whose colour-filled shapes are rendered white
-- and tappable while its stroked outlines stay black on top.
--
-- A painting is stored as VECTOR JSON, never as a PNG. That is a deliberate
-- product + privacy decision, not an optimisation:
--   * nothing about the child leaves the device as an image — no Supabase
--     Storage object, no media_assets row, no monthly quota (a PNG is produced
--     client-side only, on demand, for share / print, and is never uploaded);
--   * a few hundred KB of JSON replays identically at any resolution, on any
--     device, where a raster is locked to the tablet it was drawn on;
--   * the child undoes, and a caregiver re-renders a thumbnail, from the one
--     source of truth.
--
-- Coordinates are page-NORMALISED (0..1), never viewBox units. The bundled
-- symbols ship in ~15 different viewBoxes and scripts/build_symbols.py may
-- re-export any of them; normalised strokes stay correct across all of that and
-- survive the line art disappearing entirely (the brushwork replays on a blank
-- page).
--
-- `paintings.id` has a default but is normally CLIENT-generated: writes go
-- through the IndexedDB outbox, which is POST-only and returns nothing, so the
-- client must know the id before the row exists. Every save is an upsert on
-- that id gated by a monotonic client `rev` — a replayed queue entry is a
-- no-op and an out-of-order replay never clobbers newer art. Same contract as
-- typing_notes (migration 0023).

alter table module_settings
  add column painting_enabled boolean not null default true;

-- ---------------------------------------------------------------------------
-- paintings — one saved picture.
--   page:    {"kind":"blank"} | {"kind":"symbol","symbol_id":"cat",
--                                "sig":"8a3f1c2d","sv":"20260914e"}
--            `sig` hashes the colouring page's region keys at save time; if a
--            regenerated symbol no longer matches, fills are applied by key
--            only and the caregiver is told, instead of silently landing on
--            the wrong shapes.
--   strokes: [{"c":"#e94f37","w":0.024,"e":0,"p":[x,y, x,y, ...]}, ...]
--            `p` is a FLAT alternating x,y array (half the bytes of objects),
--            quantised to 3 decimals; `e`=1 is an eraser stroke, replayed with
--            canvas globalCompositeOperation destination-out.
--   fills:   [{"r":"<region key>","c":"#4a90e2"}, ...] — an array, not an
--            object, so the array-length check below can bound it.
--   The caps below mirror app/schemas/painting.py; the pydantic model also
--   enforces a 60,000 TOTAL point ceiling, which SQL cannot express cheaply.
-- ---------------------------------------------------------------------------
create table paintings (
  id         uuid primary key default gen_random_uuid(),
  child_id   uuid not null references children (id) on delete cascade,
  title      text not null default '' check (char_length(title) <= 80),
  page       jsonb not null default '{"kind":"blank"}'::jsonb
               check (jsonb_typeof(page) = 'object'
                      and (page ->> 'kind') in ('blank', 'symbol')),
  strokes    jsonb not null default '[]'::jsonb
               check (jsonb_typeof(strokes) = 'array'
                      and jsonb_array_length(strokes) <= 400),
  fills      jsonb not null default '[]'::jsonb
               check (jsonb_typeof(fills) = 'array'
                      and jsonb_array_length(fills) <= 300),
  rev        integer not null default 1 check (rev >= 1),
  created_by uuid references caregivers (id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index paintings_child_idx on paintings (child_id, updated_at desc);

alter table paintings enable row level security;

create policy paintings_owner_all on paintings for all
  using (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  )
  with check (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  );

grant select, insert, update, delete on paintings to authenticated;

-- ---------------------------------------------------------------------------
-- painting_pages — colouring pages the caregiver added for THIS child, on top
-- of the curated shortlist that ships as a client-side constant in
-- frontend/js/modules/painting/pages.js. Picked with the existing AAC symbol
-- picker, so this is the same `symbol_id text references symbols (id)` shape
-- task_items uses (migration 0025).
-- ---------------------------------------------------------------------------
create table painting_pages (
  id         uuid primary key default gen_random_uuid(),
  child_id   uuid not null references children (id) on delete cascade,
  symbol_id  text not null references symbols (id) on delete cascade,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (child_id, symbol_id)
);

create index painting_pages_child_idx on painting_pages (child_id, sort_order);

alter table painting_pages enable row level security;

create policy painting_pages_owner_all on painting_pages for all
  using (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  )
  with check (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  );

grant select, insert, update, delete on painting_pages to authenticated;
