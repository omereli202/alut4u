# REST API

Base path `/api`. JSON in/out. Auth is a signed HttpOnly cookie
(`alut4u_sid`) — send `credentials: "include"`; no tokens in JS.

Error shape: `{ "error": "<code>", "detail"?: "<human string>" }`.

Guards: **S** = valid session required · **C** = Caregiver Mode (live PIN
elevation) required.

## Auth & session — `/api/auth`

| Method | Path | Guard | Notes |
|---|---|---|---|
| POST | `/signup` | — | `{email, password, display_name, accept_terms:true}` → 201 + sets cookie, records `terms` consent. Rate-limited. |
| POST | `/login` | — | `{email, password}` → sets cookie. Rate-limited. |
| POST | `/logout` | S | revokes the device session, clears cookie. 204. |
| GET | `/session` | S | `{caregiver_id, mode, elevated_until, onboarding:{needs_pin,needs_terms,voice_consent}}` |
| PUT | `/pin` | S | set PIN. Onboarding: allowed. Changing an existing PIN: needs **C**. Rejects weak PINs. 204. |
| POST | `/pin` | S | verify PIN → grants Caregiver Mode. 429 `pin_locked` after 5 fails (60s→5m→15m). Rate-limited. |
| DELETE | `/pin/elevation` | S | drop back to User Mode. 204. |
| POST | `/terms` | S | `{accept:true}` re-records terms consent (version bump). 204. |
| POST | `/voice-consent` | C | `{accept:true}` → sets `voice_consent_at`, records consent. 204. |
| GET | `/devices` | C | signed-in devices (no token columns). |
| DELETE | `/devices/<id>` | C | revoke a device session. 204. |

## Children & modules — `/api/children`

| Method | Path | Guard | Notes |
|---|---|---|---|
| GET | `` | S | `{children:[…]}` active children (User Mode needs this). |
| POST | `` | C | `{name, consent_basis, birth_date?, avatar_seed?, parental_consent_attested?}`. `professional_with_parental_consent` requires the attestation → records a `professional_attestation` consent row. 201. |
| GET | `/<id>` | S | one child. 404 if not the caregiver's (RLS). |
| PATCH | `/<id>` | C | `{name?, birth_date?, avatar_seed?}`. |
| DELETE | `/<id>` | C | soft delete (`is_active=false`). 204. |
| GET | `/<id>/modules` | S | the 6 `*_enabled` booleans. |
| PUT | `/<id>/modules` | C | partial patch of the 6 booleans. |

## Account (GDPR) — `/api/account`

| Method | Path | Guard | Notes |
|---|---|---|---|
| GET | `/export` | C | JSON attachment: caregiver, children, module_settings, consent_records, devices, usage_counters. (Media bundle added in Phase 2.) |
| DELETE | `` | C | `{confirm:"DELETE"}` → deletes the auth user + cascade, clears cookie. 204. |

## Health — `/api/health`

`GET /api/health` → `{status, env, version}`. `?deep=1` also pings Supabase
(503 if unreachable).
