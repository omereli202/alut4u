-- Global reference data (Phase 2): the bundled symbol library and the starter
-- board templates. Ships to every environment (not dev-only seed).
--
-- The symbol rows mirror scripts/build_symbols.py output. When the real
-- pictogram library is licensed, add a NEW migration with the updated rows —
-- do not edit this one.

-- ---------------------------------------------------------------------------
-- symbols  (placeholder set — emoji SVGs under frontend/assets/symbols/)
-- ---------------------------------------------------------------------------
insert into symbols (id, file_path, label_he, keywords_he, licence, source) values
  ('yes', 'yes.svg', 'כן', '{"כן","מסכים","אישור"}', 'placeholder', 'emoji (Unicode)'),
  ('no', 'no.svg', 'לא', '{"לא","מסרב","שלילה"}', 'placeholder', 'emoji (Unicode)'),
  ('more', 'more.svg', 'עוד', '{"עוד","עוד פעם","להוסיף"}', 'placeholder', 'emoji (Unicode)'),
  ('stop', 'stop.svg', 'מספיק', '{"מספיק","עצור","די","להפסיק"}', 'placeholder', 'emoji (Unicode)'),
  ('want', 'want.svg', 'רוצה', '{"רוצה","אני רוצה","בבקשה"}', 'placeholder', 'emoji (Unicode)'),
  ('dont-want', 'dont-want.svg', 'לא רוצה', '{"לא רוצה","לא","מסרב"}', 'placeholder', 'emoji (Unicode)'),
  ('i', 'i.svg', 'אני', '{"אני","עצמי"}', 'placeholder', 'emoji (Unicode)'),
  ('you', 'you.svg', 'אתה', '{"אתה","את"}', 'placeholder', 'emoji (Unicode)'),
  ('eat', 'eat.svg', 'לאכול', '{"לאכול","אוכל","רעב","ארוחה"}', 'placeholder', 'emoji (Unicode)'),
  ('drink', 'drink.svg', 'לשתות', '{"לשתות","מים","צמא","שתייה"}', 'placeholder', 'emoji (Unicode)'),
  ('toilet', 'toilet.svg', 'שירותים', '{"שירותים","לשירותים","פיפי","קקי"}', 'placeholder', 'emoji (Unicode)'),
  ('help', 'help.svg', 'עזרה', '{"עזרה","עזור לי","צריך עזרה"}', 'placeholder', 'emoji (Unicode)'),
  ('hurt', 'hurt.svg', 'כואב', '{"כואב","כאב","אאוץ׳"}', 'placeholder', 'emoji (Unicode)'),
  ('play', 'play.svg', 'לשחק', '{"לשחק","משחק","צעצוע"}', 'placeholder', 'emoji (Unicode)'),
  ('break', 'break.svg', 'הפסקה', '{"הפסקה","מנוחה","לנוח"}', 'placeholder', 'emoji (Unicode)'),
  ('home', 'home.svg', 'בית', '{"בית","הביתה","ללכת הביתה"}', 'placeholder', 'emoji (Unicode)'),
  ('mom', 'mom.svg', 'אמא', '{"אמא","אימא"}', 'placeholder', 'emoji (Unicode)'),
  ('dad', 'dad.svg', 'אבא', '{"אבא"}', 'placeholder', 'emoji (Unicode)'),
  ('music', 'music.svg', 'מוזיקה', '{"מוזיקה","שיר","לשמוע"}', 'placeholder', 'emoji (Unicode)'),
  ('book', 'book.svg', 'ספר', '{"ספר","לקרוא","סיפור"}', 'placeholder', 'emoji (Unicode)'),
  ('ball', 'ball.svg', 'כדור', '{"כדור","לשחק בכדור"}', 'placeholder', 'emoji (Unicode)'),
  ('sleep', 'sleep.svg', 'לישון', '{"לישון","שינה","עייף","מיטה"}', 'placeholder', 'emoji (Unicode)'),
  ('hot', 'hot.svg', 'חם', '{"חם","חום"}', 'placeholder', 'emoji (Unicode)'),
  ('cold', 'cold.svg', 'קר', '{"קר","קור"}', 'placeholder', 'emoji (Unicode)'),
  ('happy', 'happy.svg', 'שמח', '{"שמח","שמחה","כיף"}', 'placeholder', 'emoji (Unicode)'),
  ('sad', 'sad.svg', 'עצוב', '{"עצוב","עצב","בוכה"}', 'placeholder', 'emoji (Unicode)'),
  ('angry', 'angry.svg', 'כועס', '{"כועס","כעס","רוגז"}', 'placeholder', 'emoji (Unicode)'),
  ('scared', 'scared.svg', 'מפחד', '{"מפחד","פחד","מפוחד"}', 'placeholder', 'emoji (Unicode)'),
  ('love', 'love.svg', 'אוהב', '{"אוהב","אהבה","אוהבת"}', 'placeholder', 'emoji (Unicode)'),
  ('finished', 'finished.svg', 'לסיים', '{"לסיים","סיימתי","גמרתי","נגמר"}', 'placeholder', 'emoji (Unicode)'),
  ('hello', 'hello.svg', 'שלום', '{"שלום","היי","להתראות"}', 'placeholder', 'emoji (Unicode)'),
  ('thanks', 'thanks.svg', 'תודה', '{"תודה","תודה רבה"}', 'placeholder', 'emoji (Unicode)'),
  ('wait', 'wait.svg', 'לחכות', '{"לחכות","רגע","המתנה"}', 'placeholder', 'emoji (Unicode)'),
  ('go', 'go.svg', 'ללכת', '{"ללכת","בוא","נלך"}', 'placeholder', 'emoji (Unicode)'),
  ('look', 'look.svg', 'להסתכל', '{"להסתכל","תראה","לראות"}', 'placeholder', 'emoji (Unicode)'),
  ('open', 'open.svg', 'לפתוח', '{"לפתוח","פתח"}', 'placeholder', 'emoji (Unicode)')
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- board_templates  (offered at child creation)
-- ---------------------------------------------------------------------------
insert into board_templates (id, name_he, level, description_he, spec) values
(
  'first-words', 'מילים ראשונות', 1,
  'שישה כרטיסים בסיסיים להתחלה.',
  '{"categories":[{"name":"בסיסי","color":"#1f6feb","cards":[
     {"label":"כן","symbol_id":"yes","grid_order":0},
     {"label":"לא","symbol_id":"no","grid_order":1},
     {"label":"עוד","symbol_id":"more","grid_order":2},
     {"label":"מספיק","symbol_id":"stop","grid_order":3},
     {"label":"רוצה","symbol_id":"want","grid_order":4},
     {"label":"עזרה","symbol_id":"help","grid_order":5}]}]}'::jsonb
),
(
  'basic-needs', 'צרכים בסיסיים', 2,
  'שתי קטגוריות — בסיסי ופעולות יומיומיות.',
  '{"categories":[
     {"name":"בסיסי","color":"#1f6feb","cards":[
       {"label":"כן","symbol_id":"yes","grid_order":0},
       {"label":"לא","symbol_id":"no","grid_order":1},
       {"label":"עוד","symbol_id":"more","grid_order":2},
       {"label":"מספיק","symbol_id":"stop","grid_order":3},
       {"label":"רוצה","symbol_id":"want","grid_order":4},
       {"label":"עזרה","symbol_id":"help","grid_order":5}]},
     {"name":"פעולות","color":"#1a7f37","cards":[
       {"label":"לאכול","symbol_id":"eat","grid_order":0},
       {"label":"לשתות","symbol_id":"drink","grid_order":1},
       {"label":"שירותים","symbol_id":"toilet","grid_order":2},
       {"label":"לישון","symbol_id":"sleep","grid_order":3},
       {"label":"לשחק","symbol_id":"play","grid_order":4},
       {"label":"הפסקה","symbol_id":"break","grid_order":5}]}]}'::jsonb
),
(
  'full-board', 'לוח מלא', 3,
  'ארבע קטגוריות — בסיסי, פעולות, רגשות, אנשים ומקומות.',
  '{"categories":[
     {"name":"בסיסי","color":"#1f6feb","cards":[
       {"label":"כן","symbol_id":"yes","grid_order":0},
       {"label":"לא","symbol_id":"no","grid_order":1},
       {"label":"עוד","symbol_id":"more","grid_order":2},
       {"label":"מספיק","symbol_id":"stop","grid_order":3},
       {"label":"רוצה","symbol_id":"want","grid_order":4},
       {"label":"לא רוצה","symbol_id":"dont-want","grid_order":5},
       {"label":"עזרה","symbol_id":"help","grid_order":6},
       {"label":"לסיים","symbol_id":"finished","grid_order":7}]},
     {"name":"פעולות","color":"#1a7f37","cards":[
       {"label":"לאכול","symbol_id":"eat","grid_order":0},
       {"label":"לשתות","symbol_id":"drink","grid_order":1},
       {"label":"שירותים","symbol_id":"toilet","grid_order":2},
       {"label":"לישון","symbol_id":"sleep","grid_order":3},
       {"label":"לשחק","symbol_id":"play","grid_order":4},
       {"label":"הפסקה","symbol_id":"break","grid_order":5},
       {"label":"מוזיקה","symbol_id":"music","grid_order":6},
       {"label":"ספר","symbol_id":"book","grid_order":7}]},
     {"name":"רגשות","color":"#9a6700","cards":[
       {"label":"שמח","symbol_id":"happy","grid_order":0},
       {"label":"עצוב","symbol_id":"sad","grid_order":1},
       {"label":"כועס","symbol_id":"angry","grid_order":2},
       {"label":"מפחד","symbol_id":"scared","grid_order":3},
       {"label":"אוהב","symbol_id":"love","grid_order":4},
       {"label":"כואב","symbol_id":"hurt","grid_order":5}]},
     {"name":"אנשים ומקומות","color":"#b42318","cards":[
       {"label":"אני","symbol_id":"i","grid_order":0},
       {"label":"אתה","symbol_id":"you","grid_order":1},
       {"label":"אמא","symbol_id":"mom","grid_order":2},
       {"label":"אבא","symbol_id":"dad","grid_order":3},
       {"label":"בית","symbol_id":"home","grid_order":4}]}]}'::jsonb
)
on conflict (id) do nothing;
