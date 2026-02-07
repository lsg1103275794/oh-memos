@echo off
REM ============================================================
REM MemOS Unified Venv Setup Script (Windows)
REM Creates .venv and installs MemOS + memos-cli
REM ============================================================
REM Usage: VENV_scripts\setup_venv.bat
REM Optional: set PYTHON_BIN=py -3.10
REM Optional: set INSTALL_ALL=true (install all optional deps)
REM Optional: set CLEAN=true (remove existing .venv first)

setlocal enabledelayedexpansion

echo.
echo  ============================================================
echo   MemOS Venv Setup
echo  ============================================================
echo.

:: Configuration
if "%PYTHON_BIN%"=="" set PYTHON_BIN=py -3.10
if "%INSTALL_ALL%"=="" set INSTALL_ALL=false
if "%CLEAN%"=="" set CLEAN=false

:: Navigate to project root
cd /d "%~dp0.."
set "PROJECT_ROOT=%cd%"
echo  [INFO] Project root: %PROJECT_ROOT%

:: Clean existing venv if requested
if /i "%CLEAN%"=="true" (
    if exist ".venv" (
        echo  [1/5] Removing existing .venv...
        rmdir /s /q .venv
        echo        [OK] Old venv removed
    )
)

:: Check Python
echo  [1/5] Checking Python...
%PYTHON_BIN% --version >nul 2>&1
if errorlevel 1 (
    echo        [ERROR] Python not found: %PYTHON_BIN%
    echo        Please install Python 3.10+ or set PYTHON_BIN
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('%PYTHON_BIN% --version 2^>^&1') do set PYVER=%%v
echo        [OK] Python %PYVER%

:: Create venv if not exists
if exist ".venv\Scripts\python.exe" (
    echo  [2/5] Using existing .venv
) else (
    echo  [2/5] Creating virtual environment...
    %PYTHON_BIN% -m venv .venv
    if errorlevel 1 (
        echo        [ERROR] Failed to create venv
        pause
        exit /b 1
    )
    echo        [OK] Created .venv
)

:: Activate venv
echo  [3/5] Activating venv...
call .\.venv\Scripts\activate.bat
if errorlevel 1 (
    echo        [ERROR] Failed to activate venv
    pause
    exit /b 1
)
echo        [OK] Activated

:: Upgrade pip
echo  [4/5] Upgrading pip...
python -m pip install --upgrade pip -q
if errorlevel 1 (
    echo        [WARN] pip upgrade failed, continuing...
)
echo        [OK] pip upgraded

:: Install dependencies
echo  [5/5] Installing dependencies...
if /i "%INSTALL_ALL%"=="true" (
    echo        Installing main project with all extras...
    pip install -e ".[all]" -q
) else (
    echo        Installing main project (core only)...
    pip install -e ".[tree-mem,mcp-server]" -q
)
if errorlevel 1 (
    echo        [ERROR] Failed to install main project
    pause
    exit /b 1
)
echo        [OK] Main project installed

echo        Installing memos-cli...
pip install -e memos-cli -q
if errorlevel 1 (
    echo        [ERROR] Failed to install memos-cli
    pause
    exit /b 1
)
echo        [OK] memos-cli installed

:: Summary
echo.
echo  ============================================================
echo   Setup Complete!
echo  ============================================================
echo.
echo   Venv location: %PROJECT_ROOT%\.venv
echo   Python:        .venv\Scripts\python.exe
echo.
echo   Activate later:
echo     .\.venv\Scripts\activate.bat
echo.
echo   Start MemOS:
echo     scripts\local\start.bat
echo.
echo  ============================================================

endlocal
