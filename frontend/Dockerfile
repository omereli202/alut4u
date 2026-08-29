# Frontend image — Caddy serves the static PWA and reverse-proxies /api/* to the
# backend service over Railway's private network, so the browser sees one origin
# (cookie auth, service-worker scope and offline caching all stay same-origin).
# Build context: the frontend/ directory (Railway service root = "frontend").
FROM caddy:2-alpine

COPY Caddyfile /etc/caddy/Caddyfile
COPY . /srv
RUN rm -f /srv/Caddyfile

# Caddy reads $PORT (Railway) and $BACKEND_ORIGIN (set on the service, e.g.
# http://alut4u-backend.railway.internal:8080).
