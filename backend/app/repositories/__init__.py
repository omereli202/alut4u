"""Data-access layer.

**All** Supabase reads and writes go through a repository function here. Routes
in ``app/api/`` must not build queries directly — that keeps tenancy enforcement
in one auditable place.

Rules for every function in this package:

* Take the caller's authenticated client (or identity), never a bare
  service-role client unless the operation is on the
  ``ALLOWED_SERVICE_OPERATIONS`` list.
* Never trust a caller-supplied ``caregiver_id`` / ``child_id`` without verifying
  ownership first (RLS is the backstop, not the excuse to skip the check).
* Return plain dataclasses / dicts, not raw SDK response objects.

Modules land per phase: ``caregivers``, ``children``, ``module_settings``,
``consent``, ``media`` (Phase 1); ``aac`` (Phase 2); etc.
"""
