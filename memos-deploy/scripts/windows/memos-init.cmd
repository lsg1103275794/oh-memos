@echo off
REM Project Memory - Initialize project memory cube
REM Usage: memos-init.cmd [-p PROJECT] [-u USER]

setlocal
set SCRIPT_DIR=%~dp0..
python "%SCRIPT_DIR%\memos_init_project.py" %*
endlocal
