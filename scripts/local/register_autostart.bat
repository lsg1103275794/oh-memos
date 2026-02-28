@echo off
:: ============================================================
:: 注册 MemOS 开机自动启动任务（只需运行一次）
:: 右键 → 以管理员身份运行
:: ============================================================
echo 正在注册 MemOS 开机自动启动任务...

set "VBS_PATH=G:\test\MemOS\scripts\local\autostart.vbs"

:: 删除旧任务（如果存在）
schtasks /Delete /TN "MemOS_Autostart" /F >nul 2>&1

:: 创建新任务：登录时触发，延迟 30 秒等系统稳定
schtasks /Create ^
    /TN "MemOS_Autostart" ^
    /TR "wscript.exe \"%VBS_PATH%\"" ^
    /SC ONLOGON ^
    /DELAY 0000:30 ^
    /RL HIGHEST ^
    /F

if %errorlevel% EQU 0 (
    echo.
    echo  [OK] 任务注册成功！
    echo.
    echo  效果：每次登录 Windows 后约 30 秒，MemOS 自动静默启动
    echo        启动完成后会弹出气泡通知告知状态
    echo.
    echo  管理：任务计划程序 ^> MemOS_Autostart
    echo  日志：G:\test\MemOS\logs\
    echo  状态：双击 memos_status.bat 随时查看
) else (
    echo.
    echo  [ERROR] 注册失败，请确认以管理员身份运行此脚本
)

pause
