@echo off
:: ============================================================
:: Register MemOS auto-start task
:: Self-elevates to Administrator automatically
:: ============================================================

title MemOS - Register Autostart

:: ── Self-elevate: relaunch as Administrator if needed ──────
net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo  [UAC] Requesting Administrator privileges...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

echo.
echo  ============================================================
echo   MemOS - Register Autostart Task
echo  ============================================================
echo.
echo  Registering MemOS autostart task...

set "VBS_PATH=G:\test\MemOS\scripts\local\autostart.vbs"

:: Remove old task if exists
schtasks /Delete /TN "MemOS_Autostart" /F >nul 2>&1

:: Create task: trigger at logon, delay 30s for system stability
schtasks /Create ^
    /TN "MemOS_Autostart" ^
    /TR "wscript.exe \"%VBS_PATH%\"" ^
    /SC ONLOGON ^
    /DELAY 0000:30 ^
    /RL HIGHEST ^
    /F

if %errorlevel% EQU 0 (
    echo.
    echo  [OK] Task registered successfully!
    echo.
    echo  - Starts automatically ~30s after Windows logon
    echo  - Balloon notification shows startup result
    echo  - Logs: G:\test\MemOS\logs\
    echo  - Status check: double-click MemOS_status.bat
    echo.
    echo  To manage: Task Scheduler ^> MemOS_Autostart
) else (
    echo.
    echo  [ERROR] Registration failed.
    echo          Please right-click and choose "Run as Administrator".
)

echo.
pause
