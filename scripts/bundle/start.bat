@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: MemOS Bundle Starter for Windows
:: 一键启动脚本 - 启动所有服务

set "BUNDLE_ROOT=%~dp0..\.."
pushd "%BUNDLE_ROOT%"
set "BUNDLE_ROOT=%CD%"
popd

set "RUNTIME=%BUNDLE_ROOT%\runtime"

echo.
echo ========================================
echo   MemOS 服务启动中...
echo   Starting MemOS Services...
echo ========================================
echo.

:: 检查运行时是否存在
if not exist "%RUNTIME%\conda\python.exe" (
    echo [ERROR] 运行环境未安装，请先运行 install.bat
    echo [ERROR] Runtime not installed, please run install.bat first
    pause
    exit /b 1
)

:: ============================================
:: 自动检测并设置环境变量
:: ============================================

:: 检测 Java 路径 - 支持多种目录结构
set "JAVA_HOME="
if exist "%RUNTIME%\jre\bin\java.exe" (
    set "JAVA_HOME=%RUNTIME%\jre"
) else if exist "%RUNTIME%\jdk-24\bin\java.exe" (
    set "JAVA_HOME=%RUNTIME%\jdk-24"
) else (
    for /d %%D in ("%RUNTIME%\jdk*" "%RUNTIME%\jre*" "%RUNTIME%\java*") do (
        if exist "%%D\bin\java.exe" (
            set "JAVA_HOME=%%D"
        )
    )
)

if not defined JAVA_HOME (
    echo [ERROR] 未找到 Java 运行时，请运行 install.bat 安装
    pause
    exit /b 1
)

echo [ENV] JAVA_HOME = %JAVA_HOME%

:: 设置 PATH - 包含所有必要的路径
set "PATH=%JAVA_HOME%\bin;%RUNTIME%\conda;%RUNTIME%\conda\Scripts;%RUNTIME%\conda\Library\bin;%PATH%"
set "NEO4J_HOME=%RUNTIME%\neo4j"

:: 加载 .env 文件
if exist "%BUNDLE_ROOT%\.env" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%BUNDLE_ROOT%\.env") do (
        set "line=%%a"
        if not "!line:~0,1!"=="#" (
            if not "%%a"=="" set "%%a=%%b"
        )
    )
)

:: ============================================
:: Step 1: 启动 Qdrant
:: ============================================
echo [1/3] 启动 Qdrant (端口 6333)...

:: 检查 Qdrant 是否已运行
tasklist /FI "IMAGENAME eq qdrant.exe" 2>nul | find /I "qdrant.exe" >nul
if %errorlevel% equ 0 (
    echo       Qdrant 已在运行 ✓
) else (
    :: 确保 Qdrant 数据目录存在
    if not exist "%BUNDLE_ROOT%\data\qdrant" mkdir "%BUNDLE_ROOT%\data\qdrant"

    :: 启动 Qdrant（后台）
    start "Qdrant" /MIN cmd /c "cd /d %RUNTIME%\qdrant && qdrant.exe --storage-path %BUNDLE_ROOT%\data\qdrant"
    echo       Qdrant 启动中...
)

:: 等待 Qdrant 启动
timeout /t 3 /nobreak >nul

:: ============================================
:: Step 2: 启动 Neo4j
:: ============================================
echo [2/3] 启动 Neo4j (端口 7474/7687)...

:: 检查 Neo4j 是否已运行
tasklist /FI "IMAGENAME eq java.exe" 2>nul | find /I "java.exe" >nul
:: 简单检查，实际可能需要更精确的方法
netstat -an 2>nul | find ":7687" >nul
if %errorlevel% equ 0 (
    echo       Neo4j 已在运行 ✓
) else (
    :: 启动 Neo4j（后台）
    start "Neo4j" /MIN cmd /c "cd /d %NEO4J_HOME% && bin\neo4j.bat console"
    echo       Neo4j 启动中...
)

:: 等待 Neo4j 启动
echo       等待数据库就绪...
timeout /t 8 /nobreak >nul

:: ============================================
:: Step 3: 启动 MemOS API
:: ============================================
echo [3/3] 启动 MemOS API (端口 18000)...

:: 检查 API 是否已运行
netstat -an 2>nul | find ":18000" >nul
if %errorlevel% equ 0 (
    echo       MemOS API 已在运行 ✓
) else (
    :: 启动 API（前台，可以看到日志）
    cd /d "%BUNDLE_ROOT%"

    echo.
    echo ========================================
    echo   所有服务启动完成！
    echo   All services started!
    echo ========================================
    echo.
    echo   服务地址 Service URLs:
    echo   - MemOS API: http://localhost:18000/docs
    echo   - Neo4j:     http://localhost:7474
    echo   - Qdrant:    http://localhost:6333/dashboard
    echo.
    echo   按 Ctrl+C 停止 API 服务
    echo   Press Ctrl+C to stop API service
    echo.
    echo ----------------------------------------
    echo.

    "%RUNTIME%\conda\python.exe" -m uvicorn memos.api.start_api:app --host 0.0.0.0 --port 18000
)

pause
endlocal
