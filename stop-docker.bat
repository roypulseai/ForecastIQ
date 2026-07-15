@echo off
echo ========================================
echo   ForecastIQ - Stop Services
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
        pause
        exit /b 1
    )
)

%COMPOSE_CMD% down

echo.
echo ForecastIQ services stopped.
pause
