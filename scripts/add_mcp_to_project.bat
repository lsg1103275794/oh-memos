@echo off
REM MemOS MCP Quick Setup for Windows Projects
REM Usage: Run this script in any project directory to enable MemOS MCP

echo Creating .mcp.json in current directory...

(
echo {
echo   "mcpServers": {
echo     "memos": {
echo       "command": "wsl",
echo       "args": [
echo         "bash",
echo         "/mnt/g/test/MemOS/mcp-server/run_mcp.sh"
echo       ],
echo       "env": {
echo         "MEMOS_URL": "http://localhost:18000",
echo         "MEMOS_USER": "dev_user",
echo         "MEMOS_DEFAULT_CUBE": "dev_cube"
echo       }
echo     }
echo   }
echo }
) > .mcp.json

echo.
echo Done! MemOS MCP has been configured for this project.
echo Restart Claude Code to activate.
pause
