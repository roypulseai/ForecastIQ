#!/usr/bin/env bash
# ForecastIQ - Docker Setup (macOS / Linux)
# Build and start the full stack in Docker.
set -e

echo "========================================"
echo "  ForecastIQ - Docker Setup"
echo "========================================"
echo ""

# Detect docker compose command (v1 vs v2)
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    echo "ERROR: Docker Compose not found."
    echo "Install Docker Desktop (https://www.docker.com/products/docker-desktop)"
    echo "or 'brew install docker docker-compose' on macOS."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is not installed or not in PATH."
    echo "Please install Docker from: https://www.docker.com/products/docker-desktop/"
    echo ""
    echo "macOS:   brew install --cask docker"
    echo "Ubuntu:  sudo apt-get install docker.io docker-compose"
    echo "Fedora:  sudo dnf install docker docker-compose"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running."
    echo "macOS:   Start Docker Desktop and wait for it to initialize."
    echo "Linux:   sudo systemctl start docker"
    exit 1
fi

echo "Docker is running. Building and starting ForecastIQ..."
echo ""

# Stop any existing containers first
$COMPOSE_CMD down >/dev/null 2>&1 || true

# Build and start containers
$COMPOSE_CMD up -d --build

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to build or start containers."
    echo "Run '$COMPOSE_CMD logs' to see details."
    exit 1
fi

echo ""
echo "========================================"
echo "  ForecastIQ is starting!"
echo "========================================"
echo ""
echo "Frontend (UI):     http://localhost:3000"
echo "Backend (API):     http://localhost:8000"
echo "API Docs:          http://localhost:8000/docs"
echo ""
echo "Wait 10-30 seconds for services to fully start."
echo ""
echo "Useful commands:"
echo "  Stop:    $COMPOSE_CMD down"
echo "  View:    $COMPOSE_CMD logs -f"
echo "  Restart: $COMPOSE_CMD restart"
echo "  Status:  $COMPOSE_CMD ps"
echo ""
