# Privacy & compliance

Worldwide product handling data about **minors** → GDPR (EU) and COPPA (US,
under-13) both apply. This document is the engineering position; it is **not**
legal advice and does not substitute for a lawyer's review of the privacy
policy, terms, and DPA before public launch.

## Data we deliberately do NOT store server-side

- **Family photos** — feature cut. Calming Zone uses a bundled non-personal set.
- **The child's speech audio** — reading practice is caregiver pass/fail; no
  recording, no STT, nothing sent to any third party.

## Data we do store

| Data | Basis | Notes |
|---|---|---|
| Caregiver account (email, name) | contract | Supabase Auth. |
| Child name, birth date, avatar seed | caregiver-provided | Minimal. Birth date optional. |
| `consent_basis` + `consent_records` | legal obligation | Who consented, to what, which terms version, when, IP/UA. |
| Module settings, AAC cards, schedule, tokens, progress history | contract | The product. |
| Caregiver voice recordings | **explicit consent** | Only after `voice_consent_at`; UI disabled until then. |
| TTS audio cache | legitimate interest | Derived from card text; deduped; no personal identifier. |
| `usage_counters`, `audit_log` | legitimate interest / legal | Quotas, security, compliance. |

## Therapist accounts

A therapist holds data about someone else's child. `children.consent_basis` must
be `professional_with_parental_consent`, and creating the child records a
`professional_attestation` consent row + an `audit_log` entry. The product
assumes the therapist has obtained parental consent; it records the attestation.

## Data-subject rights (built in Phase 1, not deferred)

- `GET  /api/account/export` — full JSON of the caregiver's + children's data
  plus a bundle of their media assets.
- `DELETE /api/account` — hard cascade across all tables **and** Storage
  objects. Logged to `audit_log` (with `caregiver_id` nulled by FK
  `on delete set null`).

## Retention

Default: warn at 18 months of account inactivity, purge at 24. Implemented as a
scheduled `run_retention_purge` job (Phase 8). Absent a policy, children's data
would accumulate indefinitely — that is not acceptable.

## Storage & residency

- Supabase project in an **EU region** (strictest common denominator).
- All Storage buckets **private**; objects reachable only through the backend's
  authorized `/api/media/<id>` route.
- Refresh tokens encrypted at rest (Fernet). PIN argon2-hashed. TLS everywhere.
