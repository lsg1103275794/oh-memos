@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: MemOS MCP Configuration for Claude Code
:: 自动配置 MCP �?Claude Code

set "BUNDLE_ROOT=%~dp0..\.."
pushd "%BUNDLE_ROOT%"
set "BUNDLE_ROOT=%CD%"
popd

:: 转换路径格式（Windows -> Unix-like for JSON�?
set "BUNDLE_ROOT_UNIX=%BUNDLE_ROOT:\=/%"

echo.
echo ========================================
echo   MemOS MCP 配置工具
echo   Configure MCP for Claude Code
echo ========================================
echo.

:: Claude Code 配置文件路径
set "CLAUDE_CONFIG=%USERPROFILE%\.claude\settings.json"
set "CLAUDE_CONFIG_DIR=%USERPROFILE%\.claude"

:: 检�?Claude Code 配置目录
if not exist "%CLAUDE_CONFIG_DIR%" (
    echo [INFO] 创建 Claude Code 配置目录...
    mkdir "%CLAUDE_CONFIG_DIR%"
)

echo.
echo ================================================
echo   MCP 配置信息 (MemOSlocal)
echo ================================================
echo.
echo   请将以下配置添加到您�?Claude Code settings:
echo.
echo   方式1: 使用 Claude Code 命令
echo   ----------------------------------
echo   �?Claude Code 中运�?
echo.
echo   /mcp add MemOSlocal
echo.
echo   然后输入以下配置:
echo   - command: %BUNDLE_ROOT%\runtime\conda\python.exe
echo   - args: %BUNDLE_ROOT%\mcp-server\MemOS_mcp_server.py
echo.
echo.
echo   方式2: 手动编辑配置文件
echo   ----------------------------------
echo   编辑文件: %CLAUDE_CONFIG%
echo.
echo   添加以下内容�?"mcpServers" 部分:
echo.
echo   {
echo     "mcpServers": {
echo       "MemOSlocal": {
echo         "command": "%BUNDLE_ROOT_UNIX%/runtime/conda/python.exe",
echo         "args": ["%BUNDLE_ROOT_UNIX%/mcp-server/MemOS_mcp_server.py"],
echo         "env": {
echo           "MemOS_URL": "http://localhost:18000",
echo           "MemOS_CUBES_DIR": "%BUNDLE_ROOT_UNIX%/data/MemOS_cubes"
echo         }
echo       }
echo     }
echo   }
echo.
echo ================================================
echo.

:: 生成配置模板文件
set "MCP_CONFIG_FILE=%BUNDLE_ROOT%\mcp-config.json"

echo 正在生成配置模板文件...
(
echo {
echo   "mcpServers": {
echo     "MemOSlocal": {
echo       "command": "%BUNDLE_ROOT_UNIX%/runtime/conda/python.exe",
echo       "args": ["%BUNDLE_ROOT_UNIX%/mcp-server/MemOS_mcp_server.py"],
echo       "env": {
echo         "MemOS_URL": "http://localhost:18000",
echo         "MemOS_CUBES_DIR": "%BUNDLE_ROOT_UNIX%/data/MemOS_cubes"
echo       }
echo     }
echo   }
echo }
) > "%MCP_CONFIG_FILE%"

echo.
echo 配置模板已保存到: %MCP_CONFIG_FILE%
echo.
echo ================================================
echo   下一�?Next Steps
echo ================================================
echo.
echo   1. 启动 MemOS 服务: start.bat
echo   2. �?Claude Code 中使�?MemOS_* 工具
echo.
echo   可用工具 Available Tools:
echo   - MemOS_search     : 搜索记忆
echo   - MemOS_save       : 保存记忆
echo   - MemOS_list       : 列出记忆
echo   - MemOS_list_cubes : 列出 Cubes
echo   - MemOS_suggest    : 智能建议
echo.
echo ================================================
echo.

pause
endlocal
