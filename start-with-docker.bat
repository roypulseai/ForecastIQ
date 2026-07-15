@echo off
echo ========================================
echo   ForecastIQ - Docker Setup
echo ========================================
echo.

:: Detect docker compose command (v2 vs v1)
set COMPOSE_CMD=docker-compose
docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    set COMPOSE_CMD=docker compose
) else (
    docker-compose --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Docker Compose not found.
        echo Install Docker Desktop from: https://www.docker.com/products/docker-desktop/
        pause
        exit /b 1
    )
)

:: Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not in PATH.
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

:: Check if Docker daemon is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker daemon is not running.
    echo Please start Docker Desktop and wait for it to initialize.
    pause
    exit /b 1
)

echo Docker is running. Building and starting ForecastIQ...
echo.

:: Stop any existing containers first
%COMPOSE_CMD% down >nul 2>&1

:: Build and start containers
%COMPOSE_CMD% up -d --build

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to build or start containers.
    echo Please check the logs above for errors.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ForecastIQ is starting!
echo ========================================
echo.
echo Frontend (UI):     http://localhost:3000
echo Backend (API):     http://localhost:8000
echo API Docs:          http://localhost:8000/docs
echo.
echo Wait 10-20 seconds for services to fully start.
echo.
echo To stop:    %COMPOSE_CMD% down
echo To view:    %COMPOSE_CMD% logs -f
echo To restart: %COMPOSE_CMD% restart
echo.

pause
