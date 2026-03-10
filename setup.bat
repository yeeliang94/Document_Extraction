@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   DocWeaver2 Enterprise Test - Setup
echo ========================================
echo.

:: ----------------------------------------
:: Check Python
:: ----------------------------------------
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH.
    echo         Install Python from https://www.python.org/downloads/
    echo         Or ask IT to add it to your PATH.
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] %PYVER%

:: ----------------------------------------
:: Check Node.js — install portable if missing
:: ----------------------------------------
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [!!] Node.js not found in PATH.
    echo      Downloading portable Node.js (no admin required^)...
    echo.

    if not exist "%~dp0node" mkdir "%~dp0node"

    set NODE_VER=v20.18.3
    set NODE_ZIP=node-!NODE_VER!-win-x64.zip
    set NODE_URL=https://nodejs.org/dist/!NODE_VER!/!NODE_ZIP!

    echo      Downloading !NODE_URL! ...
    powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!NODE_URL!' -OutFile '%~dp0node\!NODE_ZIP!' -UseBasicParsing }"

    if not exist "%~dp0node\!NODE_ZIP!" (
        echo [ERROR] Download failed. Check your internet or proxy settings.
        echo         If behind a proxy, set these first:
        echo           set HTTP_PROXY=http://your-proxy:port
        echo           set HTTPS_PROXY=http://your-proxy:port
        exit /b 1
    )

    echo      Extracting...
    powershell -Command "& { Expand-Archive -Path '%~dp0node\!NODE_ZIP!' -DestinationPath '%~dp0node' -Force }"
    del "%~dp0node\!NODE_ZIP!" 2>nul

    :: Rename extracted folder to a simple name
    for /d %%d in ("%~dp0node\node-*") do (
        if exist "%~dp0node\bin" rmdir /s /q "%~dp0node\bin"
        ren "%%d" "bin"
    )

    echo [OK] Portable Node.js installed to %~dp0node\bin
    echo.
) else (
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do set NODEVER=%%v
    echo [OK] Node.js !NODEVER!
)

:: Add portable node to PATH for this session
if exist "%~dp0node\bin" (
    set "PATH=%~dp0node\bin;%PATH%"
)

:: Verify node and npm work
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js still not available. Setup failed.
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo      node %%v
for /f "tokens=*" %%v in ('npm --version 2^>^&1') do echo      npm v%%v

:: ----------------------------------------
:: Backend setup
:: ----------------------------------------
echo.
echo --- Backend Setup ---

if not exist "%~dp0backend\.venv" (
    echo Creating Python virtual environment...
    python -m venv "%~dp0backend\.venv"
)

echo Installing Python dependencies...
call "%~dp0backend\.venv\Scripts\activate.bat"
pip install -r "%~dp0backend\requirements.txt" --quiet
call deactivate

if not exist "%~dp0backend\.env" (
    copy "%~dp0backend\.env.example" "%~dp0backend\.env" >nul
    echo [!!] Created backend\.env from template.
    echo      EDIT backend\.env with your proxy URL and API key before running!
)

echo [OK] Backend ready.

:: ----------------------------------------
:: Frontend setup
:: ----------------------------------------
echo.
echo --- Frontend Setup ---

cd /d "%~dp0frontend"
echo Installing npm dependencies...
call npm install --silent 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm install failed. Check errors above.
    echo         If behind a proxy, run:
    echo           npm config set proxy http://your-proxy:port
    echo           npm config set https-proxy http://your-proxy:port
    exit /b 1
)

echo [OK] Frontend ready.

:: ----------------------------------------
:: Done
:: ----------------------------------------
echo.
echo ========================================
echo   Setup complete!
echo.
echo   Next steps:
echo     1. Edit backend\.env with your API key
echo     2. Run start.bat to launch the app
echo ========================================
echo.

endlocal
