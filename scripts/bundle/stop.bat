@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: MemOS Bundle Stopper for Windows
:: 一键停止脚本 - 停止所有服务

echo.
echo ========================================
echo   MemOS 服务停止中...
echo   Stopping MemOS Services...
echo ========================================
echo.

:: ============================================
:: 停止 MemOS API (Python/uvicorn)
:: ============================================
echo [1/3] 停止 MemOS API...

for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":18000"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo       MemOS API 已停止

:: ============================================
:: 停止 Qdrant
:: ============================================
echo [2/3] 停止 Qdrant...

taskkill /F /IM qdrant.exe >nul 2>&1
echo       Qdrant 已停止

:: ============================================
:: 停止 Neo4j
:: ============================================
echo [3/3] 停止 Neo4j...

set "BUNDLE_ROOT=%~dp0..\.."
pushd "%BUNDLE_ROOT%"
set "BUNDLE_ROOT=%CD%"
popd

set "RUNTIME=%BUNDLE_ROOT%\runtime"
set "NEO4J_HOME=%RUNTIME%\neo4j"
set "JAVA_HOME=%RUNTIME%\jre"

if exist "%NEO4J_HOME%\bin\neo4j.bat" (
    call "%NEO4J_HOME%\bin\neo4j.bat" stop >nul 2>&1
)

:: 强制结束相关 Java 进程（Neo4j）
for /f "tokens=2" %%a in ('wmic process where "commandline like '%%neo4j%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo       Neo4j 已停止

echo.
echo ========================================
echo   所有服务已停止
echo   All services stopped
echo ========================================
echo.

pause
endlocal
