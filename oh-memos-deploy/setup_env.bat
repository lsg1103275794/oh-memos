@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

cd /d "%~dp0"

echo ========================================
echo    MemOS Environment Setup
echo    便携式 Python 环境安装
echo ========================================
echo.

REM Get absolute path (remove trailing backslash if present)
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "CONDA_DIR=%SCRIPT_DIR%\conda_venv"
set "MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
set "MINICONDA_INSTALLER=%SCRIPT_DIR%\miniconda_installer.exe"

echo [INFO] Installation paths:
echo.
echo        Script location:
echo        %SCRIPT_DIR%
echo.
echo        Python will be installed to:
echo        %CONDA_DIR%
echo.
echo        Python executable will be at:
echo        %CONDA_DIR%\python.exe
echo.
echo ----------------------------------------
echo.

REM Check if conda_venv already exists
if exist "%CONDA_DIR%\python.exe" (
    echo [INFO] conda_venv already exists!
    echo.
    echo        Existing Python: %CONDA_DIR%\python.exe
    echo.
    choice /C YN /M "Reinstall environment? (Y=Yes, N=No)"
    if errorlevel 2 goto :skip_install
    echo.
    echo [INFO] Removing existing environment...
    rmdir /s /q "%CONDA_DIR%" 2>nul
)

echo [1/4] Downloading Miniconda...
echo.
echo        Download URL:
echo        %MINICONDA_URL%
echo.
echo        Saving to:
echo        %MINICONDA_INSTALLER%
echo.
echo        This may take a few minutes depending on network speed...
echo.

REM Try PowerShell download first
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%MINICONDA_URL%' -OutFile '%MINICONDA_INSTALLER%'}" 2>nul

if not exist "%MINICONDA_INSTALLER%" (
    echo [WARN] PowerShell download failed, trying curl...
    curl -L -o "%MINICONDA_INSTALLER%" "%MINICONDA_URL%"
)

if not exist "%MINICONDA_INSTALLER%" (
    echo.
    echo [ERROR] Failed to download Miniconda
    echo.
    echo         Please download manually:
    echo         1. Open browser and go to:
    echo            %MINICONDA_URL%
    echo.
    echo         2. Save the file as:
    echo            %MINICONDA_INSTALLER%
    echo.
    echo         3. Run this script again
    echo.
    pause
    exit /b 1
)

echo        Download complete!
echo.

echo [2/4] Installing Miniconda (portable mode)...
echo.
echo        Installing to:
echo        %CONDA_DIR%
echo.
echo        This may take several minutes, please wait...
echo        (A new window may appear briefly)
echo.

start /wait "" "%MINICONDA_INSTALLER%" /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%CONDA_DIR%

if not exist "%CONDA_DIR%\python.exe" (
    echo.
    echo [ERROR] Miniconda installation failed
    echo.
    echo         Expected Python at:
    echo         %CONDA_DIR%\python.exe
    echo.
    echo         Please try running this script as Administrator
    echo.
    pause
    exit /b 1
)

echo        Installation complete!
echo.

echo [3/4] Cleaning up installer...
del "%MINICONDA_INSTALLER%" 2>nul
echo        Cleanup done!
echo.

echo [4/4] Verifying installation...
echo.
"%CONDA_DIR%\python.exe" --version
if errorlevel 1 (
    echo.
    echo [ERROR] Python verification failed
    pause
    exit /b 1
)
echo.
echo        Python verification OK!
echo.

:skip_install
echo.
echo ========================================
echo    Setup Complete! 安装完成!
echo ========================================
echo.
echo    [Installed Paths / 安装路径]
echo.
echo    Python executable / Python可执行文件:
echo    %CONDA_DIR%\python.exe
echo.
echo    Pip executable / Pip可执行文件:
echo    %CONDA_DIR%\Scripts\pip.exe
echo.
echo    Environment directory / 环境目录:
echo    %CONDA_DIR%
echo.
echo ========================================
echo.
echo    [Next Steps / 下一步]
echo.
echo    1. Run install_run.bat to install dependencies and start
echo       运行 install_run.bat 安装依赖并启动服务
echo.
echo    2. Or run run.bat if dependencies are already installed
echo       或运行 run.bat (如依赖已安装)
echo.
echo ========================================
echo.

pause
