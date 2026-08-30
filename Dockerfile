# ASGuard build image
FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ .
RUN npm run build

# ASGuard runtime image
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install dependencies first (cached layer — only rebuilds when deps change)
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.115" \
    "uvicorn>=0.32" \
    "httpx>=0.28" \
    "pydantic>=2.9" \
    "pydantic-settings>=2.6" \
    "sqlalchemy>=2.0.40" \
    "asyncpg>=0.30" \
    "alembic>=1.14" \
    "pyyaml>=6.0"

# Then the application code (needs to exist before `pip install .`)
COPY backend/src ./src
COPY backend/security_test_cases ./security_test_cases
RUN pip install --no-cache-dir --no-deps .

# Built dashboard, served by FastAPI
COPY --from=frontend-build /build/dist ./frontend/dist

EXPOSE 8000
CMD ["uvicorn", "asguard.api.main:app", "--host", "0.0.0.0", "--port", "8000"]