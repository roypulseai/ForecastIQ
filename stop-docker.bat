@echo off
echo ========================================
echo   ForecastIQ - Stop Services
echo ========================================
echo.

docker-compose down

echo.
echo ForecastIQ services stopped.
pause
