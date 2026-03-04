@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: MemOS Runtime Downloader for Windows
:: 下载运行时组件：Miniconda, Neo4j, JRE, Qdrant

set "BUNDLE_ROOT=%~dp0..\.."
pushd "%BUNDLE_ROOT%"
set "BUNDLE_ROOT=%CD%"
popd

set "RUNTIME=%BUNDLE_ROOT%\runtime"
set "TEMP_DIR=%BUNDLE_ROOT%\temp"

:: 创建目录
if not exist "%RUNTIME%" mkdir "%RUNTIME%"
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: 组件版本
set "MINICONDA_VERSION=latest"
set "NEO4J_VERSION=5.28.0"
set "JRE_VERSION=17.0.13+11"
set "QDRANT_VERSION=1.15.3"

:: 下载 URL
set "MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
set "NEO4J_URL=https://dist.neo4j.org/neo4j-community-%NEO4J_VERSION%-windows.zip"
set "JRE_URL=https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.13%%2B11/OpenJDK17U-jre_x64_windows_hotspot_17.0.13_11.zip"
set "QDRANT_URL=https://github.com/qdrant/qdrant/releases/download/v%QDRANT_VERSION%/qdrant-x86_64-pc-windows-msvc.zip"

:: 获取要下载的组件
set "COMPONENT=%~1"

if "%COMPONENT%"=="" (
    echo.
    echo 用法: download_runtime.bat [component]
    echo.
    echo 可用组件 Available components:
    echo   conda  - Miniconda Python 3.11
    echo   neo4j  - Neo4j Community %NEO4J_VERSION%
    echo   jre    - OpenJDK 17 JRE
    echo   qdrant - Qdrant %QDRANT_VERSION%
    echo   all    - 下载所有组�?
    echo.
    exit /b 1
)

if "%COMPONENT%"=="all" (
    call :download_conda
    call :download_jre
    call :download_neo4j
    call :download_qdrant
    goto :cleanup
)

if "%COMPONENT%"=="conda" call :download_conda
if "%COMPONENT%"=="neo4j" call :download_neo4j
if "%COMPONENT%"=="jre" call :download_jre
if "%COMPONENT%"=="qdrant" call :download_qdrant

goto :cleanup

:: ============================================
:: 下载 Miniconda
:: ============================================
:download_conda
echo.
echo ========================================
echo   下载 Miniconda (Python 3.11)
echo ========================================

if exist "%RUNTIME%\conda\python.exe" (
    echo Miniconda 已存在，跳过下载
    exit /b 0
)

set "CONDA_INSTALLER=%TEMP_DIR%\miniconda.exe"

echo 正在下载 Miniconda...
curl -L -o "%CONDA_INSTALLER%" "%MINICONDA_URL%"
if errorlevel 1 (
    echo [ERROR] 下载失败，尝试使�?PowerShell...
    powershell -Command "Invoke-WebRequest -Uri '%MINICONDA_URL%' -OutFile '%CONDA_INSTALLER%'"
)

if not exist "%CONDA_INSTALLER%" (
    echo [ERROR] Miniconda 下载失败
    exit /b 1
)

echo 正在安装 Miniconda（静默模式）...
start /wait "" "%CONDA_INSTALLER%" /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%RUNTIME%\conda

:: 安装必要的包
echo 安装 Python 基础�?..
"%RUNTIME%\conda\python.exe" -m pip install --upgrade pip --quiet
"%RUNTIME%\conda\python.exe" -m pip install uvicorn fastapi httpx --quiet

echo Miniconda 安装完成 �?
exit /b 0

:: ============================================
:: 下载 OpenJDK JRE
:: ============================================
:download_jre
echo.
echo ========================================
echo   下载 OpenJDK 17 JRE
echo ========================================

if exist "%RUNTIME%\jre\bin\java.exe" (
    echo JRE 已存在，跳过下载
    exit /b 0
)

set "JRE_ZIP=%TEMP_DIR%\jre.zip"

echo 正在下载 OpenJDK 17...
curl -L -o "%JRE_ZIP%" "%JRE_URL%"
if errorlevel 1 (
    powershell -Command "Invoke-WebRequest -Uri '%JRE_URL%' -OutFile '%JRE_ZIP%'"
)

if not exist "%JRE_ZIP%" (
    echo [ERROR] JRE 下载失败
    exit /b 1
)

echo 正在解压 JRE...
powershell -Command "Expand-Archive -Path '%JRE_ZIP%' -DestinationPath '%TEMP_DIR%\jre_temp' -Force"

:: 移动到正确位�?
for /d %%i in ("%TEMP_DIR%\jre_temp\*") do (
    if exist "%%i\bin\java.exe" (
        move "%%i" "%RUNTIME%\jre" >nul
        goto :jre_done
    )
)
:jre_done
rmdir /s /q "%TEMP_DIR%\jre_temp" 2>nul

echo JRE 安装完成 �?
exit /b 0

:: ============================================
:: 下载 Neo4j
:: ============================================
:download_neo4j
echo.
echo ========================================
echo   下载 Neo4j Community %NEO4J_VERSION%
echo ========================================

if exist "%RUNTIME%\neo4j\bin\neo4j.bat" (
    echo Neo4j 已存在，跳过下载
    exit /b 0
)

set "NEO4J_ZIP=%TEMP_DIR%\neo4j.zip"

echo 正在下载 Neo4j...
curl -L -o "%NEO4J_ZIP%" "%NEO4J_URL%"
if errorlevel 1 (
    powershell -Command "Invoke-WebRequest -Uri '%NEO4J_URL%' -OutFile '%NEO4J_ZIP%'"
)

if not exist "%NEO4J_ZIP%" (
    echo [ERROR] Neo4j 下载失败
    exit /b 1
)

echo 正在解压 Neo4j...
powershell -Command "Expand-Archive -Path '%NEO4J_ZIP%' -DestinationPath '%TEMP_DIR%\neo4j_temp' -Force"

:: 移动到正确位�?
for /d %%i in ("%TEMP_DIR%\neo4j_temp\*") do (
    if exist "%%i\bin\neo4j.bat" (
        move "%%i" "%RUNTIME%\neo4j" >nul
        goto :neo4j_done
    )
)
:neo4j_done
rmdir /s /q "%TEMP_DIR%\neo4j_temp" 2>nul

:: 配置 Neo4j
echo 配置 Neo4j...
if exist "%RUNTIME%\neo4j\conf\neo4j.conf" (
    echo dbms.security.auth_enabled=false>> "%RUNTIME%\neo4j\conf\neo4j.conf"
    echo server.default_listen_address=0.0.0.0>> "%RUNTIME%\neo4j\conf\neo4j.conf"
)

echo Neo4j 安装完成 �?
exit /b 0

:: ============================================
:: 下载 Qdrant
:: ============================================
:download_qdrant
echo.
echo ========================================
echo   下载 Qdrant %QDRANT_VERSION%
echo ========================================

if exist "%RUNTIME%\qdrant\qdrant.exe" (
    echo Qdrant 已存在，跳过下载
    exit /b 0
)

set "QDRANT_ZIP=%TEMP_DIR%\qdrant.zip"

echo 正在下载 Qdrant...
curl -L -o "%QDRANT_ZIP%" "%QDRANT_URL%"
if errorlevel 1 (
    powershell -Command "Invoke-WebRequest -Uri '%QDRANT_URL%' -OutFile '%QDRANT_ZIP%'"
)

if not exist "%QDRANT_ZIP%" (
    echo [ERROR] Qdrant 下载失败
    exit /b 1
)

echo 正在解压 Qdrant...
if not exist "%RUNTIME%\qdrant" mkdir "%RUNTIME%\qdrant"
powershell -Command "Expand-Archive -Path '%QDRANT_ZIP%' -DestinationPath '%RUNTIME%\qdrant' -Force"

echo Qdrant 安装完成 �?
exit /b 0

:: ============================================
:: 清理临时文件
:: ============================================
:cleanup
echo.
echo 清理临时文件...
rmdir /s /q "%TEMP_DIR%" 2>nul
echo 完成�?

endlocal
