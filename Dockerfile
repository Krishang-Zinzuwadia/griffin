# Griffin backend container: the FastAPI service plus the Python office pipeline.
# The API spawns "python -m ML.main" from the repo root (GRIFFIN_REPO_ROOT),
# so both ML/ and backend/api/ live in the image.
FROM python:3.12-slim

# git and curl are needed by the DevOps office (GitPython) in real mode and for health checks.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GRIFFIN_REPO_ROOT=/app

WORKDIR /app

# Install dependencies first for better layer caching.
COPY ML/requirements.txt ML/requirements.txt
COPY backend/api/requirements.txt backend/api/requirements.txt
RUN pip install -r ML/requirements.txt -r backend/api/requirements.txt

# Copy the pipeline and the API service.
COPY ML ML
COPY backend/api backend/api

WORKDIR /app/backend/api

# Cloud hosts inject PORT; default to 8000 locally. Shell form so PORT expands.
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
