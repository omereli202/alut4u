# Design brief — Google Stitch

This file is the hand-off to **Google Stitch** (stitch.withgoogle.com) for the
final visual styling of alut4u. Stitch cannot see this repo, so everything it
needs is written out here: the product, the users, the accessibility rules it
must not break, the design system, and one prompt per screen.

The app is fully built and functional — every screen listed here already exists
in `frontend/js/`. What is missing is the *look*. `frontend/css/tokens.css` and
`frontend/css/components/app.css` are deliberate placeholders ("Plain and
accessible; the Stitch visual pass replaces these values later").

**Workflow:** generate screens in Stitch → export → apply the three passes in
§6 → the palette lands in `tokens.css`, the layout in `app.css`.

> **Status:** two exports have landed — `docs/design/stitch-export/` (14
> screens: AAC board, editor, schedule, rewards, dialogs, recorder) and
> `docs/design/stitch-export-2/` (10 more: PIN inline gate, boot screen,
> shared states, reading/writing, story reader). Each folder's README maps
> its screens to a §4 ID and records what it confirmed vs. changed. The
> foundation pass (tokens, icon set, dialog component) and a per-screen
> layout pass covering both exports' screens are both done. Still open — see
> `docs/launch-checklist.md`: home, dashboard, AAC card form, schedule
> editor, calming, sign-in/up, and the full PIN keypad have no reference art
> from either export yet.

---

## §0 — How to use this file

1. **Theme prompt, once.** Paste §1 (product context) followed by §3 (design
   system) into a new Stitch project as the app description / theme. Let Stitch
   propose a palette. Save the theme.
2. **One screen at a time.** For each screen in §4, paste its fenced prompt.
   Work the tiers in order — **Tier 1 first**: those five screens fix the visual
   language, and everything after them should reuse it.
3. **Mode.** Use Stitch **Experimental / high-effort** mode for the five Tier 1
   screens. **Standard** mode is fine for Tiers 2–3.
4. **Iterate with short follow-ups** ("make the cards 20% larger", "more spacing
   between rows") rather than re-pasting the whole prompt.
5. **Copy is Hebrew, RTL.** Every prompt states the visible Hebrew strings
   inline and repeats them in a strings table. If Stitch outputs English
   placeholder text, that is fine for judging layout — the real strings are
   already in the code; §6 pass 1 handles direction and typography.
6. **Export** to Figma or HTML/CSS and hand off to §6.
7. Stitch's hex palette goes into `frontend/css/tokens.css` **and nowhere
   else** (§6 pass 2).

---

## §1 — Product context

> alut4u is an accessible AAC (Augmentative & Alternative Communication) and
> daily-support app for children on the autism spectrum and their caregivers.
> It is **Hebrew only** and **right-to-left**.
>
> It has two faces on one device:
>
> - **User Mode** — what the child uses. The device is a locked-down kiosk
>   tablet (iPadOS Guided Access / Android Screen Pinning). Large touch targets,
>   very little on screen at once, no clutter, calm colours, no way out of the
>   app. The child taps picture cards to build and speak sentences, follows a
>   visual daily schedule, earns tokens, listens to calming sounds, reads short
>   social stories, and practises reading and writing.
> - **Caregiver Mode** — a parent or therapist, behind a 4-digit PIN. Normal
>   information density: lists, forms, editors. They enable modules per child,
>   edit the communication board, build schedules, award tokens, approve reward
>   requests, and generate social stories.
>
> Primary device: a 10-inch tablet, landscape, held or on a stand. Secondary: a
> phone in portrait. The layout must work at both. It is a PWA that works
> offline for the communication board and the schedule.

---

## §2 — Design principles (non-negotiable)

These come from `docs/accessibility.md`. The child users are on the autism
spectrum — this is a core requirement, not polish.

1. **Low arousal.** Muted, low-saturation colour. Generous whitespace. Few
   elements per screen in User Mode. No visual noise, no decoration that isn't
   information.
2. **Big targets.** Every interactive element in User Mode is at least **60×60
   px**. Tiles and cards are much larger.
3. **No flashing, ever.** Nothing blinks or strobes. Nothing above 3 changes per
   second. (Seizure risk.)
4. **No motion tricks.** No parallax, no auto-advancing carousels, no content
   that moves on its own. Transitions are short and gentle and must degrade to
   nothing under `prefers-reduced-motion`.
5. **Predictable.** The same control is in the same place on every screen. The
   top bar, the back/exit control, the sentence bar — all fixed positions. No
   surprise navigation.
6. **Never show the child failure.** No error-red, no ✗-as-punishment, no "wrong"
   state in User Mode. A missed reading attempt shows encouragement ("עוד נתרגל
   יחד"), not a red X meaning. Red (`--color-danger`) is **caregiver-only**, for
   destructive actions like deleting a card.
7. **Visible focus.** A high-contrast focus ring on every focusable element,
   always. Never removed without a stronger replacement.
8. **Real semantics.** Real `<button>` / `<a>`, not clickable `<div>`s. Status
   messages in polite live regions.
9. **Audio never autoplays.** Sound only follows a tap. The one loop that exists
   (calming sounds) starts on an explicit play press.

---

## §3 — Design system (paste after §1 as the theme)

### Palette — you choose the values, we keep the names

Produce a palette that fills **exactly these semantic roles** (they are CSS
custom-property names already wired through the app). Return your choice as a
table keyed by these names, **with a light value and a dark value for every
one**:

| Token | Role |
|---|---|
| `--color-bg` | page background |
| `--color-surface` | card / panel background, one step off `--color-bg` |
| `--color-text` | primary text |
| `--color-text-muted` | secondary text, hints, timestamps |
| `--color-primary` | the single accent — primary buttons, active tab, selected state |
| `--color-primary-contrast` | text/icon on top of `--color-primary` |
| `--color-success` | calm green — completion, celebration, "+N tokens" |
| `--color-warning` | amber — mild caution (caregiver side) |
| `--color-danger` | red — **caregiver-only** destructive actions |
| `--color-focus` | the focus ring; must stand out on both `--color-bg` and `--color-surface` |
| `--color-border` | hairline dividers, input borders, card outlines |

Constraints:

- **Low saturation.** Calm, quiet hues. A soft neutral or muted blue-green base
  is a good direction. No neon, no pure `#000` or `#fff`.
- **One accent.** `--color-primary` is the only strong colour, used sparingly.
- **Success is green and gentle** — reassuring, not a bright "correct!" green.
- **Every text-on-background pair meets WCAG AA**: ≥ 4.5:1 for body text, ≥ 3:1
  for large text and UI borders. State the ratios for the main pairs.
- **No gradients, no glassmorphism, no drop-shadow-heavy "floating" cards.**
  Depth comes from the fixed shadow tokens below, used lightly.
- The dark palette is a genuine dark theme (dark `--color-bg`), not an inverted
  light one — but it keeps the same calm, low-contrast-of-hue character.

### Typography

- **Hebrew-first font stack:** `"Rubik", "Assistant", "Heebo", system-ui, sans-serif`.
  Rubik is the primary. Design with Hebrew glyphs (no uppercase, no
  ascenders/descenders the way Latin has them).
- **Type scale — fixed, use these:**

  | Token | Size | Use |
  |---|---|---|
  | `--text-sm` | 0.9rem | captions, timestamps |
  | `--text-base` | 1.125rem | body, form labels |
  | `--text-lg` | 1.4rem | card labels, section headings (`h2`/`h3`) |
  | `--text-xl` | 1.9rem | screen titles in caregiver mode |
  | `--text-2xl` | 2.6rem | screen titles and focus text in User Mode |

- **Line-height:** Hebrew needs *less* leading than Latin at the same size —
  about 1.4 for body, 1.15 for large headings. Do not over-space lines.
- Left-align is wrong here. Text aligns to the **inline-start**, which is the
  **right** edge.

### Spacing, radii, shadows — fixed, compose with these

- Spacing steps: `--space-1` 0.25rem, `--space-2` 0.5rem, `--space-3` 0.75rem,
  `--space-4` 1rem, `--space-6` 1.5rem, `--space-8` 2rem, `--space-12` 3rem.
- Radii: `--radius-sm` 6px (inputs, chips), `--radius-md` 12px (buttons, cards),
  `--radius-lg` 20px (tiles, large touch cards, modals).
- Shadows — use lightly: `--shadow-1` `0 1px 3px rgba(0,0,0,.12)` (resting card),
  `--shadow-2` `0 4px 16px rgba(0,0,0,.16)` (modal, raised control).

### Two densities from one system

The app switches density by a `data-mode` attribute on each screen's root:

- `data-mode="user"` — **child-facing.** Fewer, bigger elements. Titles at
  `--text-2xl`. Minimum 60px touch targets, usually much larger. Lots of
  breathing room. This is most of the screens in §4 group B.
- `data-mode="caregiver"` — **adult-facing.** Normal app density. Lists with
  many rows, multi-field forms, tables of transactions. Titles at `--text-xl`.
  Comfortable but efficient. §4 group C.

Same palette, same type scale, same components — only spacing, sizing and
information density differ.

### Components — render these identically on every screen

**Already in the app:**

- **Primary button** (`.btn-primary`) — filled `--color-primary`, `--radius-md`,
  full-width on narrow screens. Has a visible `:disabled` state (lower opacity,
  no shadow).
- **Secondary / link button** (`.btn-link`) — quiet, text-weight, underline or
  subtle border. Used for "back", "cancel", tab-like navigation.
- **Destructive link button** (`.btn-link.danger`) — same shape, `--color-danger`
  text. Caregiver mode only.
- **Module tile** (`.tile`) — large square-ish card, icon + Hebrew label, min
  120px tall, `--radius-lg`. The User-Mode home grid.
- **AAC card** (`.aac-card`) — picture on top, Hebrew label below, `--radius-md`,
  strong press-down feedback on `:active`. Sits in a CSS-grid whose column count
  the child changes from 2 to 5.
- **List row** (`.editor-card-row`, `.sched-row`, `.lesson-item`) — thumbnail +
  primary text + optional trailing time/meta + trailing action buttons. A
  `.done` variant (checked, dimmed, strike or check).
- **Text input** (`.field input`), **select** (`.field select`), **checkbox**
  (`.checkbox`), **toggle row** (`.toggle` — label + switch, one per module).
- **Chip** (`.chip`) — small rounded pill; `.chip.active` for the selected child
  in the switcher and for sentence-bar words.
- **Tab bar** (`.cat-tabs` / `.cat-tab`) — horizontal, scrollable, one `.active`.
  Used for AAC categories, rules/rewards, calming modes, reading/writing.
- **Top bar** (`.aac-topbar`) — fixed strip: exit control (inline-start), screen
  title (centre), one contextual control (inline-end, e.g. grid size, month,
  token badge).
- **Token badge** (`.token-badge`) — star icon + number, top-inline-end. Also a
  `.queue-badge` variant on the caregiver dashboard (pending reward count).
- **Toast** (`.toast` / `.toast-error`) — transient status, bottom-centre, auto
  dismiss ~4s. `role="status"`. The only existing overlay.
- **Empty state** — centred icon + one muted line of Hebrew, optionally a
  `.btn-link` back.
- **Focus ring** — 3px solid `--color-focus`, 2px offset, on `:focus-visible`.

**Commission these — the app needs them and has none:**

- **`dialog`** — a real modal to replace native `confirm()`. Centred card,
  `--shadow-2`, `--radius-lg`, dimmed backdrop, title + body + two buttons
  (cancel = `.btn-link`, confirm = `.btn-primary`). Focus-trapped, closes on a
  clearly visible control (Esc and backdrop-tap also close). Title/body Hebrew.
- **`dialog.destructive`** — same, confirm button is `--color-danger`. For "hide
  profile", "delete card", "delete category".
- **`dialog.type-to-confirm`** — same, plus a text input the user must type a
  literal word into (`DELETE`) before the confirm button enables. For account
  deletion only.
- **`pin`** — one PIN component, two sizes:
  - **`pin.keypad`** (large) — 4 dots + a 3×4 grid of digit keys (1–9, then a
    blank slot / `0` / backspace), each key ≥ 64px. Auto-submits on the 4th
    digit. An error line clears the dots. Optional cancel in the blank slot.
    Used for setting the PIN and unlocking Caregiver Mode.
  - **`pin.inline`** (small) — a single 4-digit field + a confirm button,
    inline in a page. Used for the reading-verdict gate.
  Both are `dir="ltr"` internally (digits read left-to-right) even though the
  page is RTL.

### Icon set — commission ~20 glyphs, replace the emoji

The app currently uses raw emoji for every action (🔒 ✕ ⭐ 🎉 📖 🌧️ ▶ ⏸ ⏹ ⌫ 🎙 🔊 ✓
✗ 💪 📅 → ←). Emoji render differently on every OS, ignore `currentColor` and the
focus ring, and read inconsistently to screen readers — unacceptable on a shared
kiosk. Design a single coherent set:

`lock · close · star · check · cross · play · pause · stop · backspace · mic ·
speaker · calendar · book · chevron-prev · chevron-next · plus · trash · drag ·
edit · settings · party (celebration)`

Rules: one stroke weight, two sizes (24px UI, 40px User-Mode actions), drawn on
a square grid, inherit `currentColor`, no built-in colour. **Directional icons
(prev/next, backspace) are mirrored for RTL** — "next" points left.

Emoji that are *content the child reads* (calming-track glyphs, story-cover
mark) may stay as illustration; emoji that are *controls* must become icons.

---

## §4 — Screen catalogue

Each block: **screen · mode · repo file · how it's reached** (there is no URL
routing — navigation is imperative), then a fenced prompt, a Hebrew strings
table, required elements, and extra states.

### Tier 1 — generate first; these fix the visual language

---

#### T1.1 — AAC communication board

- **Mode:** User · **File:** `frontend/js/modules/aac/board.js` · **Reached:** child taps the בוא נדבר tile on the home screen.

```
A full-screen communication board for a non-speaking child, Hebrew, right-to-left,
on a 10-inch tablet in landscape. Calm and uncluttered.

Top bar, fixed: an exit icon button on the right (label "יציאה"), the child's
name centred as the title, and on the left a small stepper labelled "גודל הרשת"
with a minus button, a number, and a plus button (it changes the grid from 2 to
5 columns).

Directly under the top bar: a sentence bar spanning the full width — a light
raised strip, at least 76px tall, holding a horizontal row of word chips the
child has tapped, and on its left three buttons: a large "הקראה" play button
(primary colour), a backspace button, and a "נקה" clear button. When no words
are chosen the three buttons look disabled and the strip is empty.

Under the sentence bar: a horizontal scrollable row of category tabs
(e.g. "אוכל", "רגשות", "פעילויות"), one selected. Each tab carries a small colour
dot from that category.

Below that, filling the rest of the screen: a grid of communication cards,
currently 3 columns. Each card is a rounded tile with a picture symbol filling
the top two-thirds and a Hebrew word label below it (e.g. "עוד", "בבקשה", "כן",
"מים"). Big, evenly spaced, obvious press-down feedback.

Muted palette, one accent colour on the play button and the active tab only.
No gradients. Large touch targets everywhere.
```

| Hebrew | Meaning |
|---|---|
| `יציאה` | exit |
| `גודל הרשת` | grid size |
| `הקראה` | speak aloud |
| `נקה` | clear |
| (card labels) | `עוד` more, `בבקשה` please, `כן` yes, `לא` no, `מים` water |

**Must include:** fixed top bar; sentence bar with chips + speak/backspace/clear;
category tab strip; responsive card grid driven by a `--cols` variable (2–5).
**Also generate:** the load-error state (T3.5) and a phone-portrait layout.

---

#### T1.2 — Sentence bar (component detail)

- **Mode:** User · **File:** `frontend/js/modules/aac/sentence-bar.js` · **Reached:** persistent inside the AAC board.

```
Close-up of the sentence-building bar from a child's communication board, Hebrew
RTL. A full-width raised strip. On the right, a horizontal row of word chips,
each a rounded pill with a Hebrew word and a small remove "x"; chips fill from
the right. On the left, three controls in a row: a prominent circular "הקראה"
(speak) button in the accent colour with a play icon, a backspace icon button,
and a "נקה" (clear) text button. Show two versions: one with four chips
("אני", "רוצה", "עוד", "מים"), and one empty with all three controls visibly
disabled.
```

| Hebrew | Meaning |
|---|---|
| `הקראה` | speak | 
| `נקה` | clear |
| `הסר {מילה}` | "remove {word}" (chip aria-label) |

**Must include:** chips growing from inline-start=right; disabled state.

---

#### T1.3 — User Mode home

- **Mode:** User · **File:** `frontend/js/views/home.js` · **Reached:** landing screen after sign-in + PIN onboarding.

```
The home screen of a children's tablet app, Hebrew, right-to-left, landscape.
Very calm, very sparse.

A small lock icon button pinned in the top corner on the left (label "מצב מטפל"),
this is the only way an adult leaves to the settings area.

If there is more than one child profile: a single row of name chips near the top,
one highlighted.

A large friendly greeting headline: "שלום, נועה".

Below it, centred, a grid of 2–6 big square tiles — this is the whole screen.
Each tile is a large rounded card with a simple line icon and a Hebrew label:
"בוא נדבר", "סדר יום", "הכללים שלי", "פינת רוגע", "סיפורים חברתיים",
"תרגול קריאה וכתיבה". Tiles are big enough to hit easily, generously spaced, muted
colours, gentle press feedback. No other navigation, no bottom bar, no clutter.
```

| Hebrew | Meaning |
|---|---|
| `מצב מטפל` | caregiver mode |
| `שלום, {שם}` | Hello, {name} |
| `בוא נדבר` | Let's talk |
| `סדר יום` | Daily routine |
| `הכללים שלי` | My rules |
| `פינת רוגע` | Calming corner |
| `סיפורים חברתיים` | Social stories |
| `תרגול קריאה וכתיבה` | Reading & writing practice |

**Must include:** corner lock button; optional child-switch chip row; tile grid
(2–6 tiles, responsive). **Also generate:** the no-children empty state — same
frame, headline `ברוכים הבאים`, one muted line `מטפל צריך להוסיף פרופיל חבר/ה
במצב מטפל.`, no tiles.

---

#### T1.4 — Caregiver dashboard

- **Mode:** Caregiver · **File:** `frontend/js/views/dashboard.js` · **Reached:** after entering the PIN.

```
The settings dashboard for a parent/therapist in a child-support app, Hebrew,
right-to-left. Normal app density — this is the adult side.

Header: title "מצב מטפל" on the right. On the left, optionally a small badge
showing a number and a star (pending reward requests), and a quiet text button
"יציאה ממצב מטפל".

Main content, a single column of cards:

1. Section heading "חברים". Then one card per child. Each child card has the
   child's name as a heading, then a vertical list of six labelled toggle
   switches: "בוא נדבר (AAC)", "סדר יום", "הכללים שלי", "פינת רוגע",
   "סיפורים חברתיים", "תרגול קריאה וכתיבה". Below the toggles, a row of quiet action
   buttons that appear only for enabled modules: "ערוך לוח תקשורת",
   "ערוך לוח זמנים", "כללים ואסימונים", "סיפורים חברתיים", and a red text button
   "הסתרת פרופיל".

2. A card titled "הוספת חבר/ה" — a small form: a text field "שם", a select
   "בסיס להסכמה", and a primary button "הוספה".

3. Section heading "החשבון שלי". A card with: a link "הורדת כל הנתונים שלי (JSON)",
   a red text button "מחיקת החשבון וכל הנתונים", a divider, and a quiet button
   "התנתקות מהמכשיר".

Calm palette, the accent colour only on primary buttons and active toggles. Red
only on the two destructive text buttons.
```

| Hebrew | Meaning |
|---|---|
| `מצב מטפל` | Caregiver mode |
| `יציאה ממצב מטפל` | Exit caregiver mode |
| `חברים` | Friends |
| `החשבון שלי` | My account |
| `הוספת חבר/ה` | Add a friend |
| toggle labels | see T1.4 prompt |
| `הסתרת פרופיל` | Hide profile |
| `הורדת כל הנתונים שלי (JSON)` | Download all my data (JSON) |
| `מחיקת החשבון וכל הנתונים` | Delete account and all data |
| `התנתקות מהמכשיר` | Sign out of this device |

**Must include:** header with optional queue badge; repeating child card with
toggle list + conditional action row; add-child form card; account card.
**Also generate:** empty state (`עדיין לא נוספו חברים.`).

---

#### T1.5 — AAC card form (add / edit a card)

- **Mode:** Caregiver · **File:** `frontend/js/modules/aac/editor.js` (`openCardForm`) · **Reached:** "+ הוסף כרטיס" or "ערוך" in the AAC editor. Full-screen, not an overlay.

```
A form for a parent to create one picture card for a child's communication board,
Hebrew, right-to-left. Full screen, adult density.

Heading "כרטיס חדש" (or "עריכת כרטיס" when editing).

Fields, stacked:
- text field "מילה / תווית"
- text field "טקסט להקראה (רשות)"
- label "תמונה:" then a preview box (shows the chosen symbol, or a muted "אין
  תמונה" when empty)
- a symbol picker: a search field "חיפוש סמל…" and a grid of symbol thumbnails
  below it
- a file row "או העלאת תמונה משלך:" with a file-choose control
- an audio row: label "קול:", a status word, a text button "הקלטה" with a mic
  icon, and (when a recording exists) a "הסר הקלטה" button

Footer: a primary "שמור" button and a quiet "ביטול" button. An error line can
appear above the footer.

Clean, calm, single column, comfortable spacing.
```

| Hebrew | Meaning |
|---|---|
| `כרטיס חדש` / `עריכת כרטיס` | New card / Edit card |
| `מילה / תווית` | Word / label |
| `טקסט להקראה (רשות)` | Text to speak (optional) |
| `תמונה:` | Image: |
| `אין תמונה` | No image |
| `חיפוש סמל…` | Search symbol… |
| `או העלאת תמונה משלך:` | Or upload your own image: |
| `קול:` | Voice: |
| `הקלטה` | Record |
| `הסר הקלטה` | Remove recording |
| `שמור` / `ביטול` | Save / Cancel |

**Must include:** the two text fields, symbol preview, embedded symbol picker,
file-upload row, audio row, sticky footer actions, inline error slot.

---

### Tier 2 — module surfaces

---

#### T2.1 — Schedule: focus view ("where are we now")

- **Mode:** User · **File:** `frontend/js/modules/schedule/focus.js` (+ `index.js` shell) · **Reached:** the סדר יום tile; default sub-view.

```
A "what's happening now" screen for a child's visual daily schedule, Hebrew RTL,
landscape, very calm.

Top bar: exit icon (right), child's name or "הלוח שלי" (centre), a text button
"📅 חודש" / calendar icon (left).

Centre of screen: a single large card for the current activity — a big picture
symbol, the activity name in very large text, and the time under it in muted
text. The whole card is tappable (it speaks the activity). To its side, a very
large circular check button (label like 'סימון "ארוחת בוקר" כבוצע').

Above the card, a row of small dots — one per activity today, filled for the ones
already done ("3 מתוך 6 הושלמו").

Below the card: quiet buttons "כל היום" and, if applicable, "יציאה".

When the check is pressed the card gently slides away and the next activity fades
in. Nothing flashes.
```

| Hebrew | Meaning |
|---|---|
| `הלוח שלי` | My schedule |
| `חודש` | Month |
| `כל היום` | The whole day |
| `יציאה` | Exit |
| `{done} מתוך {total} הושלמו` | {done} of {total} completed |

**Also generate:** empty state (`אין משימות להיום.` + `חזרה`); all-done
celebration — a party icon, headline `כל הכבוד! סיימנו להיום`, button
`צפייה בכל היום`.

---

#### T2.2 — Schedule: day list

- **Mode:** User · **File:** `frontend/js/modules/schedule/day-list.js` · **Reached:** "כל היום" from the focus view.

```
The full daily schedule as a checklist for a child, Hebrew RTL.

Header row: a "הקראת כל היום" button with a speaker icon (toggles to "עצור" while
reading), a "מיקוד" text button, optional "יציאה".

Then a vertical list of activities. Each row: a large checkbox on the right, a
picture thumbnail, the activity name, and the time on the left. Completed rows
are checked and gently dimmed. Rows are tall and easy to tap.
```

| Hebrew | Meaning |
|---|---|
| `הקראת כל היום` | Read the whole day aloud |
| `עצור` | Stop |
| `מיקוד` | Focus |
| `אין משימות להיום.` | No tasks today. |

---

#### T2.3 — Schedule: monthly calendar

- **Mode:** User · **File:** `frontend/js/modules/schedule/calendar.js` · **Reached:** "חודש" from the schedule top bar.

```
A monthly calendar for a child's app, Hebrew RTL. Header: a previous-month
chevron (points right, RTL), the month and year centred ("מרץ 2026"), a
next-month chevron (points left), and a "יציאה" text button. Below: a 7-column
grid. Weekday headers "א׳ ב׳ ג׳ ד׳ ה׳ ו׳ ש׳" from the right. Then day cells;
leading blanks for the first week; today's cell is outlined in the accent
colour; a cell with an event shows a small label under the date. Cells at least
72px tall. Calm, plain, no colour coding beyond "today".
```

| Hebrew | Meaning |
|---|---|
| month names | `ינואר … דצמבר` |
| weekday heads | `א׳ ב׳ ג׳ ד׳ ה׳ ו׳ ש׳` |
| `יציאה` | Exit |

---

#### T2.4 — Schedule editor

- **Mode:** Caregiver · **File:** `frontend/js/modules/schedule/editor.js` · **Reached:** "ערוך לוח זמנים" on a child card.

```
An editor for a parent to build a child's daily schedule, Hebrew RTL, adult
density.

Header "סדר יום — נועה" with a "חזרה" button.

A date field "תאריך" at the top.

Card "משימות היום": a list of existing tasks (each row shows "08:00 ארוחת בוקר"
with reorder up/down buttons and a red "מחק"), then an add form — task name, a
time input, an optional symbol picker with a "בחר סמל (רשות)" preview, and an
"הוסף משימה" primary button. Below, a small "העתקה מתאריך:" row with a date field
and an "העתק" button.

Card "אירועים בלוח החודשי": a list of calendar events, then an add form — event
title, a date, an optional note "הערה (רשות)", and an "הוסף אירוע" button.
```

| Hebrew | Meaning |
|---|---|
| `סדר יום — {שם}` | Schedule — {name} |
| `תאריך` | Date |
| `משימות היום` | Today's tasks |
| `מחק` | Delete |
| `בחר סמל (רשות)` | Choose a symbol (optional) |
| `הוסף משימה` | Add task |
| `העתקה מתאריך:` / `העתק` | Copy from date: / Copy |
| `אירועים בלוח החודשי` | Monthly-calendar events |
| `הערה (רשות)` | Note (optional) |
| `הוסף אירוע` | Add event |

**Also:** empty states `אין משימות. הוסיפו למטה או העתיקו מיום אחר.` /
`אין אירועים החודש.`

---

#### T2.5 — Rules & tokens: rules tab

- **Mode:** User · **File:** `frontend/js/modules/rules/index.js` · **Reached:** the הכללים שלי tile.

```
A screen showing a child their behaviour-support rules, Hebrew RTL, calm.

Top bar: exit icon (right), child name or "כללים ואסימונים" (centre), and a token
badge on the left — a star icon and a number ("⭐ 12", label "12 אסימונים").

Two tabs: "כללים" (selected) and "חנות הפרסים".

Under the tabs, a vertical list of rule cards. Each card: a picture symbol on the
right, then bold rule text and a lighter explanatory line under it. Tapping a
card plays a spoken explanation. Big, calm, one accent colour on the token badge
and active tab.
```

| Hebrew | Meaning |
|---|---|
| `הכללים שלי` | My rules |
| `{n} אסימונים` | {n} tokens |
| `כללים` | Rules |
| `חנות הפרסים` | Reward store |
| `אין כללים כרגע.` | No rules right now. |

**Also generate:** load-error state — centred `לא ניתן לטעון.` + `חזרה` (same
pattern serves the rewards tab).

---

#### T2.6 — Rules & tokens: reward store tab

- **Mode:** User · **File:** `frontend/js/modules/rules/index.js` · **Reached:** the "חנות הפרסים" tab.

```
A reward store for a child, Hebrew RTL. Same top bar and token badge as the rules
screen, "חנות הפרסים" tab selected. A grid of reward tiles. Each tile: a picture,
the reward name, and a cost line with a star ("⭐ 5"). Rewards the child can't
afford yet look locked (dimmed, small lock icon). Tapping an affordable reward
opens a confirm dialog "לממש \"זמן מסך\" תמורת 5 אסימונים?". Calm, celebratory but
not loud.
```

| Hebrew | Meaning |
|---|---|
| `חנות הפרסים` | Reward store |
| `⭐ {cost}` | cost in tokens |
| `לממש "{פרס}" תמורת {n} אסימונים?` | Redeem "{reward}" for {n} tokens? |
| `הבקשה נשלחה למטפל ✓` | Request sent to caregiver ✓ (toast) |
| `אין מספיק אסימונים` | Not enough tokens (toast) |
| `אין פרסים כרגע.` | No rewards right now. |

---

#### T2.7 — Rules & tokens editor

- **Mode:** Caregiver · **File:** `frontend/js/modules/rules/editor.js` · **Reached:** "כללים ואסימונים" on a child card.

```
A parent's editor for a child's token economy, Hebrew RTL, adult density.
Header "הכללים שלי — נועה". Four stacked cards:

1. "אסימונים: 12 ⭐" — quick-award buttons "+1" "+2" "+5", a "כמות" number field,
   a "סיבה (רשות)" text field, an "הענקה" button. Below, a short list of recent
   transactions with positive amounts in green and negative in muted red.

2. "בקשות פרס ממתינות (2)" — rows like "זמן מסך — 5 ⭐" each with an "אישור"
   button and a red "דחייה (החזר אסימונים)" button. Empty: "אין בקשות.".

3. "כללי התנהגות" — list of rules, then an add form: rule name, an explanation
   field "הסבר (יוקרא בקול)", an optional symbol picker, "הוסף כלל".

4. "חנות הפרסים" — list of rewards (disabled ones dimmed) each with an
   "השבתה"/"הפעלה" toggle button and "מחק"; then an add form: reward name, a
   "מחיר באסימונים" number, an optional symbol, "הוסף פרס".
```

| Hebrew | Meaning |
|---|---|
| `אסימונים: {n} ⭐` | Tokens: {n} |
| `כמות` | Amount |
| `סיבה (רשות)` | Reason (optional) |
| `הענקה` | Award |
| `בקשות פרס ממתינות ({n})` | Pending reward requests ({n}) |
| `אישור` / `דחייה (החזר אסימונים)` | Approve / Reject (refund tokens) |
| `כללי התנהגות` | Behaviour rules |
| `הסבר (יוקרא בקול)` | Explanation (read aloud) |
| `הוסף כלל` | Add rule |
| `חנות הפרסים` | Reward store |
| `השבתה` / `הפעלה` | Disable / Enable |
| `מחיר באסימונים` | Price in tokens |
| `הוסף פרס` | Add reward |

---

#### T2.8 — Calming: sounds

- **Mode:** User · **File:** `frontend/js/modules/calming/index.js` + `sounds.js` · **Reached:** the פינת רוגע tile.

```
A calming-sounds screen for a child, Hebrew RTL. Top bar: exit icon (right),
title "פינת רוגע" (centre). Three tabs: "צלילים" (selected), "נשימה", "זיכרון".
Below, four large sound buttons in a grid: "גשם", "גלים", "רוח", "זמזום רגוע",
each with a simple illustration and a small play/pause indicator. Only one plays
at a time; the active one is clearly marked. Nothing autoplays. Very quiet, muted
palette, lots of space.
```

| Hebrew | Meaning |
|---|---|
| `פינת רוגע` | Calming corner |
| `צלילים` / `נשימה` / `זיכרון` | Sounds / Breathing / Memory |
| `גשם` `גלים` `רוח` `זמזום רגוע` | Rain / Waves / Wind / Gentle hum |

---

#### T2.9 — Calming: breathing

- **Mode:** User · **File:** `frontend/js/modules/calming/breathing.js` · **Reached:** the "נשימה" tab.

```
A guided-breathing screen for a child, Hebrew RTL. Centre: one large soft circle
that slowly expands and contracts. A word above it shows the phase: "שאיפה"
(breathe in), "החזקה" (hold), "נשיפה" (breathe out) — before starting it reads
"מוכנים?". One button below: "התחלה" (becomes "עצירה"). Extremely calm, slow, no
colour shifts, no numbers, no sound. Must still make sense with the animation
turned off (text cue only).
```

| Hebrew | Meaning |
|---|---|
| `מוכנים?` | Ready? |
| `שאיפה` / `החזקה` / `נשיפה` | In / Hold / Out |
| `התחלה` / `עצירה` | Start / Stop |

---

#### T2.10 — Calming: memory game

- **Mode:** User · **File:** `frontend/js/modules/calming/memory.js` · **Reached:** the "זיכרון" tab.

```
A gentle picture-matching memory game for a child, Hebrew RTL. A small header:
progress "2/6", a "משחק חדש" button, and a "זוגות: 6" toggle for 6 or 8 pairs.
Below, a 4-column grid of square cards — face-down cards show a plain "?" back,
face-up cards show a calm picture. No timer, no score, no pressure. On a win, a
quiet line "🎉 מצאת הכל!".
```

| Hebrew | Meaning |
|---|---|
| `משחק חדש` | New game |
| `זוגות: {n}` | Pairs: {n} |
| `🎉 מצאת הכל!` | You found them all! |

---

#### T2.11 — Social stories: list

- **Mode:** User · **File:** `frontend/js/modules/stories/index.js` · **Reached:** the סיפורים חברתיים tile.

```
A child's shelf of personalised social stories, Hebrew RTL. Top bar: exit icon
(right), title "הסיפורים של נועה" (centre). A vertical list (or 2-column grid on
wide screens) of story cards, each a large tile with a book icon and the story
title. Calm, inviting, few items. Empty: "אין עדיין סיפורים. מטפל יכול ליצור
סיפור במצב מטפל.".
```

| Hebrew | Meaning |
|---|---|
| `הסיפורים של {שם}` | {name}'s stories |
| `אין עדיין סיפורים. מטפל יכול ליצור סיפור במצב מטפל.` | No stories yet. A caregiver can create one in caregiver mode. |

---

#### T2.12 — Social story: reader

- **Mode:** User · **File:** `frontend/js/modules/stories/reader.js` · **Reached:** tapping a story.

```
A one-page-at-a-time social-story reader for a child, Hebrew RTL. Top strip: a
"✕ סגירה" button and a page counter "2 / 5". Centre: a large illustration (or a
plain book-icon placeholder if the image is missing), and below it a few lines
of large story text (tapping the text re-reads it aloud). Bottom: a nav row —
"הקודם" (right, disabled on page 1), a "הקראה" speaker button (centre), and
"הבא" (left; becomes "סיום" on the last page). The story is read aloud on open
and on each page turn. Calm, spacious, storybook feel without being babyish.
```

| Hebrew | Meaning |
|---|---|
| `סגירה` | Close |
| `{n} / {total}` | page counter |
| `הקודם` / `הבא` / `סיום` | Previous / Next / Finish |
| `הקראה` | Read aloud |

---

#### T2.13 — Social stories editor (AI interview)

- **Mode:** Caregiver · **File:** `frontend/js/modules/stories/editor.js` · **Reached:** "סיפורים חברתיים" on a child card.

```
A parent's screen for creating a social story with an AI assistant, Hebrew RTL,
adult density. Header "סיפורים חברתיים — נועה".

Card "יצירת סיפור חדש": a chat log — the assistant's questions as bubbles on the
right, the parent's answers as bubbles on the left. A "typing" bubble ("…")
shows while the assistant is thinking. At the bottom, either a text input with a
"שליחה" send button, or — once the assistant has enough — a primary button
"צור את הסיפור".

Card "סיפורים קיימים": a list of already-made stories, each with a red "מחק".
```

| Hebrew | Meaning |
|---|---|
| `סיפורים חברתיים — {שם}` | Social stories — {name} |
| `יצירת סיפור חדש` | Create a new story |
| `התשובה שלך…` | Your answer… |
| `שליחה` | Send |
| `צור את הסיפור` | Create the story |
| `סיפורים קיימים` | Existing stories |
| `אין עדיין סיפורים.` | No stories yet. |

**Also generate:** the loading/typing state.

---

#### T2.14 — Reading: lesson list

- **Mode:** User · **File:** `frontend/js/modules/learning/index.js` + `reading.js` · **Reached:** the תרגול קריאה וכתיבה tile.

```
A reading-practice list for a child, Hebrew RTL. Top bar: exit icon (right),
title "תרגול קריאה וכתיבה — נועה" (centre), a token badge (left). Two tabs: "קריאה"
(selected), "כתיבה". A vertical list of short lessons, each row: a level pill
"רמה 1" and the lesson title. Calm, few items, big rows.
```

| Hebrew | Meaning |
|---|---|
| `תרגול קריאה וכתיבה — {שם}` | Reading & writing — {name} |
| `קריאה` / `כתיבה` | Reading / Writing |
| `רמה {n}` | Level {n} |

---

#### T2.15 — Reading: text view + result

- **Mode:** User · **File:** `frontend/js/modules/learning/reading.js` · **Reached:** tapping a reading lesson.

```
A single short reading passage for a child, Hebrew RTL. Top: a "→ חזרה" back
button and the lesson title. Then the passage in large, well-spaced text. Below,
three buttons: "🔊 שמיעה" (hear it), "✓ קרא/ה יפה" (read it well), "✗ עוד תרגול"
(needs more practice) — the last two are for the caregiver to press.

Result state: replaces the buttons with a calm celebration — a party or
strong-arm icon, a line "כל הכבוד! +2 אסימונים" (or the gentle "עוד נתרגל יחד"),
and a "לטקסט נוסף" button. Never a red failure look.
```

| Hebrew | Meaning |
|---|---|
| `חזרה` | Back |
| `שמיעה` | Listen |
| `קרא/ה יפה` | Read it nicely |
| `עוד תרגול` | More practice |
| `כל הכבוד! +{n} אסימונים` | Well done! +{n} tokens |
| `עוד נתרגל יחד` | We'll practise more together |
| `לטקסט נוסף` | To another text |

**Also generate:** the inline caregiver PIN gate (T3.11).

---

### Tier 3 — remainder, sub-views, states

---

#### T3.1 — Sign-in

- **Mode:** Auth · **File:** `frontend/js/views/auth.js` · **Reached:** app start when signed out.

```
A minimal sign-in screen, Hebrew RTL. Centered card. Wordmark "alut4u" as the
heading, a muted line "כניסה". A field "אימייל", a field "סיסמה", a primary
button "כניסה", and a quiet button "אין לי חשבון — הרשמה". An error line can
appear ("אימייל או סיסמה שגויים"). Calm, uncluttered, single card on a plain
background.
```

| Hebrew | Meaning |
|---|---|
| `כניסה` | Sign in |
| `אימייל` / `סיסמה` | Email / Password |
| `אין לי חשבון — הרשמה` | I don't have an account — sign up |
| `אימייל או סיסמה שגויים` | Wrong email or password |

---

#### T3.2 — Sign-up

- **Mode:** Auth · **File:** `frontend/js/views/auth.js` (`signup` toggle) · **Reached:** "אין לי חשבון — הרשמה".

```
Same card as sign-in, in sign-up mode. Muted line "יצירת חשבון מטפל". Fields:
"שם", "אימייל", "סיסמה" (min 8). A checkbox "קראתי ואני מסכים/ה לתנאי השימוש
ולמדיניות הפרטיות". Primary button "צור חשבון", quiet toggle "יש לי כבר חשבון".
```

| Hebrew | Meaning |
|---|---|
| `יצירת חשבון מטפל` | Create a caregiver account |
| `שם` | Name |
| `קראתי ואני מסכים/ה לתנאי השימוש ולמדיניות הפרטיות` | I have read and agree to the Terms and Privacy Policy |
| `צור חשבון` | Create account |
| `יש לי כבר חשבון` | I already have an account |

---

#### T3.3 — Boot / loading

- **Mode:** pre-auth · **File:** `frontend/js/app.js` (`boot`) · **Reached:** every launch.

```
A bare loading screen: centered, one muted line "טוען…" on a plain background.
Nothing else. Also show a variant with an error line "אין חיבור לשרת." and a
"נסה שוב" text button.
```

| Hebrew | Meaning |
|---|---|
| `טוען…` | Loading… |
| `אין חיבור לשרת.` | No connection to the server. |
| `נסה שוב` | Try again |

---

#### T3.4 — PIN keypad

- **Mode:** Onboarding / gate · **File:** `frontend/js/views/pinpad.js` · **Reached:** onboarding (`בחירת קוד מטפל`) and unlocking Caregiver Mode (`כניסה למצב מטפל`).

```
A 4-digit PIN screen, Hebrew RTL page but the keypad itself reads left-to-right.
A centered card. A title ("בחירת קוד מטפל" when setting up, "כניסה למצב מטפל" when
unlocking) and a hint line under it. Four dots that fill as digits are entered.
An error line that clears the dots on a wrong code. Below, a 3×4 grid of large
round keys: 1–9, then [cancel-or-blank] 0 [backspace]. Keys at least 64px. Auto
-submits on the fourth digit. This is the `pin.keypad` component from §3.
```

| Hebrew | Meaning |
|---|---|
| `בחירת קוד מטפל` | Choose a caregiver PIN |
| `קוד בן 4 ספרות שרק המטפל יודע. הוא נדרש כדי לשנות הגדרות.` | A 4-digit code only the caregiver knows. Needed to change settings. |
| `כניסה למצב מטפל` | Enter caregiver mode |
| `הזינו את קוד המטפל` | Enter the caregiver code |
| `קוד שגוי` | Wrong code |
| `יותר מדי ניסיונות — נסו שוב בעוד רגע` | Too many attempts — try again shortly |
| `ביטול` | Cancel |

---

#### T3.5 — AAC board: load error

- **Mode:** User · **File:** `frontend/js/modules/aac/board.js` · **Reached:** board fetch fails.

```
Inside the communication-board frame: a centered gentle message "לא ניתן לטעון
את הלוח." and a "חזרה" text button. No alarming colours.
```

| Hebrew | Meaning |
|---|---|
| `לא ניתן לטעון את הלוח.` | Can't load the board. |
| `חזרה` | Back |

---

#### T3.6 — AAC editor (category & card management)

- **Mode:** Caregiver · **File:** `frontend/js/modules/aac/editor.js` · **Reached:** "ערוך לוח תקשורת" on a child card.

```
A parent's editor for a child's communication board, Hebrew RTL, adult density.
Header "בוא נדבר — נועה" with a "חזרה" button.

One card per category. Each category card: an inline-editable name field on the
right, a red "מחק קטגוריה" button on the left, then a list of the cards in that
category. Each card row: a thumbnail, the label, and action buttons — move
right, move left, "ערוך", red "מחק". At the end of each category, a "+ הוסף
כרטיס" button.

Footer: a small form to add a new category — a "שם קטגוריה חדשה" field and a
"הוסף קטגוריה" button.
```

| Hebrew | Meaning |
|---|---|
| `בוא נדבר — {שם}` | Communication board — {name} |
| `מחק קטגוריה` | Delete category |
| `הזז ימינה` / `הזז שמאלה` | Move right / Move left |
| `ערוך` / `מחק` | Edit / Delete |
| `+ הוסף כרטיס` | + Add card |
| `שם קטגוריה חדשה` / `הוסף קטגוריה` | New category name / Add category |

---

#### T3.7 — Symbol picker (component)

- **Mode:** Caregiver · **File:** `frontend/js/modules/aac/symbol-picker.js` · **Reached:** embedded in the AAC card form, schedule editor, rules editor.

```
A compact symbol picker, Hebrew RTL. A search field with a "חיפוש סמל…"
placeholder, then a scrollable grid of symbol thumbnails below it. Each thumbnail
is a plain rounded button; the selected one has an accent outline. Sits inline
inside a form, not as a popup.
```

| Hebrew | Meaning |
|---|---|
| `חיפוש סמל…` | Search symbol… |

---

#### T3.8 — Add-child form (expanded)

- **Mode:** Caregiver · **File:** `frontend/js/views/dashboard.js` · **Reached:** the add-child card on the dashboard.

```
The "הוספת חבר/ה" form card expanded, Hebrew RTL. Fields: "שם"; a select "בסיס
להסכמה" with options "הורה" / "אפוטרופוס" / "איש מקצוע (בהסכמת הורה)"; a checkbox
"אני מאשר/ת שקיבלתי את הסכמת ההורה/אפוטרופוס" that only appears when "איש מקצוע"
is chosen; a select "לוח תקשורת התחלתי" whose first option is "ללא — אתחיל
מאפס"; a primary "הוספה" button; an error slot.
```

| Hebrew | Meaning |
|---|---|
| `בסיס להסכמה` | Consent basis |
| `הורה` / `אפוטרופוס` / `איש מקצוע (בהסכמת הורה)` | Parent / Guardian / Professional (with parental consent) |
| `אני מאשר/ת שקיבלתי את הסכמת ההורה/אפוטרופוס` | I attest I have the parent's/guardian's consent |
| `לוח תקשורת התחלתי` | Starter communication board |
| `ללא — אתחיל מאפס` | None — start from scratch |
| `הוספה` | Add |

---

#### T3.9 — Account / data-rights card

- **Mode:** Caregiver · **File:** `frontend/js/views/dashboard.js` · **Reached:** bottom of the dashboard.

```
The "החשבון שלי" card, Hebrew RTL. A link "הורדת כל הנתונים שלי (JSON)", a red
text button "מחיקת החשבון וכל הנתונים", a divider, a quiet "התנתקות מהמכשיר"
button. Deleting opens the type-to-confirm dialog (§3): body "פעולה בלתי הפיכה.
הקלד/י DELETE כדי לאשר מחיקה מלאה:", a text field, a red confirm button that
stays disabled until "DELETE" is typed.
```

| Hebrew | Meaning |
|---|---|
| `פעולה בלתי הפיכה. הקלד/י DELETE כדי לאשר מחיקה מלאה:` | Irreversible. Type DELETE to confirm full deletion: |

---

#### T3.10 — Voice recorder row

- **Mode:** Caregiver · **File:** `frontend/js/modules/aac/recorder.js` · **Reached:** "הקלטה" in the AAC card form.

```
The audio row of the card form in its recording states, Hebrew RTL. Show three:
(1) idle — label "קול:", status "אין הקלטה", a "🎙 הקלטה" button; (2) a consent
dialog "הקלטת קול דורשת אישור. לאשר עכשיו?"; (3) recording — status "מקליט…
(לחץ שוב לעצירה)" with the button active; (4) done — status "הוקלט" plus a
"הסר הקלטה" button.
```

| Hebrew | Meaning |
|---|---|
| `אין הקלטה` / `הוקלט` | No recording / Recorded |
| `הקלטת קול דורשת אישור. לאשר עכשיו?` | Voice recording needs consent. Approve now? |
| `מקליט… (לחץ שוב לעצירה)` | Recording… (press again to stop) |
| `אין גישה למיקרופון` | No microphone access |

---

#### T3.11 — Reading verdict: inline PIN gate

- **Mode:** User→Caregiver · **File:** `frontend/js/modules/learning/reading.js` · **Reached:** child presses a verdict button; server needs caregiver elevation.

```
Inside the reading screen, replacing the action buttons: a short prompt "מטפל,
הזינו קוד כדי לאשר את הקריאה:", a single small 4-digit password field, an "אישור"
button, an error slot ("קוד שגוי"), and a "חזרה" button. This is the `pin.inline`
component from §3 — distinct from the full keypad.
```

| Hebrew | Meaning |
|---|---|
| `מטפל, הזינו קוד כדי לאשר את הקריאה:` | Caregiver, enter the code to confirm the reading: |
| `אישור` | Confirm |
| `קוד שגוי` | Wrong code |

---

#### T3.12 — Writing: exercise + result

- **Mode:** User · **File:** `frontend/js/modules/learning/writing.js` · **Reached:** the "כתיבה" tab → a prompt.

```
First, a prompt list identical in shape to the reading list (T2.14): rows with a
"רמה N" level pill and the prompt hint.

Then the exercise itself: a copy-the-word screen, Hebrew RTL. Top: "→ חזרה". A
label with the prompt (or "כתבו את המשפט"). A single large text input (no
autocomplete, no spellcheck). A primary "בדיקה" button.

Result: a calm icon (party for correct, a gentle "almost" for not), a line
"נכון! +1 אסימון" or "כמעט! הכיתוב הנכון: שלום", then "נסה שוב" and "תרגיל אחר"
buttons. No red, no harsh "wrong".
```

| Hebrew | Meaning |
|---|---|
| `כתבו את המשפט` | Write the sentence |
| `בדיקה` | Check |
| `נכון! +{n} אסימון` | Correct! +{n} token |
| `כמעט! הכיתוב הנכון: {מילה}` | Almost! The correct spelling: {word} |
| `נסה שוב` / `תרגיל אחר` | Try again / Another exercise |

---

#### T3.13 — Shared states (generate once, reused everywhere)

```
A small set of shared states in the app's style, Hebrew RTL:
- empty state: centered light icon + one muted Hebrew line + optional "חזרה".
- offline banner: a thin unobtrusive strip, muted, "אין חיבור — חלק מהתכונות לא
  זמינות" (the board and schedule keep working from cache).
- inline error: a short "err" line that reserves its own height so nothing
  jumps.
- toast: bottom-centre pill, info and error variants, auto-dismiss.
- celebration: gentle — soft party icon, a short praise line, a calm accent
  colour. Never confetti storms, never loud.
```

| Hebrew | Meaning |
|---|---|
| `אין חיבור — חלק מהתכונות לא זמינות` | Offline — some features unavailable |

---

## §5 — Out of scope for Stitch

Do **not** ask Stitch to design or generate these; each has its own source:

| Thing | Why not Stitch | Placeholder in repo |
|---|---|---|
| **AAC symbol artwork** (the picture vocabulary) | Mulberry Symbols (CC BY-SA 4.0) licensed, ingestion in progress — see `docs/symbols.md`. This is separate from the §3 UI icon set. | 26/36 core ids real Mulberry artwork, 10 kept placeholder (no adequate equivalent), ~2,955 more concepts pending Hebrew-label review — `frontend/assets/symbols/` (`scripts/build_symbols.py`) |
| **PWA app icons** (home-screen / install) | Product branding decision, needs the final wordmark | placeholder in `frontend/` icon slots |
| **Any image of a real child** | Privacy — the app never stores or shows real children's photos | n/a — illustrations only |
| **Marketing / landing / app-store pages** | Not part of the product | n/a |
| **Calming audio loops** | Audio, not visual | placeholder procedural WAVs (`scripts/build_calming.py`) |

Stitch **should** design: the ~20-glyph UI icon set (§3), all illustrative
placeholder art *slots* (so we know the size/shape), and every screen in §4.

---

## §6 — Post-export pipeline

Everything Stitch produces goes through three passes before it lands in the repo.
`frontend/css/tokens.css` is the **only** file that receives raw values.

### Pass 1 — RTL correctness

- Stitch emits LTR. Convert every physical property to a **logical** one:
  `margin-inline-start` not `margin-left`, `padding-inline`, `inset-inline`,
  `border-start-start-radius`, `text-align: start`.
- `dir="rtl"` on `<html>` (already set); verify nothing overrides it.
- **Mirror directional icons**: prev/next chevrons, backspace, "move right/left"
  — "next" points **left**.
- Keep the PIN keypad and any numeric field `dir="ltr"` internally.
- Check Hebrew line length and wrapping at `--text-2xl` on a 10" landscape
  screen — Hebrew runs longer than the English mockup text.

### Pass 2 — token extraction

- Take Stitch's palette table and paste the hexes into
  `frontend/css/tokens.css`, keyed by the existing custom-property names, in
  **both** the `:root` (light) block **and** the
  `@media (prefers-color-scheme: dark)` block. The dark block currently omits
  `--color-focus`, `--color-success`, `--color-warning`, `--color-danger` — fill
  those in this pass.
- Keep the existing `--space-*`, `--radius-*`, `--shadow-*`, `--touch-min` and
  the type scale unless Stitch had a strong reason to change them (note it if
  so).
- Then rewrite `frontend/css/components/app.css` section by section against
  those variables. **No literal colours in `app.css`** — every colour is
  `var(--color-*)`.
- Re-run the contrast check on the final pairs; record the ratios in
  `docs/accessibility.md`.

### Pass 3 — accessibility (Stitch won't produce these)

- `:focus-visible { outline: 3px solid var(--color-focus); outline-offset: 2px }`
  on every focusable element; `[tabindex="-1"]:focus { outline: none }` for the
  programmatic focus target.
- Under `[data-mode="user"]`: `min-block-size` / `min-inline-size: var(--touch-min)`
  on every button, link-button and card.
- `@media (prefers-reduced-motion: reduce)` — neutralise every transition and
  animation (the global rule in `base.css` plus the per-component ones).
- **Add the three missing pieces:**
  - an `.sr-only` / visually-hidden utility class,
  - an `@media (prefers-contrast: more)` block (stronger borders, full-contrast
    text),
  - an `@media (forced-colors: active)` block (respect system colours, keep
    focus visible).
- Keep every `aria-live`, `role="status"`, `role="alert"`, `role="tablist"`
  already in the JS.

### Screen → repo file map

| Screen (§4) | File |
|---|---|
| T1.1 AAC board / T3.5 error | `frontend/js/modules/aac/board.js` |
| T1.2 Sentence bar | `frontend/js/modules/aac/sentence-bar.js` |
| T1.3 Home (+ empty) | `frontend/js/views/home.js` |
| T1.4 Dashboard / T3.8 add-child / T3.9 account | `frontend/js/views/dashboard.js` |
| T1.5 AAC card form / T3.6 AAC editor | `frontend/js/modules/aac/editor.js` |
| T3.10 recorder row | `frontend/js/modules/aac/recorder.js` |
| T3.7 symbol picker | `frontend/js/modules/aac/symbol-picker.js` |
| T2.1 focus / T2.2 day list / T2.3 calendar / T2.4 editor | `frontend/js/modules/schedule/{focus,day-list,calendar,editor,index}.js` |
| T2.5 rules / T2.6 rewards | `frontend/js/modules/rules/index.js` |
| T2.7 rules editor | `frontend/js/modules/rules/editor.js` |
| T2.8 sounds / T2.9 breathing / T2.10 memory | `frontend/js/modules/calming/{sounds,breathing,memory,index}.js` |
| T2.11 story list / T2.12 reader / T2.13 editor | `frontend/js/modules/stories/{index,reader,editor}.js` |
| T2.14 reading list / T2.15 text+result / T3.11 PIN gate | `frontend/js/modules/learning/{index,reading}.js` |
| T3.12 writing | `frontend/js/modules/learning/writing.js` |
| T3.1 sign-in / T3.2 sign-up | `frontend/js/views/auth.js` |
| T3.3 boot / T3.4 PIN keypad | `frontend/js/app.js`, `frontend/js/views/pinpad.js` |
| T3.13 shared states, toast, dialogs | `frontend/js/ui.js` (+ new dialog module) |

### Follow-on code work (lift into `docs/launch-checklist.md`)

The brief commissions components the app doesn't have yet. After the visual pass:

- [ ] Build the `dialog` component and replace the 6 native `confirm()` /
      `prompt()` call sites (hide profile, delete card, delete category, redeem
      reward, voice consent, account deletion).
- [ ] Build the unified `pin` component; replace both `views/pinpad.js` and the
      inline gate in `modules/learning/reading.js`.
- [ ] Replace emoji controls with the icon set; keep emoji only where it's
      illustrative content.
- [ ] Delete the dead `frontend/js/router.js`.
- [ ] Add `.sr-only`, `prefers-contrast`, `forced-colors` (pass 3).

### Verification

No CI impact (docs + CSS only). After the passes: the axe-core CI job must stay
green, and re-run the manual list in `docs/accessibility.md` (keyboard-only, 200%
zoom, VoiceOver smoke, contrast, reduced-motion) against the restyled screens.
