# AAC module (Phase 2)

The communication grid and sentence builder.

Planned files:
- `board.js` — grid render (2×2 → 5×5), category tabs, card tap → speak + append
- `sentence-bar.js` — the builder strip: append, remove-last, clear, speak-all
- `speech.js` — plays the card's pre-generated audio from cache; falls back to
  the `audio_asset` upload, then to nothing (never synthesizes at tap time)
- `editor.js` — caregiver: add/edit/reorder/delete cards, symbol picker vs icon
  upload, per-card audio upload or `MediaRecorder` capture (consent-gated)

Offline: the board snapshot, every symbol/icon image and every audio file are
cached by the service worker under stable `/api/media/<id>` URLs on first load.
