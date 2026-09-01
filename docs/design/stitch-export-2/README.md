# Stitch export 2 — "Serene Path"

Second Google Stitch export for this project (see `docs/design/stitch-export/`
for the first — that one's README has the full explanation of what this
process is and how it's used). Same theme: `serene_path_2/DESIGN.md`'s palette
and radii are byte-identical to the first export's `serene_path/DESIGN.md`, so
nothing here changes `tokens.css`.

**Several folder names are misleading** — Stitch's own naming, not renamed
here so the folders still match what's in the zip:

| Folder | What it actually is | `docs/design.md` §4 ID | Informs |
|---|---|---|---|
| `pin` | The `pin.inline` component (4 separate digit inputs, auto-advance, lock badge) — the first real reference art either export has given this component | T3.11 | `frontend/js/modules/learning/reading.js` (`renderPinGate`) |
| `boot_screen` | Boot/loading screen with a cross-fading error+retry state | T3.3 | `frontend/js/app.js` (`boot`) |
| `_5` | "System States & Components" — offline banner, empty state, celebration state, toast | T3.13 | shared, `frontend/js/ui.js` + `app.css` |
| `_6` | Modal/dialog gallery (standard/destructive/type-to-confirm) — duplicates the first export's `_13`; `frontend/js/dialog.js` already supersedes both | — | none, already built |
| `serene_path` | **Not the theme spec** — a "Delete Account Confirmation" screen (the type-to-confirm dialog variant) | T3.9 | same as `_6` — already covered by `dialog.js` |
| `serene_path_2` | The actual theme spec (`DESIGN.md` only, no screen) | — | `tokens.css` (confirmed unchanged) |
| `_1` | Social story reader | T2.12 | `frontend/js/modules/stories/reader.js` |
| `_2`, `_3` | Reading & writing lesson list (tabs + list), two near-identical takes | T2.14 | `frontend/js/modules/learning/index.js` |
| `1`, `_4` | Writing exercise — prompt, speak button, input, check button, pass/fail feedback | T2.15 / T3.12 | `frontend/js/modules/learning/writing.js`, `reading.js` |
| `alut4u_ui_icon_set` | **Not a UI icon sheet** — the app's logo/brand mark (a stylized "A" knot), as a PNG mockup only, no SVG source | — | future PWA icon work (blocked on a real vector source — see `docs/launch-checklist.md`) |

## What this confirmed vs. added

- **Palette/radii** — confirmed identical to export 1, byte-for-byte.
- **Dialogs** — confirmed export 1's analysis was right to not copy the
  markup verbatim: `_6`/`serene_path` here repeat the same `backdrop-blur`
  and disabled-button-contrast issues already avoided in `dialog.js`.
- **Icons** — 10 new Material Symbols ligatures beyond the first export's 29:
  `arrow_forward`, `auto_stories`, `dashboard`, `gpp_maybe`, `inbox`,
  `manage_accounts`, `refresh`, `security`, `toll`, `wifi_off`. Added to
  `scripts/build_icons.py`.
- **Accessibility** — the reading/writing screens (`_2`/`_3`/`1`/`_4`) are the
  cleanest screens either export has produced: no red anywhere in the
  pass/fail states (the "try again" card uses neutral grays + a
  secondary-container button, matching `docs/design.md` §2.6 exactly), no
  backdrop-blur. Not everything is clean — `_1`'s exit button is `p-2`
  (≈40px, under the 60px User-Mode floor) and reuses the same
  `flex-row-reverse`-on-RTL placement inconsistency export 1's board variants
  had.
