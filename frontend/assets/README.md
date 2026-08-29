# Static assets

`icon-192.png`, `icon-512.png`, `icon-maskable-512.png` are **placeholder** flat
blue squares so the PWA installs. Replace with real artwork before launch
(maskable safe zone: centre 80%).

The bundled AAC symbol library is generated into `symbols/_generated/` by
`scripts/build_symbols.py` (Phase 2) from the licensed source set — that folder
is git-ignored; the build runs in CI.
