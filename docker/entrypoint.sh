#!/bin/bash
set -e

echo "[entrypoint] Starting codex-switch-server..."

mkdir -p /app/data/packages

if [ ! -f /etc/nginx/ssl/codexswtich.cloud_bundle.crt ]; then
    echo "[entrypoint] WARNING: SSL certificate not found at /etc/nginx/ssl/codexswtich.cloud_bundle.crt"
    echo "[entrypoint] HTTPS will not work. Mount certs directory to /etc/nginx/ssl:ro"
fi

if [ -z "$ADMIN_TOKEN" ]; then
    echo "[entrypoint] WARNING: ADMIN_TOKEN is not set, admin panel will not be accessible"
fi

echo "[entrypoint] Starting supervisor (nginx + uvicorn)..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
