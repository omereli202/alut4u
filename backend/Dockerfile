# Backend image — Flask API only. No public domain in production; the frontend
# service reverse-proxies /api/* to it over Railway's private network.
# Build context: the backend/ directory (Railway service root = "backend").
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SERVE_FRONTEND=0

WORKDIR /app

COPY pyproject.toml ./
COPY app/ app/
RUN pip install .

EXPOSE 8080

# $PORT is injected by Railway; default is for local `docker run`.
# gthread workers: story compose runs 3 sequential Gemini calls + per-page TTS
# and legitimately takes 60-120s. A blocked thread must not take the whole
# worker down with it (health checks, other requests keep flowing), and the
# request timeout has to clear a slow compose. All three are env-overridable so
# ops can tune without a rebuild.
CMD ["sh", "-c", "gunicorn 'app:create_app()' --bind 0.0.0.0:${PORT:-8080} --workers ${WEB_CONCURRENCY:-2} --worker-class gthread --threads ${WEB_THREADS:-4} --timeout ${WEB_TIMEOUT:-180} --graceful-timeout 30 --access-logfile - --error-logfile -"]
