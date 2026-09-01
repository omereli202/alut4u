# Fonts

**Rubik** — the app's Hebrew-first UI typeface (see `docs/design.md` §3). Self-hosted
so the PWA works offline and nothing is fetched from Google at runtime (privacy: the
app serves minors in the EU).

`rubik-<subset>-<weight>.woff2` — static instances pulled from Google Fonts' `css2`
endpoint. Subsets: `hebrew`, `latin`, `latin-ext`. Weights: `400`, `500`, `700`.
The `@font-face` rules (with matching `unicode-range`) live in `css/base.css`.

Licensed under the SIL Open Font License 1.1 — see `OFL.txt`. Rubik v31.

To refresh: re-download from `https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;700`
with a modern browser User-Agent (older UAs get TTF, not woff2).
