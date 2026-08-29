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
CMD ["sh", "-c", "gunicorn 'app:create_app()' --bind 0.0.0.0:${PORT:-8080} --workers ${WEB_CONCURRENCY:-2} --timeout 60 --access-logfile - --error-logfile -"]
