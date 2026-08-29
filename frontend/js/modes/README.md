# Modes

- `user/` — the child-facing interface. Renders only enabled modules, large
  targets, no navigation chrome that could lead out of the app.
- `caregiver/` — behind the PIN. Dashboard, module toggles, editors.

The active mode is on `document.body.dataset.mode` (`"user"` | `"caregiver"`),
which `css/base.css` keys the touch-target floor off of. Switching to caregiver
mode requires a successful `POST /api/auth/pin`; the elevation times out and
drops back to `user`.
