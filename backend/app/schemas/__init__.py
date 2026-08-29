"""Pydantic request/response models, grouped by resource.

Response models must never include secret fields — notably ``pin_hash`` and
``refresh_token_enc``. Prefer an explicit output model over serializing a DB row.
"""
