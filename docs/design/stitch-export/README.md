# Stitch export — "Serene Path"

Raw Google Stitch export (`code.html` + `screen.png` per folder), generated
from the `docs/design.md` brief. `serene_path/DESIGN.md` is the theme spec
(palette, type scale, radii, spacing) Stitch produced for §1 (paste `code.html`
into a browser to see the live render — it pulls Tailwind + Google Fonts from a
CDN, so it needs network access; that CDN dependency is why this markup is
*translated* into the app's plain CSS rather than used directly, per
`docs/design.md` §6).

These are **reference only** — nothing here ships. The app's real markup lives
in `frontend/js/`; this folder is what informed the `tokens.css` values and the
shared components in `frontend/css/components/app.css`.

14 folders, not 14 distinct screens — several are the same AAC board with a
different category selected or in dark mode.

| Folder(s) | Screen | `docs/design.md` §4 ID | Informs |
|---|---|---|---|
| `_1` | Daily schedule — day list | T2.2 | `frontend/js/modules/schedule/day-list.js` |
| `_2` | Rules & tokens — reward store / rules tabs | T2.5 / T2.6 | `frontend/js/modules/rules/index.js` |
| `_3` | Schedule — focus view | T2.1 | `frontend/js/modules/schedule/focus.js` |
| `_4` | Schedule — monthly calendar | T2.3 | `frontend/js/modules/schedule/calendar.js` |
| `_5`, `_6` | AAC board — "רגשות" (emotions) category, light | T1.1 | `frontend/js/modules/aac/board.js` |
| `_8`, `_9` | AAC board — "אוכל" (food) category, light/dark | T1.1 | same |
| `_10` | AAC board — "אוכל" sub-category ("צהריים"/lunch) | T1.1 | same |
| `_11` | AAC board — "אנשים" (people) category | T1.1 | same |
| `_12` | AAC board — "פעילויות" (activities) category | T1.1 | same |
| `_7` | AAC editor — drag-to-reorder cards | T3.6 | `frontend/js/modules/aac/editor.js` |
| `_13` | Dialog/modal variants (standard, destructive, type-to-confirm) — new component, §3 "commission these" | — | new `frontend/js/dialog.js` |
| `_14` | Voice recorder row states | T3.10 | `frontend/js/modules/aac/recorder.js` |

**Not exported** — these screens keep their current layout after the
foundation pass and are candidates for a later per-screen pass: User-Mode home
(T1.3), caregiver dashboard (T1.4), AAC card form (T1.5), schedule editor
(T2.4), calming sounds/breathing/memory (T2.8–10), social stories (T2.11–13),
reading & writing (T2.14–15, T3.12), sign-in/up (T3.1–2), boot (T3.3), PIN
keypad (T3.4).

## What this export confirmed vs. changed

A pass at `tokens.css`/`base.css` happened before this export arrived, working
from a pasted palette table without the underlying screens. Cross-checking
against the real export:

- **Palette** — confirmed exactly (`bg`, `text`, `primary`, `secondary`,
  `success`, `warning`, `danger`, `focus`, `border`, all hex-for-hex).
- **Radii** — corrected. The earlier pass read a stray note ("21 screens") and
  set `sm/md/lg` to 8/16/24px. The export's actual Tailwind config resolves
  `rounded-lg` → 8px, `rounded-xl` → 12px (114 uses, the dominant radius),
  `rounded-2xl` → 16px, `rounded-3xl` → 24px, `rounded-full` → pill.
- **Semantic "ink" text colours** — kept as-is, after checking, not swapped for
  the export's Material-3 `error`/`tertiary`/`secondary-container` roles. Those
  looked like a natural match at first (the export does use `error-container` +
  `text-error` in its own destructive-dialog icon badge), but computing HSL for
  both shows the app's own danger/warning/success hues and the M3 auto-palette
  are a different family: `--color-success` is H≈101° (olive-sage) while M3
  `secondary` is H≈159° (teal) — a 58° hue jump that would look mismatched next
  to the actual success-green fills used elsewhere. The existing ink values
  (`#a63a25`/`#8a5a00`/`#4a7a33`) are within 1–3° of their own base hues —
  same-family darkened text shades — and already clear AA (5–6.5:1 on white).
- **`--color-secondary`** — confirmed in use: the AAC board's active category
  tab is a `secondary-container` pill, matching the token the earlier pass had
  added speculatively.

## Watch-outs for the per-screen pass (not yet applied)

A deep read of the actual markup — not just the theme spec — turned up real
problems in the export itself. None of this is ported as-is; recorded here so
whoever does the T1.1/T2.x layout pass doesn't reintroduce it:

- **The seven AAC-board variants (`_5,_6,_8,_9,_10,_11,_12`) don't agree with
  each other** — different top-bar heights (64–88px), different sentence-bar
  shapes (pill vs. card vs. docked strip), three incompatible category-tab
  designs (pill/secondary, pill/primary, underline), four different chip
  shapes, four different card-label type scales. There's no single "the AAC
  card" to copy — one has to be chosen and applied uniformly. `_11` is not
  usable at all (byte-identical to `_8` with placeholder images, a truncated
  sidebar, and an `.aac-tile` class the file never defines).
- **Touch targets under 60px in `data-mode="user"` markup**: grid-size
  ±/clear buttons (28–32px), most exit buttons (40–48px), category tabs
  (~53px), a chip remove-✕ visible only on `:hover` (~14px, invisible on
  touch). Only `_3` and `_4` consistently clear the floor.
- **Red beyond the one accepted emotion tile**: the exit-button label/icon in
  `_3`, the sentence-bar "clear"/backspace hover state in `_5`, the "כואב לי"
  (it hurts) tile in `_6`, a food card in `_10`, an activity card in `_12` —
  all `text-danger`/`error-container` in child-facing UI. `docs/design.md`
  §2.6 reserves red for caregiver mode; a distressed-emotion glyph is
  arguably content rather than a failure state, but that argument doesn't
  extend to a meatball or a garden-visit icon.
- **Unbounded looping animation**: `_2`'s affordable-reward tiles pulse via
  `animation: subtle-pulse 2s infinite`, and `_8`'s tile-tap flash is fired
  from an inline `<script>`. §2 rule 4 rules out motion that isn't
  user-initiated and doesn't end.
- **`backdrop-blur` on the dialog backdrops** (`_13`, `_14`) — glassmorphism,
  which §3 rules out. `frontend/js/dialog.js` uses a plain scrim instead.
- **9 of 14 screens have no focus style at all**, and `_14` writes
  `focus:ring-3` (not a real Tailwind class) alongside `focus:outline-none`,
  removing the native outline with nothing to replace it.
- **Physical (non-logical) CSS throughout** despite `dir="rtl"` on `<html>`:
  `ml-*`, `pr-*`, `border-r`, `left-*`, plus `flex-row-reverse` layered on top
  of RTL in 8 of 14 files — which puts the exit control on the physical right
  in some screens and the physical left in others. `backspace` is never
  mirrored anywhere in the export (`.icon-flip` in `base.css` now handles
  this for the app's own icon sprite).
- **Invalid/no-op Tailwind classes**: `scale-98` (not a real class — five of
  the AAC-card variants silently lost their press feedback), `focus:ring-3`,
  `var(--color-surface-container-high)` referenced with no custom property
  ever defined. A reminder to actually render the export before trusting it.
