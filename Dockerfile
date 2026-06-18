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

# 使用清华 PyPI 镜像加速国内构建
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

COPY pyproject.toml uv.lock* ./
# 去掉 --frozen：让 uv 从镜像重新解析，避开锁文件中 files.pythonhosted.org 的境外下载 URL
# pyproject.toml 的版本约束足以保证依赖兼容性
RUN uv sync --no-dev

COPY src/ ./src/
COPY scripts/ ./scripts/
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
