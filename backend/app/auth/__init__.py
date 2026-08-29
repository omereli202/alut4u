"""Authentication & session handling.

Landing in Phase 1:

* ``sessions.py`` — server-side Supabase Auth calls (sign-up / sign-in / reset),
  ``device_sessions`` rows, the signed HttpOnly session cookie, transparent
  access-token refresh, and per-device revocation.
* ``pin.py`` — argon2 PIN hashing/verification, escalating lockout, the
  time-boxed Caregiver-Mode elevation on the session.
* ``decorators.py`` — ``@require_session`` and ``@require_caregiver_mode`` for
  route protection, plus a helper that yields a request-scoped
  :func:`app.services.supabase_client.user_client`.

Nothing here is implemented yet (Phase 0 is scaffolding).
"""
