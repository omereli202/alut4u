# AAC module (Phase 2)

The communication grid and sentence builder.

Planned files:
- `board.js` — grid render (2×2 → 5×5), category tabs, card tap → speak + append
- `sentence-bar.js` — the builder strip: append, remove-last, clear, speak-all
- `speech.js` — plays the card's pre-generated audio from cache; falls back to
  the `audio_asset` upload, then to nothing (never synthesizes at tap time)
- `editor.js` — caregiver: add/edit/reorder/delete cards, symbol picker vs icon
  upload, per-card audio upload or `MediaRecorder` capture (consent-gated)

Offline: the board snapshot is cached (`sw.js`'s `DATA_CACHE`), every
caregiver-uploaded icon/audio file is cached under its stable `/api/media/<id>`
URL (`MEDIA_CACHE`), and every bundled symbol image is cached under its
versioned `/assets/symbols/<id>.svg?v=` URL (`SYMBOL_CACHE`, see `ui.js`'s
`symbolUrl()`) — `board.js` explicitly prefetches both on load
(`speech.js`'s `prefetch()` + `prefetchSymbols()`) rather than relying on
whatever happened to render while online.
