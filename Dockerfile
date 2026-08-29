# Deterministic build for Railway (both environments) and local parity.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY backend/ backend/
COPY frontend/ frontend/
RUN pip install ./backend

EXPOSE 8000

# $PORT is injected by Railway; the default is for local `docker run`.
CMD ["sh", "-c", "gunicorn --chdir backend 'app:create_app()' --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout 60 --access-logfile - --error-logfile -"]
