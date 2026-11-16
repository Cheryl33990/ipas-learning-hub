FROM ghcr.io/astral-sh/uv:0.9.11@sha256:5aa820129de0a600924f166aec9cb51613b15b68f1dcd2a02f31a500d2ede568 AS uv
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS base
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
ARG EMBEDDINGS=false
ARG CODE_VERSION=unavailable
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 UV_LINK_MODE=copy \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=/models/huggingface \
    PATH="/app/.venv/bin:$PATH" IPAS_CODE_VERSION=$CODE_VERSION
COPY pyproject.toml uv.lock ./
RUN if [ "$EMBEDDINGS" = "true" ]; then uv sync --locked --extra embeddings --no-dev --no-install-project; \
    else uv sync --locked --no-dev --no-install-project; fi
COPY src ./src
COPY config ./config
RUN if [ "$EMBEDDINGS" = "true" ]; then uv sync --locked --extra embeddings --no-dev --no-editable; \
    else uv sync --locked --no-dev --no-editable; fi

FROM base AS test
COPY tests ./tests
RUN uv sync --locked --group dev --no-editable \
    && python -m pytest -p no:cacheprovider

FROM base AS runtime
RUN mkdir -p /app/data /models/huggingface && chown -R 10001:10001 /app/data /models
USER 10001:10001
ENTRYPOINT ["python", "-m", "ipas_hub.cli"]
CMD ["--help"]
