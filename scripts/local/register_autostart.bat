@echo off
:: ============================================================
:: Register MemOS auto-start task (run once as Administrator)
:: ============================================================
echo Registering MemOS autostart task...

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
    echo  - Status check: double-click memos_status.bat
    echo.
    echo  To manage: Task Scheduler ^> MemOS_Autostart
) else (
    echo.
    echo  [ERROR] Registration failed.
    echo  Please right-click this file and run as Administrator.
)

pause
