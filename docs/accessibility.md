# Accessibility

The primary users are children on the autism spectrum. This is a core
requirement, not a checklist item.

## Rules

- **Touch targets** ≥ 60px in User Mode (`--touch-min`, enforced in `base.css`
  via `[data-mode="user"]`).
- **Contrast** ≥ WCAG AA (4.5:1 text, 3:1 large text / UI). Verified below for
  the "Serene Path" Stitch palette in `tokens.css`.
- **Focus** always visible (`:focus-visible`, amber ring). Never removed without
  a stronger replacement.
- **Motion** — respect `prefers-reduced-motion`; `base.css` already neutralizes
  animation/transition durations. No parallax, no auto-advancing carousels.
- **Audio** — never autoplay. No sound without a user action. No looping
  background audio in User Mode except the Calming player (explicit play).
- **No flashing** — nothing above 3 flashes/sec, ever (seizure risk).
- **Language** — `<html lang="he" dir="rtl">`. Content is Hebrew; layout is
  logical-property based so it stays correct.
- **Predictability** — consistent placement, no surprise navigation, no modals
  that trap focus without an obvious exit. The child must not be able to
  navigate out of the app (kiosk + no external links in User Mode).
  `frontend/js/dialog.js` (replacing native `confirm()`/`prompt()`) uses a real
  `<dialog>` — `showModal()` gives a native focus trap, Esc closes, and a
  backdrop tap closes it, so there's always an obvious way out.
- **Semantics** — real `<button>`/`<a>`, ARIA roles where needed, `aria-live`
  for status, focus moved to `#main` on route change (see `router.js`).

## Contrast ratios — Stitch palette (docs/design.md §6 pass 2)

Computed from the hex values in `tokens.css`. AA floors: 4.5:1 body text,
3:1 large text (≥ 24px, or ≥ 19px bold) and non-text UI (borders, icons).

| Pair | Light | Dark |
|---|---|---|
| `--color-text` on `--color-bg` | 12.00:1 | 15.07:1 |
| `--color-text-muted` on `--color-bg` | 4.96:1 | 9.20:1 |
| `--color-text` on `--color-surface` | 12.68:1 | — |
| `--color-primary-contrast` on `--color-primary` | 6.73:1 | 10.02:1 |
| `--color-border-strong` on `--color-bg` (input outlines) | 4.25:1 | 5.85:1 |
| `--color-focus` on `--color-bg` / `--color-surface` | 3.12:1 / 3.29:1 | — |
| `--color-success-ink` on white / dark surface | 5.09:1 | 8.45:1 |
| `--color-warning-ink` on white / dark surface | 5.93:1 | 9.50:1 |
| `--color-danger-ink` on white / dark surface | 6.45:1 | 7.25:1 |

`--color-border` (the plain hairline token, ~1.3:1 on both surfaces) is
**decorative only** — dividers and card outlines that aren't the sole cue for
a control's boundary. Anything the caregiver types into or presses as a
distinct control (`<input>`, `<select>`, PIN keys, the sentence-bar/AAC
category-tab default border) uses `--color-border-strong` instead.

`--color-success` / `--color-warning` / `--color-danger` (the base, non-`-ink`
hues) fall as low as 2.07–3.52:1 as *text* or with white text *on* them as a
solid fill in light mode — below AA on both counts. They're for fills, icons
and large marks only, per the rule below:

- **Text of any size** (`.err`, `.btn-link.danger`, `.tx-pos`/`.tx-neg`,
  `.reward-cost`) → the `-ink` variant, which is a darker shade in light mode
  and equals the base hue in dark mode (already >= 7:1 there).
- **A large icon/mark on top of the base-hue fill** (`.focus-check`'s
  checkmark, `.token-badge`) → `--color-text`, not white — white-on-base-hue
  is 2.2–2.5:1, under even the 3:1 large-text/icon floor.
- **Small text that must sit on a danger/warning/success fill**
  (`.queue-badge`) → base-hue text can't clear 4.5:1 against either black or
  white at that luminance, so the fill flips to `--color-surface` with
  `-ink` text and a base-hue border instead of a solid fill (`.toast-error`
  does the same).
- **A solid destructive button** (`.btn-primary.danger`, the dialog confirm
  button) → fills with `--color-danger-ink`, not the base hue, keeping the
  primary button's white text (6.45:1) instead of the 3.52:1 the base danger
  gives white text at that size.

`--radius-*` was also corrected against the real Stitch export
(`docs/design/stitch-export/`) rather than a guess — see that folder's README
— but radius has no contrast implication, only the colour table above does.

### Contrast — per-screen layout pass (docs/design/stitch-export-2)

New pairs introduced applying the PIN gate, boot screen, and shared states:

| Pair | Light | Dark |
|---|---|---|
| `--color-primary` on `--color-primary-soft` (`.pin-gate-icon`, `.celebration-icon`) | 5.20:1 | 5.45:1 |
| `--color-text` on `--color-primary-soft` (`.celebration-state` body text) | 9.80:1 | 7.67:1 |

`.offline-banner` was drafted with `--color-text-muted` on
`--color-surface-sunken` first — computed at **4.50:1**, technically over the
4.5:1 floor but with no real margin at `--text-sm` size, so it uses full
`--color-text` instead (comfortably clear in both themes — see the table
above for that pair on `--color-bg`; `--color-surface-sunken` is close enough
in lightness not to need a separate ratio).

### Contrast — `.btn-link` as a bordered chip

`.btn-link` (back/cancel/action links, 53 call sites) moved from underlined
text to a bordered chip — `docs/design.md` §3 already permits either
treatment. New background is `--color-surface`, not `--color-bg`, so the
existing border-strong ratios don't quite apply verbatim; recomputed for the
actual pair:

| Pair | Light | Dark |
|---|---|---|
| `--color-primary` on `--color-surface` (text) | 6.73:1 | 9.46:1 |
| `--color-border-strong` on `--color-surface` (border) | 4.49:1 | 5.17:1 |
| `--color-danger-ink` on `--color-surface` (`.btn-link.danger` text) | 6.45:1 | 7.25:1 |
| `--color-danger` on `--color-surface` (`.btn-link.danger` border) | 3.52:1 | 7.25:1 |

The danger border only needs the 3:1 non-text-UI floor (it's decorative, not
carrying text) — light mode clears it at 3.52:1; dark mode's `--color-danger`
equals `--color-danger-ink` there (both resolve to the same pastel base hue),
so it's the same 7.25:1 as the row above.

## Verification

- **CI**: axe-core against key views (added in Phase 1).
- **Manual per release**: keyboard-only navigation, 200% browser zoom, VoiceOver
  (iPadOS) smoke, contrast check, reduced-motion on.
- **Device**: real tablet in Guided Access / Screen Pinning — see
  `kiosk-setup.md`.
