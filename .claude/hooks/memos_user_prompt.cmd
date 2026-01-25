@echo off
REM MemOS Hook: UserPromptSubmit (Windows)
REM Triggered when user submits a prompt

REM Read input from stdin (not used in this simple hook)
REM Just return success JSON

echo {"continue": true, "suppressOutput": true}
exit /b 0
