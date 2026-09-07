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

## Assistant & Heebo — typing-board alternate faces

`assistant-hebrew.woff2`, `heebo-hebrew.woff2` — the two alternate typefaces the
child can choose for a note in "הפתקים שלי" (the typing board). **Hebrew subset
only** (`unicode-range: U+0590-05FF …`); Latin glyphs fall through to Rubik. Both
are **variable** fonts — a single file spans weights 400–700, so `@font-face`
declares `font-weight: 400 700` and headings at 500 render natively.

Licensed under the SIL Open Font License 1.1 — see `OFL-Assistant.txt` /
`OFL-Heebo.txt`. Assistant v24, Heebo v28.

To refresh: re-download the `hebrew` subset woff2 URLs from
`https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&family=Heebo:wght@400;700`
with a modern browser User-Agent.
