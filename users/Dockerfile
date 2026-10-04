# Build context: repo root (uv.lock lives in the workspace root)
# docker build -f users/Dockerfile .
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY users/pyproject.toml users/pyproject.toml
COPY notifications/pyproject.toml notifications/pyproject.toml
COPY products/pyproject.toml products/pyproject.toml

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package users --no-install-workspace


FROM python:3.14-slim

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN useradd --system --no-create-home app

COPY --from=builder /app/.venv .venv
COPY users/main.py users/alembic.ini ./
COPY users/src src
COPY users/migrations migrations

USER app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
