-- Graded reading & writing practice (Phase 7).
--
-- reading_texts / writing_prompts are global read-only graded content.
-- learning_attempts records each try (per child, RLS). Reading pass/fail is
-- the caregiver's judgement (NO speech recognition — privacy decision);
-- writing is checked server-side by normalised Hebrew comparison.

create table reading_texts (
  id         text primary key,
  level      integer not null,
  title      text not null,
  body       text not null,
  created_at timestamptz not null default now()
);
alter table reading_texts enable row level security;
create policy reading_texts_read on reading_texts for select to authenticated using (true);

create table writing_prompts (
  id         text primary key,
  level      integer not null,
  hint       text,                    -- what to write (shown to the child)
  target     text not null,           -- the correct answer
  created_at timestamptz not null default now()
);
alter table writing_prompts enable row level security;
create policy writing_prompts_read on writing_prompts for select to authenticated using (true);

create table learning_attempts (
  id              uuid primary key default gen_random_uuid(),
  child_id        uuid not null references children (id) on delete cascade,
  kind            text not null,       -- 'reading' | 'writing'
  ref_id          text not null,       -- reading_texts.id | writing_prompts.id
  level           integer not null,
  verdict         text not null,       -- 'pass' | 'fail'
  tokens_awarded  integer not null default 0,
  created_at      timestamptz not null default now()
);
create index learning_attempts_child_idx on learning_attempts (child_id, created_at desc);
alter table learning_attempts enable row level security;
create policy learning_attempts_owner_all on learning_attempts for all
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

grant select on reading_texts, writing_prompts to authenticated;
grant select, insert on learning_attempts to authenticated;

-- ---------------------------------------------------------------------------
-- Bundled graded content (Hebrew).
-- ---------------------------------------------------------------------------
insert into reading_texts (id, level, title, body) values
  ('r1-cat',   1, 'החתול',      'לחתול יש זנב. החתול אוהב חלב. החתול ישן על הכיסא.'),
  ('r1-ball',  1, 'הכדור',      'הכדור אדום. אני זורק את הכדור. הכדור מתגלגל.'),
  ('r2-park',  2, 'בפארק',      'הלכנו לפארק אחרי הצהריים. שיחקנו בחול ובנינו מגדל גדול. אחר כך אכלנו תפוח וחזרנו הביתה.'),
  ('r2-rain',  2, 'יום גשום',   'בבוקר ירד גשם חזק. לבשתי מעיל וגם מגפיים. קפצתי בשלולית אחת קטנה בדרך לגן.'),
  ('r3-trip',  3, 'הטיול',      'ביום שישי יצאנו לטיול משפחתי אל ההר. הדרך הייתה ארוכה ומפותלת, אבל הנוף מלמעלה היה שווה כל צעד. ראינו נשר גדול חג במעגלים מעל העמק.')
on conflict (id) do nothing;

insert into writing_prompts (id, level, hint, target) values
  ('w1-shalom', 1, 'כתבו: שלום',        'שלום'),
  ('w1-ima',    1, 'כתבו: אמא',         'אמא'),
  ('w1-bayit',  1, 'כתבו: בית',         'בית'),
  ('w2-sun',    2, 'כתבו: השמש זורחת',  'השמש זורחת'),
  ('w2-dog',    2, 'כתבו: הכלב רץ מהר', 'הכלב רץ מהר'),
  ('w3-sent',   3, 'כתבו: אני אוהב ללמוד דברים חדשים', 'אני אוהב ללמוד דברים חדשים')
on conflict (id) do nothing;
