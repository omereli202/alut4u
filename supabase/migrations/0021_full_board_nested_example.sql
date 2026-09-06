-- Give the "לוח מלא" starter board one real nested branch so a caregiver who
-- picks it at child creation sees how categories nest:
--   אוכל ‹ פירות ‹ (תפוח, בננה)
--        ‹ ירקות ‹ (גזר, בצל, תפוח אדמה)
-- All symbols here are from the production-cleared Mulberry set (0011/0013).
-- board_templates.apply_to_child walks `categories` recursively.

update board_templates set
  description_he = 'חמש קטגוריות — בסיסי, פעולות, רגשות, אנשים ומקומות, ואוכל (עם תת-קטגוריות).',
  spec = '{"categories":[
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
       {"label":"בית","symbol_id":"home","grid_order":4}]},
     {"name":"אוכל","color":"#1a7f37","symbol_id":"fried-breakfast","categories":[
       {"name":"פירות","color":"#1a7f37","symbol_id":"apple","cards":[
         {"label":"תפוח","symbol_id":"apple","grid_order":0},
         {"label":"בננה","symbol_id":"banana","grid_order":1}]},
       {"name":"ירקות","color":"#1a7f37","symbol_id":"carrot","cards":[
         {"label":"גזר","symbol_id":"carrot","grid_order":0},
         {"label":"בצל","symbol_id":"onion","grid_order":1},
         {"label":"תפוח אדמה","symbol_id":"potato","grid_order":2}]}]}]}'::jsonb
where id = 'full-board';
