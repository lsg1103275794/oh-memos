@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: MemOS Bundle Installer for Windows
:: 一键安装脚�?- 自动配置运行环境

set "BUNDLE_ROOT=%~dp0..\.."
pushd "%BUNDLE_ROOT%"
set "BUNDLE_ROOT=%CD%"
popd

set "RUNTIME=%BUNDLE_ROOT%\runtime"
set "LOCAL_BACKUP=%BUNDLE_ROOT%\local_backup\runtime"
set "SCRIPTS=%BUNDLE_ROOT%\scripts\bundle"

echo.
echo ========================================
echo   MemOS 一键安装程�?
echo   MemOS Bundle Installer
echo ========================================
echo.

:: 确保 runtime 目录存在
if not exist "%RUNTIME%" mkdir "%RUNTIME%"

:: 显示配置路径
echo [INFO] 项目目录: %BUNDLE_ROOT%
echo [INFO] 运行时目�? %RUNTIME%
echo [INFO] 本地备份: %LOCAL_BACKUP%
echo.

:: ============================================
:: Step 1: 检�?下载 Python 环境
:: ============================================
echo [1/5] 检�?Python 环境...

if exist "%RUNTIME%\conda\python.exe" (
    echo       Python 已安�?�?
) else (
    echo       正在下载 Miniconda...
    call "%SCRIPTS%\download_runtime.bat" conda
    if errorlevel 1 (
        echo [ERROR] Python 环境安装失败
        goto :error
    )
)

:: ============================================
:: Step 2: 检�?下载 Java 运行�?
:: ============================================
echo [2/5] 检�?Java 运行�?..

:: 先检�?runtime 目录
set "JAVA_OK="
if exist "%RUNTIME%\jre\bin\java.exe" (
    echo       Java 已安�?(jre) �?
    set "JAVA_OK=1"
)
if not defined JAVA_OK (
    if exist "%RUNTIME%\jdk-24\bin\java.exe" (
        echo       Java 已安�?(jdk-24) �?
        set "JAVA_OK=1"
    )
)
:: 检查其�?jdk 目录
if not defined JAVA_OK (
    for /d %%D in ("%RUNTIME%\jdk*") do (
        if exist "%%D\bin\java.exe" (
            echo       Java 已安�?(%%~nxD) �?
            set "JAVA_OK=1"
        )
    )
)

:: 如果 runtime 没有，检�?local_backup
if not defined JAVA_OK (
    echo       检查本地备份目�?..
    set "JDK_FOUND="

    :: 检�?local_backup\runtime 下的 jdk/jre 目录
    if exist "%LOCAL_BACKUP%\jdk-24\bin\java.exe" (
        set "JDK_FOUND=%LOCAL_BACKUP%\jdk-24"
    )
    if not defined JDK_FOUND (
        for /d %%D in ("%LOCAL_BACKUP%\jdk*") do (
            if exist "%%D\bin\java.exe" set "JDK_FOUND=%%D"
        )
    )
    if not defined JDK_FOUND (
        for /d %%D in ("%LOCAL_BACKUP%\jre*") do (
            if exist "%%D\bin\java.exe" set "JDK_FOUND=%%D"
        )
    )

    if defined JDK_FOUND (
        echo       检测到本地 Java: !JDK_FOUND!
        echo       正在复制�?runtime 目录...

        :: 获取源目录名作为目标目录�?
        for %%F in ("!JDK_FOUND!") do set "JDK_NAME=%%~nxF"
        xcopy "!JDK_FOUND!" "%RUNTIME%\!JDK_NAME!\" /E /I /Q /Y >nul

        if exist "%RUNTIME%\!JDK_NAME!\bin\java.exe" (
            echo       Java 已从本地复制 �?
            set "JAVA_OK=1"
        ) else (
            echo [ERROR] Java 复制失败
            goto :error
        )
    )
)

:: 如果都没有，下载
if not defined JAVA_OK (
    echo       正在下载 OpenJDK 17...
    call "%SCRIPTS%\download_runtime.bat" jre
    if errorlevel 1 (
        echo [ERROR] Java 运行时安装失�?
        goto :error
    )
)

:: ============================================
:: Step 3: 检�?下载 Neo4j
:: ============================================
echo [3/5] 检�?Neo4j...

set "NEO4J_OK="
if exist "%RUNTIME%\neo4j\bin\neo4j.bat" (
    echo       Neo4j 已安�?�?
    set "NEO4J_OK=1"
)

:: 如果 runtime 没有，检�?local_backup
if not defined NEO4J_OK (
    echo       检查本地备份目�?..
    set "NEO4J_FOUND="

    :: 检查精确名�?
    if exist "%LOCAL_BACKUP%\neo4j\bin\neo4j.bat" (
        set "NEO4J_FOUND=%LOCAL_BACKUP%\neo4j"
    )
    :: 检查带版本号的目录
    if not defined NEO4J_FOUND (
        for /d %%D in ("%LOCAL_BACKUP%\neo4j*") do (
            if exist "%%D\bin\neo4j.bat" set "NEO4J_FOUND=%%D"
        )
    )

    if defined NEO4J_FOUND (
        echo       检测到本地 Neo4j: !NEO4J_FOUND!
        echo       正在复制�?runtime 目录...
        xcopy "!NEO4J_FOUND!" "%RUNTIME%\neo4j\" /E /I /Q /Y >nul
        if exist "%RUNTIME%\neo4j\bin\neo4j.bat" (
            echo       Neo4j 已从本地复制 �?
            set "NEO4J_OK=1"
        ) else (
            echo [ERROR] Neo4j 复制失败
            goto :error
        )
    )
)

:: 如果都没有，下载
if not defined NEO4J_OK (
    echo       正在下载 Neo4j Community...
    call "%SCRIPTS%\download_runtime.bat" neo4j
    if errorlevel 1 (
        echo [ERROR] Neo4j 安装失败
        goto :error
    )
)

:: ============================================
:: Step 4: 检�?下载 Qdrant
:: ============================================
echo [4/5] 检�?Qdrant...

set "QDRANT_OK="
if exist "%RUNTIME%\qdrant\qdrant.exe" (
    echo       Qdrant 已安�?�?
    set "QDRANT_OK=1"
)

:: 如果 runtime 没有，检�?local_backup
if not defined QDRANT_OK (
    echo       检查本地备份目�?..
    set "QDRANT_FOUND="

    :: 检查目录形�?
    if exist "%LOCAL_BACKUP%\qdrant\qdrant.exe" (
        set "QDRANT_FOUND=%LOCAL_BACKUP%\qdrant"
        set "QDRANT_IS_DIR=1"
    )
    :: 检查带版本号的目录
    if not defined QDRANT_FOUND (
        for /d %%D in ("%LOCAL_BACKUP%\qdrant*") do (
            if exist "%%D\qdrant.exe" (
                set "QDRANT_FOUND=%%D"
                set "QDRANT_IS_DIR=1"
            )
        )
    )
    :: 检查直接放置的 exe 文件
    if not defined QDRANT_FOUND (
        if exist "%LOCAL_BACKUP%\qdrant.exe" (
            set "QDRANT_FOUND=%LOCAL_BACKUP%\qdrant.exe"
            set "QDRANT_IS_DIR="
        )
    )

    if defined QDRANT_FOUND (
        echo       检测到本地 Qdrant: !QDRANT_FOUND!
        echo       正在复制�?runtime 目录...
        if not exist "%RUNTIME%\qdrant" mkdir "%RUNTIME%\qdrant"

        if defined QDRANT_IS_DIR (
            xcopy "!QDRANT_FOUND!" "%RUNTIME%\qdrant\" /E /I /Q /Y >nul
        ) else (
            copy "!QDRANT_FOUND!" "%RUNTIME%\qdrant\qdrant.exe" >nul
        )

        if exist "%RUNTIME%\qdrant\qdrant.exe" (
            echo       Qdrant 已从本地复制 �?
            set "QDRANT_OK=1"
        ) else (
            echo [ERROR] Qdrant 复制失败
            goto :error
        )
    )
)

:: 如果都没有，下载
if not defined QDRANT_OK (
    echo       正在下载 Qdrant...
    call "%SCRIPTS%\download_runtime.bat" qdrant
    if errorlevel 1 (
        echo [ERROR] Qdrant 安装失败
        goto :error
    )
)

:: ============================================
:: Step 5: 安装 Python 依赖
:: ============================================
echo [5/5] 安装 Python 依赖...

:: 设置 Python 环境
set "PATH=%RUNTIME%\conda;%RUNTIME%\conda\Scripts;%RUNTIME%\conda\Library\bin;%PATH%"

:: 安装项目依赖
pushd "%BUNDLE_ROOT%"

:: 首先安装 requirements-bundle.txt 中的所有依�?
echo       正在安装依赖�?(可能需要几分钟)...
if exist "%BUNDLE_ROOT%\requirements-bundle.txt" (
    "%RUNTIME%\conda\python.exe" -m pip install -r "%BUNDLE_ROOT%\requirements-bundle.txt" --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo [WARNING] 部分依赖安装失败，继续安装核心包...
    ) else (
        echo       依赖包安装完�?�?
    )
)

:: 安装 MemOS 本体（开发模式）
echo       正在安装 MemOS 核心...
"%RUNTIME%\conda\python.exe" -m pip install -e . --quiet --disable-pip-version-check
if errorlevel 1 (
    echo [ERROR] MemOS 安装失败
    goto :error
)
echo       MemOS 安装完成 �?

popd

:: ============================================
:: 初始化配置文�?
:: ============================================
echo.
echo 初始化配置文�?..

if not exist "%BUNDLE_ROOT%\.env" (
    if exist "%BUNDLE_ROOT%\.env.bundle.example" (
        copy "%BUNDLE_ROOT%\.env.bundle.example" "%BUNDLE_ROOT%\.env" >nul
        echo       已创�?.env 配置文件
    )
)

:: 创建数据目录
if not exist "%BUNDLE_ROOT%\data\MemOS_cubes\dev_cube" (
    mkdir "%BUNDLE_ROOT%\data\MemOS_cubes\dev_cube" 2>nul
    echo       已创�?dev_cube 目录
)

:: 创建 dev_cube 配置文件
if not exist "%BUNDLE_ROOT%\data\MemOS_cubes\dev_cube\config.json" (
    echo { > "%BUNDLE_ROOT%\data\MemOS_cubes\dev_cube\config.json"
    echo   "cube_id": "dev_cube", >> "%BUNDLE_ROOT%\data\MemOS_cubes\dev_cube\config.json"
    echo   "user_name": "dev_cube", >> "%BUNDLE_ROOT%\data\MemOS_cubes\dev_cube\config.json"
    echo   "memory_mode": "tree_text", >> "%BUNDLE_ROOT%\data\MemOS_cubes\dev_cube\config.json"
    echo   "storage_path": "data/MemOS_cubes/dev_cube" >> "%BUNDLE_ROOT%\data\MemOS_cubes\dev_cube\config.json"
    echo } >> "%BUNDLE_ROOT%\data\MemOS_cubes\dev_cube\config.json"
    echo       已创�?dev_cube 配置文件
)

:: 创建 Qdrant 数据目录
if not exist "%BUNDLE_ROOT%\data\qdrant" (
    mkdir "%BUNDLE_ROOT%\data\qdrant" 2>nul
)

:: ============================================
:: 配置 Neo4j 初始密码
:: ============================================
echo.
echo 配置 Neo4j...

set "NEO4J_HOME=%RUNTIME%\neo4j"

:: 设置 JAVA_HOME - 支持多种 Java 目录结构
if exist "%RUNTIME%\jre\bin\java.exe" (
    set "JAVA_HOME=%RUNTIME%\jre"
) else if exist "%RUNTIME%\jdk-24\bin\java.exe" (
    set "JAVA_HOME=%RUNTIME%\jdk-24"
) else (
    for /d %%D in ("%RUNTIME%\jdk*" "%RUNTIME%\jre*") do (
        if exist "%%D\bin\java.exe" set "JAVA_HOME=%%D"
    )
)

:: 设置 Neo4j 配置
if exist "%NEO4J_HOME%\conf\neo4j.conf" (
    :: 检查是否已配置
    findstr /C:"dbms.security.auth_enabled=false" "%NEO4J_HOME%\conf\neo4j.conf" >nul 2>&1
    if errorlevel 1 (
        echo dbms.security.auth_enabled=false>> "%NEO4J_HOME%\conf\neo4j.conf"
        echo       Neo4j 认证已禁用（开发模式）
    )
)

:: ============================================
:: 安装完成
:: ============================================
echo.
echo ========================================
echo   安装完成�?Installation Complete!
echo ========================================
echo.
echo   下一�?Next Steps:
echo.
echo   1. 编辑 .env 配置 LLM API Key
echo      Edit .env to configure your LLM API Key
echo.
echo   2. 运行 configure_mcp.bat 配置 Claude Code
echo      Run configure_mcp.bat to setup Claude Code MCP
echo.
echo   3. 运行 start.bat 启动服务
echo      Run start.bat to start all services
echo.
echo ========================================
echo.

goto :end

:error
echo.
echo ========================================
echo   安装失败！请检查错误信�?
echo   Installation failed! Please check errors above
echo ========================================
echo.

:end
pause
endlocal
