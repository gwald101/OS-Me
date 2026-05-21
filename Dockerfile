FROM python:3.12-slim

WORKDIR /app

# Install uv (pinned for reproducible builds)
COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /usr/local/bin/uv

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Copy app code
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY app/ ./app/

# Run as a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run migrations then start server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
