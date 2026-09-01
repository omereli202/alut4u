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

## Verification

- **CI**: axe-core against key views (added in Phase 1).
- **Manual per release**: keyboard-only navigation, 200% browser zoom, VoiceOver
  (iPadOS) smoke, contrast check, reduced-motion on.
- **Device**: real tablet in Guided Access / Screen Pinning — see
  `kiosk-setup.md`.
