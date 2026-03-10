@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   DocWeaver2 Enterprise Test
echo ========================================
echo.

:: Add portable node to PATH if it exists
if exist "%~dp0node\bin" (
    set "PATH=%~dp0node\bin;%PATH%"
)

:: ----------------------------------------
:: Preflight checks
:: ----------------------------------------
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Run setup.bat first.
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Run setup.bat first.
    exit /b 1
)

if not exist "%~dp0backend\.venv" (
    echo [ERROR] Backend not set up. Run setup.bat first.
    exit /b 1
)

if not exist "%~dp0frontend\node_modules" (
    echo [ERROR] Frontend not set up. Run setup.bat first.
    exit /b 1
)

if not exist "%~dp0backend\.env" (
    echo [ERROR] backend\.env not found. Copy .env.example and add your API key.
    exit /b 1
)

:: ----------------------------------------
:: Start Backend (in a new window)
:: ----------------------------------------
echo Starting backend on http://localhost:8002 ...
start "DocWeaver2 Backend" cmd /k "cd /d "%~dp0backend" && call .venv\Scripts\activate.bat && python main.py"

:: Give backend a moment to start
timeout /t 2 /nobreak >nul

:: ----------------------------------------
:: Start Frontend (in a new window)
:: ----------------------------------------
echo Starting frontend on http://localhost:3000 ...

if exist "%~dp0node\bin" (
    start "DocWeaver2 Frontend" cmd /k "set "PATH=%~dp0node\bin;%PATH%" && cd /d "%~dp0frontend" && npm run dev"
) else (
    start "DocWeaver2 Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
)

:: ----------------------------------------
:: Done
:: ----------------------------------------
echo.
echo ========================================
echo   Both servers starting!
echo.
echo   Backend:  http://localhost:8002
echo   Frontend: http://localhost:3000
echo.
echo   Close the server windows to stop.
echo   Or press Ctrl+C in each window.
echo ========================================
echo.

endlocal
