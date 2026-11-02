# MVP académico: ejecución no privilegiada, sin claves API incorporadas a la imagen.
# uv y Python están fijados a versiones de referencia; actualizarlos de forma conjunta.
FROM ghcr.io/astral-sh/uv:0.10.0 AS uv-bin

FROM python:3.12-slim-bookworm AS builder
COPY --from=uv-bin /uv /uvx /usr/local/bin/
WORKDIR /app
ENV UV_NO_DEV=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
ARG WITH_DASHBOARD=false
# Se usa uv.lock versionado; sin él la construcción debe fallar (reproducibilidad).
COPY . .
RUN if [ "$WITH_DASHBOARD" = "true" ]; then \
      uv sync --locked --no-dev --group dashboard --no-install-project; \
    else \
      uv sync --locked --no-dev --no-install-project; \
    fi

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:${PATH}" \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_ANALYTICS_ENABLED=False \
    HF_HUB_DISABLE_TELEMETRY=1 \
    GRADIO_TEMP_DIR=/tmp/gradio \
    HOME=/tmp \
    PORT=7860 \
    VANTRA_MODE=DEMO
RUN groupadd --system vantra && useradd --system --gid vantra --home-dir /tmp vantra \
    && mkdir -p /state && chown -R vantra:vantra /state
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --chown=vantra:vantra app.py ./app.py
COPY --chown=vantra:vantra src ./src
COPY --chown=vantra:vantra scripts ./scripts
COPY --chown=vantra:vantra data ./data
COPY --chown=vantra:vantra analytics ./analytics
COPY --chown=vantra:vantra dashboard.py ./dashboard.py
COPY --chown=vantra:vantra results ./results
USER vantra
EXPOSE 7860
CMD ["python", "app.py"]
