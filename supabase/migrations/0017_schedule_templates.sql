-- Schedule templates (Phase 3 follow-up): starter daily routines a caregiver
-- can apply to a date instead of building the day task-by-task. Mirrors
-- board_templates (0004_aac.sql) — global, read-only, shipped to every
-- environment (not a dev-only seed).
--
-- spec: { "tasks": [ { "title", "start_time"?"HH:MM", "symbol_id"? } ] }
-- symbol_id values must exist in `symbols` (see 0005_reference_data.sql).

create table schedule_templates (
  id             text primary key,
  name_he        text not null,
  description_he text,
  sort_order     integer not null default 0,
  spec           jsonb not null,
  created_at     timestamptz not null default now()
);

alter table schedule_templates enable row level security;
create policy schedule_templates_read on schedule_templates
  for select to authenticated using (true);

grant select on schedule_templates to authenticated;

-- ---------------------------------------------------------------------------
-- Seed rows. Add a NEW migration to change these — do not edit this one.
-- ---------------------------------------------------------------------------
insert into schedule_templates (id, name_he, description_he, sort_order, spec) values
(
  'home-day', 'יום רגיל בבית',
  'שגרת יום מלא בבית — ארוחות, משחק, מנוחה ושינה.', 0,
  '{"tasks":[
     {"title":"ארוחת בוקר","start_time":"07:30","symbol_id":"eat"},
     {"title":"להתלבש","start_time":"08:00"},
     {"title":"צחצוח שיניים","start_time":"08:20"},
     {"title":"משחק","start_time":"09:00","symbol_id":"play"},
     {"title":"חטיף","start_time":"10:30","symbol_id":"eat"},
     {"title":"סיפור","start_time":"11:15","symbol_id":"book"},
     {"title":"ארוחת צהריים","start_time":"12:30","symbol_id":"eat"},
     {"title":"מנוחה","start_time":"13:30","symbol_id":"break"},
     {"title":"משחק בחוץ","start_time":"15:30","symbol_id":"ball"},
     {"title":"מוזיקה","start_time":"17:00","symbol_id":"music"},
     {"title":"ארוחת ערב","start_time":"18:00","symbol_id":"eat"},
     {"title":"אמבטיה","start_time":"19:00"},
     {"title":"סיפור לפני השינה","start_time":"19:30","symbol_id":"book"},
     {"title":"שינה","start_time":"20:00","symbol_id":"sleep"}
   ]}'
),
(
  'school-day', 'יום בית ספר',
  'בוקר מהיר, יום לימודים, ואחר הצהריים בבית.', 1,
  '{"tasks":[
     {"title":"ארוחת בוקר","start_time":"07:00","symbol_id":"eat"},
     {"title":"להתלבש","start_time":"07:30"},
     {"title":"צחצוח שיניים","start_time":"07:45"},
     {"title":"בית ספר","start_time":"08:00","symbol_id":"go"},
     {"title":"חזרה הביתה","start_time":"13:00","symbol_id":"home"},
     {"title":"ארוחת צהריים","start_time":"13:30","symbol_id":"eat"},
     {"title":"מנוחה","start_time":"14:30","symbol_id":"break"},
     {"title":"שיעורי בית","start_time":"15:30","symbol_id":"book"},
     {"title":"משחק","start_time":"16:30","symbol_id":"play"},
     {"title":"ארוחת ערב","start_time":"18:00","symbol_id":"eat"},
     {"title":"סיפור לפני השינה","start_time":"19:30","symbol_id":"book"},
     {"title":"שינה","start_time":"20:00","symbol_id":"sleep"}
   ]}'
),
(
  'morning', 'בוקר בלבד',
  'רק שגרת הבוקר — מהקימה ועד היציאה מהבית.', 2,
  '{"tasks":[
     {"title":"להתעורר","start_time":"07:00"},
     {"title":"שירותים","start_time":"07:15","symbol_id":"toilet"},
     {"title":"ארוחת בוקר","start_time":"07:30","symbol_id":"eat"},
     {"title":"להתלבש","start_time":"07:50"},
     {"title":"צחצוח שיניים","start_time":"08:05"},
     {"title":"מוכנים לצאת","start_time":"08:20","symbol_id":"finished"}
   ]}'
)
on conflict (id) do nothing;
