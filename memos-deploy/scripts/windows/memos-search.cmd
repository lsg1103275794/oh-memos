@echo off
REM Project Memory - Search memories in MemOS
REM Usage: memos-search.cmd "query" [-p PROJECT] [--all] [--json]

setlocal
set SCRIPT_DIR=%~dp0..
python "%SCRIPT_DIR%\memos_search.py" %*
endlocal
