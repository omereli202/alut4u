"""Flask extensions instantiated once, initialised in the app factory."""

from __future__ import annotations

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# In-memory store is fine for a single Railway instance. If the backend is ever
# scaled past one replica, point storage_uri at Redis.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["600 per hour"],
    storage_uri="memory://",
    strategy="fixed-window",
)
