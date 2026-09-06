-- Reading & typing ("קריאה והקלדה") — level-based practice with milestone rewards.
--
-- Changes to the Phase-7 model:
--  * reading_texts / writing_prompts gain an optional child_id: NULL = bundled
--    global content (readable by everyone), a value = caregiver-authored for that
--    child. The caregiver editor writes child rows; RLS keeps them private.
--  * learning_completions is the "done" marker — a task, once completed, never
--    reappears (PK child_id+task_id).
--  * Tokens no longer flow per attempt. Every 3 completed tasks in the same
--    (kind, level) is a milestone worth a fixed 3 tokens, released only when the
--    caregiver enters their PIN. learning_reward_claims tracks how many
--    milestones have been paid.

-- ---------------------------------------------------------------------------
-- content: bundled (child_id NULL) + caregiver-authored (child_id set)
-- ---------------------------------------------------------------------------
alter table reading_texts
  add column child_id     uuid references children (id) on delete cascade,
  add column created_by   uuid references caregivers (id) on delete set null,
  add column tts_asset_id uuid references media_assets (id) on delete set null;
alter table writing_prompts
  add column child_id   uuid references children (id) on delete cascade,
  add column created_by uuid references caregivers (id) on delete set null;

-- caregiver rows get a generated id; bundled rows keep their slugs
alter table reading_texts   alter column id set default gen_random_uuid()::text;
alter table writing_prompts alter column id set default gen_random_uuid()::text;

drop policy reading_texts_read on reading_texts;
drop policy writing_prompts_read on writing_prompts;

create policy reading_texts_select on reading_texts for select to authenticated using (
  child_id is null
  or exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
);
create policy reading_texts_write on reading_texts for all to authenticated
  using (child_id is not null
    and exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (child_id is not null
    and exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

create policy writing_prompts_select on writing_prompts for select to authenticated using (
  child_id is null
  or exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
);
create policy writing_prompts_write on writing_prompts for all to authenticated
  using (child_id is not null
    and exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (child_id is not null
    and exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

grant insert, update, delete on reading_texts, writing_prompts to authenticated;

-- ---------------------------------------------------------------------------
-- learning_completions — the "done" marker; a completed task never reappears
-- ---------------------------------------------------------------------------
create table learning_completions (
  child_id     uuid not null references children (id) on delete cascade,
  task_id      text not null,        -- reading_texts.id | writing_prompts.id
  kind         text not null,        -- 'reading' | 'writing'
  level        integer not null,
  completed_at timestamptz not null default now(),
  primary key (child_id, task_id)
);
create index learning_completions_progress_idx on learning_completions (child_id, kind, level);
alter table learning_completions enable row level security;
create policy learning_completions_owner_all on learning_completions for all
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));
grant select, insert on learning_completions to authenticated;

-- ---------------------------------------------------------------------------
-- learning_reward_claims — how many 3-task milestones have been paid, per level
-- ---------------------------------------------------------------------------
create table learning_reward_claims (
  child_id   uuid not null references children (id) on delete cascade,
  kind       text not null,
  level      integer not null,
  claimed    integer not null default 0,
  updated_at timestamptz not null default now(),
  primary key (child_id, kind, level)
);
alter table learning_reward_claims enable row level security;
create policy learning_reward_claims_owner_all on learning_reward_claims for all
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));
grant select, insert, update on learning_reward_claims to authenticated;

-- ---------------------------------------------------------------------------
-- Bundled graded content — ~10 reading texts and ~10 typing prompts per level.
-- ---------------------------------------------------------------------------
insert into reading_texts (id, level, title, body) values
  ('r1-sun',   1, 'השמש',   'השמש זורחת. השמש חמה וצהובה. אני שמח בשמש.'),
  ('r1-dog',   1, 'הכלב',   'לכלב יש זנב. הכלב נובח. הכלב רץ בחצר.'),
  ('r1-cake',  1, 'העוגה',  'אמא אפתה עוגה. העוגה מתוקה. אני אוכל פרוסה.'),
  ('r1-fish',  1, 'הדג',    'לדג יש סנפיר. הדג שוחה במים. הדג קטן וכסוף.'),
  ('r1-flow',  1, 'הפרח',   'הפרח אדום. הפרח ריחני. אני שם פרח באגרטל.'),
  ('r1-bus',   1, 'האוטובוס', 'האוטובוס גדול. אני נוסע באוטובוס לגן. האוטובוס עוצר בתחנה.'),
  ('r1-rain',  1, 'הגשם',   'יורד גשם. אני לובש מעיל. אני קופץ בשלולית.'),
  ('r1-friend',1, 'החבר',   'בא אליי חבר. שיחקנו יחד בכדור. היה לנו כיף.'),
  ('r1-book',  1, 'הספר',   'אני אוהב ספר. בספר יש תמונות. אמא קוראת לי סיפור.'),
  ('r1-night', 1, 'הלילה',  'בלילה חשוך. הכוכבים מאירים. אני ישן במיטה.'),
  ('r2-morning', 2, 'בוקר בגן', 'בבוקר קמתי מוקדם. צחצחתי שיניים ואכלתי דגני בוקר. לבשתי בגדים והלכתי לגן עם אבא.'),
  ('r2-garden',  2, 'הגינה שלנו', 'בגן שלנו יש גינה קטנה. שתלנו בה עגבניות ותות. כל בוקר אנחנו משקים את הצמחים ובודקים אם גדלו.'),
  ('r2-bday',    2, 'יום הולדת', 'אתמול היה יום הולדת לאחותי. תלינו בלונים צבעוניים בכל הבית. היא קיבלה אופניים חדשים ושמחה מאוד.'),
  ('r2-sea',     2, 'ארמון בחול', 'יצאנו לים בסוף השבוע. בנינו ארמון גדול מחול והוספנו לו דגל. הגלים הגיעו ומחקו חלק מהחומה, אז בנינו אותה שוב.'),
  ('r2-guest',   2, 'אורח בכיתה', 'לכיתה שלנו הגיע אורח מיוחד. הוא סיפר לנו על ציפורים נודדות ואיך הן מוצאות את הדרך. אחר כך יצאנו לחצר לחפש קנים.'),
  ('r2-shelf',   2, 'מדף חדש', 'אבא הרכיב לי מדף בחדר. הוא מדד את הקיר, סימן בעיפרון וקדח שני חורים. עכשיו כל הספרים שלי מסודרים במקום אחד.'),
  ('r2-hike',    2, 'עולים על ההר', 'בטיול השנתי עלינו על הר גבוה. הדרך הייתה תלולה ונשמנו חזק, אבל מלמעלה ראינו את כל העיר קטנה מתחתינו.'),
  ('r2-seed',    2, 'הזרע שנבט', 'המורה חילקה לנו זרעים של חמנייה. שמנו כל זרע בכוס עם אדמה ליד החלון. אחרי שבוע הציץ נבט ירוק קטן.'),
  ('r2-picnic',  2, 'פיקניק בערב', 'בערב עשינו פיקניק בגינה. פרשנו שמיכה על הדשא ואכלנו כריכים. כשהחשיך הדלקנו פנס וספרנו סיפורים.'),
  ('r2-kittens', 2, 'הגורים', 'החתולה שלנו הביאה גורים. הם קטנים ורכים ועדיין לא פוקחים עיניים. אנחנו שומרים עליהם בשקט כדי שלא ייבהלו.'),
  ('r3-spring', 3, 'המעיין שבהרים', 'ביום שישי בבוקר יצאנו כל המשפחה לטיול אל מעיין שבין ההרים. הדרך הייתה ארוכה ומפותלת, וכמעט ויתרנו באמצע, אבל כשהגענו גילינו בריכה צלולה שמימיה קרים כקרח. טבלנו את הרגליים, אכלנו ארוחת בוקר על סלע שטוח, וראינו נשר גדול חג במעגלים איטיים מעל העמק.'),
  ('r3-grandma', 3, 'הימים של סבתא', 'הסבתא שלי מספרת שכשהייתה ילדה לא היו טלפונים ולא מחשבים. בערבים הילדים היו נפגשים ברחוב, ממציאים משחקים מאבנים ומקלות, ומקשיבים לרדיו הישן שעמד במטבח. היא אומרת שלמרות שהיה פחות, היא זוכרת את הימים ההם כמלאים ומאושרים.'),
  ('r3-commgarden', 3, 'גינה קהילתית', 'בכיתה החלטנו להקים גינה קהילתית בשטח נטוש ליד בית הספר. פינינו אבנים ופסולת, הבאנו אדמה טובה בשקים כבדים, ובנינו ערוגות מלוחות עץ. כל תלמיד קיבל פינה משלו לטפח. חודשיים אחר כך המקום היה מלא ירק, פרפרים והמון גאווה.'),
  ('r3-snow', 3, 'בוקר של שלג', 'כשהתעוררתי בבוקר ראיתי שהעולם בחוץ הפך לבן. שלג נדיר ירד בלילה וכיסה את הגגות, את המכוניות ואת ענפי העצים. יצאנו החוצה בכפפות ובמגפיים, גלגלנו כדור ענק והפכנו אותו לאיש שלג עם גזר לאף. הידיים קפאו אבל אף אחד לא רצה להיכנס הביתה.'),
  ('r3-tracks', 3, 'עקבות ביער', 'המדריך בטיול לימד אותנו לזהות עקבות של חיות באדמה הרכה. ראינו טביעות קטנות של שועל שחצה את השביל בלילה, וטביעות גדולות יותר של חזיר בר ליד הנחל. הוא הסביר שכל חיה משאירה סימן משלה, ושאם לומדים להתבונן אפשר לקרוא את הסיפור של היער בלי לראות אף חיה.'),
  ('r3-bike', 3, 'רוכב לבד', 'אחי הגדול לימד אותי לרכוב על אופניים בלי גלגלי עזר. בהתחלה נפלתי שוב ושוב והברכיים נשרטו, ורציתי לוותר. הוא רץ לצידי ואחז בכיסא, ואז, בלי שהרגשתי, שחרר את היד. פתאום הבנתי שאני נוסע לבד, והרוח נשבה בפנים שלי כמו כנפיים.'),
  ('r3-library', 3, 'סיפור בספרייה', 'בספרייה של השכונה יש פינה שקטה עם כריות גדולות. בכל יום רביעי אחרי הצהריים הספרנית קוראת בקול סיפור לילדים שמתאספים סביבה. היא משנה את הקול לכל דמות, עוצרת ברגעים המרתקים, ולפעמים מבקשת מאיתנו לנחש מה יקרה. יצאתי משם עם שלושה ספרים חדשים בתיק.'),
  ('r3-turtle', 3, 'צב על החוף', 'בחוף הים מצאנו צב ים פצוע ליד הסלעים. לא נגענו בו, אלא התקשרנו למוקד הצלה כמו שלימדו אותנו. אנשים באו עם ארגז מיוחד ומים, בדקו את השריון בעדינות, והבטיחו שיטפלו בו במרכז ההצלה עד שיוכל לחזור לים. חזרנו הביתה עייפים אבל מרוצים.'),
  ('r3-village', 3, 'קיץ בכפר', 'בכל קיץ אנחנו נוסעים לשבוע אצל דוד שלי בכפר. שם קמים עם הזריחה, אוספים ביצים מהלול, ומאכילים את העז שקוראים לה נמרה. אחר הצהריים חם מדי לצאת, אז יושבים בצל התאנה, שוברים אגוזים ומקשיבים לזמזום הדבורים. אלה השבועות הכי טובים בשנה.'),
  ('r3-moon', 3, 'הירח בטלסקופ', 'המורה למדעים הביאה לכיתה טלסקופ קטן. חיכינו עד שהחשיך, כיוונו אותו אל הירח, וכל אחד הציץ בתורו. במקום עיגול חלק ראינו הרים, בקעות ומכתשים עגולים. קשה להאמין שהדבר הרחוק הזה, שנראה כל לילה קטן כמו מטבע, הוא עולם שלם משלו.')
on conflict (id) do nothing;

insert into writing_prompts (id, level, hint, target) values
  ('w1-shalom', 1, 'כתבו: שלום', 'שלום'),
  ('w1-ima',    1, 'כתבו: אמא',  'אמא'),
  ('w1-aba',    1, 'כתבו: אבא',  'אבא'),
  ('w1-bayit',  1, 'כתבו: בית',  'בית'),
  ('w1-yeled',  1, 'כתבו: ילד',  'ילד'),
  ('w1-kelev',  1, 'כתבו: כלב',  'כלב'),
  ('w1-hatul',  1, 'כתבו: חתול', 'חתול'),
  ('w1-shemesh',1, 'כתבו: שמש',  'שמש'),
  ('w1-mayim',  1, 'כתבו: מים',  'מים'),
  ('w1-sefer',  1, 'כתבו: ספר',  'ספר'),
  ('w2-dograts',2, 'כתבו: הכלב רץ',        'הכלב רץ'),
  ('w2-sun',    2, 'כתבו: השמש זורחת',      'השמש זורחת'),
  ('w2-play',   2, 'כתבו: אני אוהב לשחק',   'אני אוהב לשחק'),
  ('w2-soup',   2, 'כתבו: אמא בישלה מרק',   'אמא בישלה מרק'),
  ('w2-read',   2, 'כתבו: הילד קורא ספר',   'הילד קורא ספר'),
  ('w2-flower', 2, 'כתבו: הפרח יפה מאוד',   'הפרח יפה מאוד'),
  ('w2-gan',    2, 'כתבו: אנחנו הולכים לגן', 'אנחנו הולכים לגן'),
  ('w2-rain',   2, 'כתבו: הגשם יורד בחוץ',  'הגשם יורד בחוץ'),
  ('w2-cat',    2, 'כתבו: החתול ישן על הספה', 'החתול ישן על הספה'),
  ('w2-water',  2, 'כתבו: אני שותה מים קרים', 'אני שותה מים קרים'),
  ('w3-learn',  3, 'כתבו: אני אוהב ללמוד דברים חדשים',        'אני אוהב ללמוד דברים חדשים'),
  ('w3-bread',  3, 'כתבו: בבוקר אכלתי לחם עם גבינה',           'בבוקר אכלתי לחם עם גבינה'),
  ('w3-ball',   3, 'כתבו: אחרי הצהריים שיחקנו בכדור בפארק',    'אחרי הצהריים שיחקנו בכדור בפארק'),
  ('w3-story',  3, 'כתבו: סבתא סיפרה לי סיפור לפני השינה',      'סבתא סיפרה לי סיפור לפני השינה'),
  ('w3-birds',  3, 'כתבו: בטיול ראינו ציפורים רבות בשמיים',    'בטיול ראינו ציפורים רבות בשמיים'),
  ('w3-doctor', 3, 'כתבו: כשאגדל אני רוצה להיות רופא',          'כשאגדל אני רוצה להיות רופא'),
  ('w3-count',  3, 'כתבו: המורה לימדה אותנו לספור עד מאה',      'המורה לימדה אותנו לספור עד מאה'),
  ('w3-visit',  3, 'כתבו: בסוף השבוע נסענו לבקר את הדודים',     'בסוף השבוע נסענו לבקר את הדודים'),
  ('w3-card',   3, 'כתבו: הכנתי כרטיס ברכה ליום ההולדת של אחי', 'הכנתי כרטיס ברכה ליום ההולדת של אחי'),
  ('w3-water',  3, 'כתבו: אנחנו שומרים על הגינה ומשקים את הפרחים', 'אנחנו שומרים על הגינה ומשקים את הפרחים')
on conflict (id) do nothing;
