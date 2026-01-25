@echo off
REM ================================================
REM Project Memory Skill - Windows Installer
REM ================================================

echo ========================================
echo   Project Memory Skill Installer
echo   Platform: Windows
echo ========================================
echo.

REM Check Python
echo [1/4] Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.8+
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo       %%i found

REM Check MemOS
echo.
echo [2/4] Checking MemOS...
set MEMOS_URL=http://localhost:18000
curl -s --connect-timeout 3 %MEMOS_URL% >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo       MemOS available at %MEMOS_URL%
) else (
    echo       WARNING: MemOS not responding at %MEMOS_URL%
    echo       Make sure to start MemOS before using the skill
)

REM Create commands directory
echo.
echo [3/4] Creating command shortcuts...
set BIN_DIR=%USERPROFILE%\.local\bin
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

set SKILL_DIR=%USERPROFILE%\.claude\skills\project-memory

REM Create wrapper scripts
echo @echo off > "%BIN_DIR%\memos-save.cmd"
echo python "%SKILL_DIR%\scripts\memos_save.py" %%* >> "%BIN_DIR%\memos-save.cmd"

echo @echo off > "%BIN_DIR%\memos-search.cmd"
echo python "%SKILL_DIR%\scripts\memos_search.py" %%* >> "%BIN_DIR%\memos-search.cmd"

echo @echo off > "%BIN_DIR%\memos-init.cmd"
echo python "%SKILL_DIR%\scripts\memos_init_project.py" %%* >> "%BIN_DIR%\memos-init.cmd"

echo       Commands installed to %BIN_DIR%

REM Check PATH
echo.
echo [4/4] Checking PATH...
echo %PATH% | findstr /C:"%BIN_DIR%" >nul
if %ERRORLEVEL% NEQ 0 (
    echo       WARNING: %BIN_DIR% is not in PATH
    echo       Add it manually via:
    echo         System Properties ^> Environment Variables ^> Path ^> New
    echo       Or run:
    echo         setx PATH "%%PATH%%;%BIN_DIR%"
) else (
    echo       PATH OK
)

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Usage:
echo   memos-init                    # Initialize current project
echo   memos-save "content" -t TYPE  # Save a memory
echo   memos-search "query"          # Search memories
echo.
echo Environment variables (optional):
echo   MEMOS_URL    - MemOS API URL (default: http://localhost:18000)
echo   MEMOS_USER   - User ID (default: dev_user)
echo.

pause
