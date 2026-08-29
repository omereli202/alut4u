# Accessibility

The primary users are children on the autism spectrum. This is a core
requirement, not a checklist item.

## Rules

- **Touch targets** ≥ 60px in User Mode (`--touch-min`, enforced in `base.css`
  via `[data-mode="user"]`).
- **Contrast** ≥ WCAG AA (4.5:1 text, 3:1 large text / UI). Verify token pairs
  when the Stitch palette lands.
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
- **Semantics** — real `<button>`/`<a>`, ARIA roles where needed, `aria-live`
  for status, focus moved to `#main` on route change (see `router.js`).

## Verification

- **CI**: axe-core against key views (added in Phase 1).
- **Manual per release**: keyboard-only navigation, 200% browser zoom, VoiceOver
  (iPadOS) smoke, contrast check, reduced-motion on.
- **Device**: real tablet in Guided Access / Screen Pinning — see
  `kiosk-setup.md`.
