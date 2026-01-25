@echo off
REM Project Memory - Save memory to MemOS
REM Usage: memos-save.cmd "content" [-t TYPE] [-p PROJECT] [--tags tag1 tag2]

setlocal
set SCRIPT_DIR=%~dp0..
python "%SCRIPT_DIR%\memos_save.py" %*
endlocal
