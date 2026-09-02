# Build context is the repo root (see docker-compose.yml).
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.10.12 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/goodfog ./goodfog
ENV PYTHONPATH=/app PATH="/app/.venv/bin:$PATH"
# Baked in at build time (Coolify passes SOURCE_COMMIT as a build arg); reported by /api/health.
# Stored under a different name on purpose: Coolify's compose parser auto-creates an (empty)
# SOURCE_COMMIT app variable for any ${SOURCE_COMMIT} reference and injects it into the container's
# runtime env, which would override an image ENV of the same name. Settings falls back to BUILD_COMMIT.
ARG SOURCE_COMMIT=dev
ENV BUILD_COMMIT=${SOURCE_COMMIT}
RUN useradd -r -u 10001 app && chown -R app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"
CMD ["uvicorn", "goodfog.app:app", "--host", "0.0.0.0", "--port", "8000"]
