@echo off
echo ============================================================
echo    WaterWatch - Complete Demo Launcher
echo ============================================================
echo.
echo This script starts:
echo   - Landing Page (Next.js) on port 3000
echo   - Login Portal (Dash) on port 8050  
echo   - Dashboard (Dash) on port 8051
echo.
echo ============================================================
echo.

:: Start the Python Login App (which also starts the dashboard)
echo [1/2] Starting Login Portal + Dashboard...
cd /d "%~dp0frontend"
start "WaterWatch-Backend" cmd /c "python login_app.py"

:: Wait for Python apps to start
echo Waiting for backend services...
timeout /t 4 /nobreak > nul

:: Start the Next.js Landing Page
echo [2/2] Starting Landing Page...
cd /d "d:\End Use Projects\AQUA-GOV-Landing-Page\src\aqua-gov-app"
start "WaterWatch-Frontend" cmd /c "npm run dev"

:: Wait for Next.js to compile
echo Waiting for frontend to compile...
timeout /t 6 /nobreak > nul

echo.
echo ============================================================
echo    WaterWatch is Ready!
echo ============================================================
echo.
echo    Landing Page:  http://localhost:3000
echo    Login Portal:  http://localhost:8050
echo    Dashboard:     http://localhost:8051
echo.
echo    Demo Credentials:
echo      - admin / admin123
echo      - operator / operator123
echo.
echo ============================================================
echo.

:: Open the landing page in default browser
start http://localhost:3000

echo.
echo Press any key to STOP all services and exit...
pause > nul

:: Cleanup
echo.
echo Shutting down WaterWatch services...
taskkill /FI "WINDOWTITLE eq WaterWatch-Backend*" /F > nul 2>&1
taskkill /FI "WINDOWTITLE eq WaterWatch-Frontend*" /F > nul 2>&1
taskkill /IM node.exe /F > nul 2>&1
taskkill /IM python.exe /F > nul 2>&1
echo.
echo All services stopped. Goodbye!
timeout /t 2 > nul
