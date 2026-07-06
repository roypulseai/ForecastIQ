@echo off
echo ========================================
echo   ForecastIQ - Docker Setup
echo ========================================
echo.

:: Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running.
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

echo Docker found. Starting ForecastIQ...
echo.

:: Build and start containers
docker-compose up -d --build

echo.
echo ========================================
echo   ForecastIQ is starting!
echo ========================================
echo.
echo Frontend (UI):     http://localhost:3000
echo Backend (API):    http://localhost:8000
echo API Docs:          http://localhost:8000/docs
echo.
echo To stop: docker-compose down
echo To view logs: docker-compose logs -f
echo.

pause
