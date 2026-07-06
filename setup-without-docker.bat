@echo off
setlocal

echo ========================================
echo   ForecastIQ - Setup (No Docker)
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed.
    echo Please install Python 3.10+ from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python found.
echo.

:: Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed.
    echo Please install Node.js 18+ from: https://nodejs.org/
    pause
    exit /b 1
)

echo Node.js found.
echo.

:: Create directories
echo Creating directories...
if not exist "backend\uploads" mkdir backend\uploads
if not exist "backend\outputs" mkdir backend\outputs
if not exist "frontend\node_modules" mkdir frontend\node_modules

:: Setup Backend
echo.
echo ========================================
echo   Setting up Backend...
echo ========================================
cd backend
echo Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python dependencies.
    pause
    exit /b 1
)
cd ..

:: Setup Frontend
echo.
echo ========================================
echo   Setting up Frontend...
echo ========================================
cd frontend
echo Installing Node dependencies...
call npm install
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Node dependencies.
    pause
    exit /b 1
)
cd ..

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo To start ForecastIQ:
echo.
echo   1. Open terminal in backend folder and run:
echo      uvicorn app.main:app --reload --port 8000
echo.
echo   2. Open another terminal in frontend folder and run:
echo      npm run dev
echo.
echo Or use the Docker option for simpler startup.
echo.

pause
