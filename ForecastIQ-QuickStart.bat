@echo off
echo ========================================
echo   ForecastIQ - Quick Start
echo ========================================
echo.

:: Check if Docker is available
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Docker detected! Using Docker setup...
    echo.
    call start-with-docker.bat
    goto :end
)

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Python detected! Starting with Python...
    echo.
    goto :python_setup
)

:: Neither Docker nor Python available
echo.
echo ERROR: Neither Docker nor Python is available.
echo.
echo Please choose one option:
echo.
echo   1. Install Docker (recommended):
echo      https://www.docker.com/products/docker-desktop/
echo.
echo   2. Install Python + Node.js:
echo      Python: https://www.python.org/downloads/
echo      Node.js: https://nodejs.org/
echo.
pause
exit /b 1

:python_setup
echo.
echo NOTE: This will start backend on port 8000
echo       You need to manually start frontend in another terminal
echo.

:end
pause
