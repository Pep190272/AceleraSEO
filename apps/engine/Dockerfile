# ─────────────────────────────────────────────────────────────
# AceleraSEO engine — multi-stage build.
# Stage 1 installs deps into a venv; stage 2 is a slim runtime.
# Build context = apps/engine (see docker-compose.yml).
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /build
RUN python -m venv /opt/venv

# pyproject's `readme = "../../README.md"` points outside this build context, so
# drop that line for the image build (long-description is irrelevant at runtime).
COPY pyproject.toml ./
RUN sed -i '/^readme = /d' pyproject.toml

COPY src ./src
RUN pip install .

# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_PORT=8000

# Never run a web service as root.
RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY src ./src

# Writable dir for the SQLite DB + OAuth token cache (mounted as a volume).
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx,sys; sys.exit(0 if httpx.get('http://127.0.0.1:8000/health').status_code==200 else 1)"

CMD ["sh", "-c", "uvicorn aceleraseo.interfaces.api.app:app --host 0.0.0.0 --port ${APP_PORT} --app-dir src"]
