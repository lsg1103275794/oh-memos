@echo off
REM MemOS MCP Quick Setup for Windows Projects
REM Usage: Run this script in any project directory to enable MemOS MCP

echo Creating .mcp.json in current directory...

(
echo {
echo   "mcpServers": {
echo     "MemOS": {
echo       "command": "wsl",
echo       "args": [
echo         "bash",
echo         "/mnt/g/test/MemOS/mcp-server/run_mcp.sh"
echo       ],
echo       "env": {
echo         "MemOS_URL": "http://localhost:18000",
echo         "MemOS_USER": "dev_user",
echo         "MemOS_DEFAULT_CUBE": "dev_cube"
echo       }
echo     }
echo   }
echo }
) > .mcp.json

echo.
echo Done! MemOS MCP has been configured for this project.
echo Restart Claude Code to activate.
pause
