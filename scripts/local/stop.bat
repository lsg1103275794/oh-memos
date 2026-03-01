@echo off
setlocal EnableDelayedExpansion

:: ============================================================
::  __  __                 ___  ____
:: |  \/  | ___ _ __ ___  / _ \/ ___|
:: | |\/| |/ _ \ '_ ` _ \| | | \___ \
:: | |  | |  __/ | | | | | |_| |___) |
:: |_|  |_|\___|_| |_| |_|\___/|____/
::
:: MemOS One-Click Stopper
:: Stops API server and all database services
:: ============================================================

title MemOS - Stopping Services

echo.
echo  ============================================================
echo   MemOS - Stopping All Services
echo  ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "MEMOS_ROOT=%SCRIPT_DIR%..\.."
set "NEO4J_HOME=D:\User\neo4j-community-5.15.0"

:: ============================================================
:: Phase 1: Stop MemOS API Server
:: ============================================================
echo  [1/3] Stopping MemOS API server...

:: Find uvicorn/python process listening on port 18000
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":18000 " ^| findstr "LISTENING"') do (
    set "API_PID=%%p"
)

if defined API_PID (
    taskkill /F /PID !API_PID! >nul 2>&1
    echo        [OK] API server stopped ^(PID: !API_PID!^)
) else (
    echo        [SKIP] API server not running
)

:: ============================================================
:: Phase 2: Stop Qdrant
:: ============================================================
echo  [2/3] Stopping Qdrant...

tasklist /FI "IMAGENAME eq qdrant.exe" 2>nul | find /I "qdrant.exe" >nul 2>&1
if !errorlevel! EQU 0 (
    taskkill /F /IM qdrant.exe >nul 2>&1
    echo        [OK] Qdrant stopped
) else (
    echo        [SKIP] Qdrant not running
)

:: ============================================================
:: Phase 3: Stop Neo4j
:: ============================================================
echo  [3/3] Stopping Neo4j...

netstat -ano 2>nul | findstr ":7687 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! EQU 0 (
    :: Try graceful stop via neo4j command first
    if exist "%NEO4J_HOME%\bin\neo4j.bat" (
        pushd "%NEO4J_HOME%\bin"
        call neo4j.bat stop >nul 2>&1
        popd
    )
    :: Kill remaining Java processes with neo4j in command line
    for /f "tokens=2" %%i in ('wmic process where "commandline like '%%neo4j%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
        taskkill /F /PID %%i >nul 2>&1
    )
    echo        [OK] Neo4j stopped
) else (
    echo        [SKIP] Neo4j not running
)

echo.
echo  ============================================================
echo   All MemOS services stopped.
echo.
echo   To restart: double-click start.bat
echo  ============================================================
echo.

pause
