@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: MemOS One-Click Launcher Template
::
:: INSTRUCTIONS:
:: 1. Copy this file to scripts/local/start.bat
:: 2. Edit the database paths below to match your system
:: 3. Double-click to run
::
:: PYTHON ENVIRONMENT:
:: - .venv (preferred): run VENV_scripts\setup_venv.bat first
:: - conda_venv (legacy): still supported as fallback
:: ============================================================

title MemOS - AI Memory System

echo.
echo  ============================================================
echo   MemOS - Privacy-First AI Memory System
echo  ============================================================
echo.

:: ============================================================
:: CONFIGURATION - EDIT DATABASE PATHS ONLY
:: ============================================================
set "Oh-MEMOS_ROOT=%~dp0..\.."
cd /d "%Oh-MEMOS_ROOT%"

:: Auto-detect Python environment: venv > conda_venv
if exist "%Oh-MEMOS_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%Oh-MEMOS_ROOT%\.venv\Scripts\python.exe"
    set "ENV_TYPE=venv"
) else if exist "%Oh-MEMOS_ROOT%\conda_venv\python.exe" (
    set "PYTHON_EXE=%Oh-MEMOS_ROOT%\conda_venv\python.exe"
    set "ENV_TYPE=conda_venv (legacy)"
) else (
    echo  [ERROR] No Python environment found!
    echo.
    echo  Please run setup first:
    echo    VENV_scripts\setup_venv.bat
    echo.
    pause
    exit /b 1
)

:: Database paths - MODIFY FOR YOUR SYSTEM
set "NEO4J_HOME=D:\User\neo4j-community-5.15.0"
set "QDRANT_HOME=D:\User\Qdrant"
:: ============================================================

:: Check Python
echo  [1/4] Checking Python environment...
if not exist "%PYTHON_EXE%" (
    echo        [ERROR] Python not found: %PYTHON_EXE%
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('"%PYTHON_EXE%" --version 2^>^&1') do set PYVER=%%v
echo        [OK] Python %PYVER% (%ENV_TYPE%)

:: Start Qdrant (silent)
echo  [2/4] Starting Qdrant...
netstat -ano 2>nul | findstr ":6333 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! NEQ 0 (
    if exist "%QDRANT_HOME%\qdrant.exe" (
        powershell -WindowStyle Hidden -Command "Start-Process -FilePath '%QDRANT_HOME%\qdrant.exe' -WorkingDirectory '%QDRANT_HOME%' -WindowStyle Hidden" >nul 2>&1
        timeout /t 2 /nobreak >nul
        echo        [OK] Qdrant started
    ) else (
        echo        [SKIP] Qdrant not found at %QDRANT_HOME%
    )
) else (
    echo        [OK] Qdrant already running
)

:: Start Neo4j (silent)
echo  [3/4] Starting Neo4j...
netstat -ano 2>nul | findstr ":7687 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! NEQ 0 (
    if exist "%NEO4J_HOME%\bin\neo4j.bat" (
        powershell -WindowStyle Hidden -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d \"%NEO4J_HOME%\bin\" && neo4j.bat console' -WindowStyle Hidden" >nul 2>&1
        echo        [OK] Neo4j started
        timeout /t 5 /nobreak >nul
    ) else (
        echo        [SKIP] Neo4j not found at %NEO4J_HOME%
    )
) else (
    echo        [OK] Neo4j already running
)

:: Sync config
echo  [4/4] Syncing configuration...
if exist ".env" copy /y ".env" "src\.env" >nul 2>&1
echo        [OK] Config synced

:: Start API
echo.
echo  ============================================================
echo   Server: http://localhost:18000
echo   Docs:   http://localhost:18000/docs
echo   Press Ctrl+C to stop
echo  ============================================================
echo.

cd /d "%Oh-MEMOS_ROOT%\src"
"%PYTHON_EXE%" -m uvicorn oh_memos.api.start_api:app --host 0.0.0.0 --port 18000 --reload

pause
