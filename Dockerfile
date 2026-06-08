FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
        ca-certificates \
        curl && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/nginx/sites-enabled/default

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

RUN mkdir -p /app/data /etc/nginx/ssl /var/log/supervisor

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD curl -f http://localhost/ || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
