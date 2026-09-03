# PCS / Boardmaker symbol set — bundled for `dev` only

The PNGs in this folder are **Picture Communication Symbols (PCS)**, authored by
Mayer-Johnson and distributed with Boardmaker (now Tobii Dynavox). They were
imported from a PowerPoint export supplied by the project owner
(`scripts/build_pcs_symbols.py`).

**PCS is proprietary. This set is NOT open-licensed** (unlike the Mulberry
Symbols at the parent folder, which are CC BY-SA 4.0).

It is bundled here to unblock design and testing on the `dev` environment. It
**must not be deployed to production / `main`** without a Boardmaker content
licence from Tobii Dynavox.

Enforcement:
- the DB rows carry `licence = 'proprietary (PCS / Boardmaker) — dev only'`, `source = 'Boardmaker PCS (Mayer-Johnson / Tobii Dynavox)'`
- the migration is named `*_pcs_symbols.sql`
- `scripts/release.sh` aborts the release if that migration is present and the
  target is the production environment

To remove the set entirely: delete this folder, delete
`supabase/migrations/*_pcs_symbols.sql` and `scripts/data/pcs_manifest.json`,
and revert the `core_overrides` re-skin of the 36 `*.svg` files (re-run
`scripts/build_symbols.py --apply`).
