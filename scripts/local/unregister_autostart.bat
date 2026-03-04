@echo off
:: ============================================================
:: Unregister MemOS auto-start task
:: Self-elevates to Administrator automatically
:: ============================================================

title MemOS - Remove Autostart

:: ── Self-elevate: relaunch as Administrator if needed ──────
net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo  [UAC] Requesting Administrator privileges...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

echo.
echo  ============================================================
echo   MemOS - Remove Autostart Task
echo  ============================================================
echo.
echo  Checking for MemOS autostart task...

:: Check if task exists
schtasks /Query /TN "MemOS_Autostart" >nul 2>&1
if %errorlevel% NEQ 0 (
    echo.
    echo  [INFO] Task "MemOS_Autostart" not found.
    echo         Already removed or never registered.
    echo.
    pause
    exit /b 0
)

:: Delete the task
echo  Removing task...
schtasks /Delete /TN "MemOS_Autostart" /F

if %errorlevel% EQU 0 (
    echo.
    echo  [OK] Task "MemOS_Autostart" removed successfully!
    echo.
    echo  MemOS will no longer start automatically at Windows logon.
    echo.
    echo  To re-enable: run register_autostart.bat as Administrator
) else (
    echo.
    echo  [ERROR] Failed to remove task.
    echo          Please right-click and choose "Run as Administrator".
)

echo.
pause
