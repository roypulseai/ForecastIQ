#!/usr/bin/env bash
# ForecastIQ - Stop Docker containers (macOS / Linux)
set -e

if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    echo "Docker Compose not found."
    exit 1
fi

echo "Stopping ForecastIQ containers..."
$COMPOSE_CMD down
echo "Done."
