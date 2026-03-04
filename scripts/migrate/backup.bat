@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: MemOS 数据库备份脚�?
:: 打包 Neo4j + Qdrant + 配置文件，用于迁移到其他电脑
:: ============================================================

title MemOS - Database Backup

echo.
echo  ============================================================
echo   MemOS Database Backup Tool
echo  ============================================================
echo.

:: 获取脚本目录和项目根目录
set "SCRIPT_DIR=%~dp0"
set "Oh-MEMOS_ROOT=%SCRIPT_DIR%..\.."
cd /d "%Oh-MEMOS_ROOT%"

:: 配置路径 - 根据你的实际安装位置修改
set "NEO4J_HOME=D:\User\neo4j-community-5.15.0"
set "QDRANT_HOME=D:\User\Qdrant"

:: 备份输出目录
set "BACKUP_DIR=%Oh-MEMOS_ROOT%\backups"
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set "DATE=%%c%%a%%b"
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set "TIME=%%a%%b"
set "BACKUP_NAME=MemOS_backup_%DATE%_%TIME%"
set "BACKUP_PATH=%BACKUP_DIR%\%BACKUP_NAME%"

echo  [INFO] Backup will be saved to:
echo         %BACKUP_PATH%
echo.

:: 创建备份目录
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
mkdir "%BACKUP_PATH%"
mkdir "%BACKUP_PATH%\neo4j"
mkdir "%BACKUP_PATH%\qdrant"
mkdir "%BACKUP_PATH%\config"

:: ============================================================
:: 1. 停止服务（如果运行中�?
:: ============================================================
echo  [1/5] Checking running services...

:: 检�?Neo4j
netstat -ano 2>nul | findstr ":7687 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! EQU 0 (
    echo        [WARN] Neo4j is running. Please stop it first for a clean backup.
    echo        Run: %NEO4J_HOME%\bin\neo4j stop
    set /p CONTINUE="       Continue anyway? (Y/N): "
    if /i not "!CONTINUE!"=="Y" exit /b 1
)

:: 检�?Qdrant
netstat -ano 2>nul | findstr ":6333 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! EQU 0 (
    echo        [WARN] Qdrant is running. Backup may be inconsistent.
)

echo        [OK] Service check complete

:: ============================================================
:: 2. 备份 Neo4j 数据
:: ============================================================
echo  [2/5] Backing up Neo4j...

if exist "%NEO4J_HOME%\data" (
    echo        Copying Neo4j data directory...
    xcopy /E /I /H /Y "%NEO4J_HOME%\data" "%BACKUP_PATH%\neo4j\data" >nul 2>&1
    if !errorlevel! EQU 0 (
        echo        [OK] Neo4j data backed up
    ) else (
        echo        [WARN] Neo4j backup may be incomplete
    )
) else (
    echo        [SKIP] Neo4j data directory not found
)

:: ============================================================
:: 3. 备份 Qdrant 数据
:: ============================================================
echo  [3/5] Backing up Qdrant...

if exist "%QDRANT_HOME%\storage" (
    echo        Copying Qdrant storage directory...
    xcopy /E /I /H /Y "%QDRANT_HOME%\storage" "%BACKUP_PATH%\qdrant\storage" >nul 2>&1
    if !errorlevel! EQU 0 (
        echo        [OK] Qdrant data backed up
    ) else (
        echo        [WARN] Qdrant backup may be incomplete
    )
) else (
    echo        [SKIP] Qdrant storage directory not found
)

:: ============================================================
:: 4. 备份配置文件
:: ============================================================
echo  [4/5] Backing up configuration...

:: .env 文件
if exist "%Oh-MEMOS_ROOT%\.env" (
    copy /Y "%Oh-MEMOS_ROOT%\.env" "%BACKUP_PATH%\config\.env" >nul
    echo        [OK] .env backed up
)

:: Cube 配置
if exist "%Oh-MEMOS_ROOT%\data\MemOS_cubes" (
    xcopy /E /I /H /Y "%Oh-MEMOS_ROOT%\data\MemOS_cubes" "%BACKUP_PATH%\config\MemOS_cubes" >nul 2>&1
    echo        [OK] Cube configs backed up
)

:: MCP 配置
if exist "%USERPROFILE%\.MemOS" (
    xcopy /E /I /H /Y "%USERPROFILE%\.MemOS" "%BACKUP_PATH%\config\user_MemOS" >nul 2>&1
    echo        [OK] User MCP configs backed up
)

:: ============================================================
:: 5. 创建压缩�?
:: ============================================================
echo  [5/5] Creating archive...

:: 创建备份信息文件
echo MemOS Backup > "%BACKUP_PATH%\BACKUP_INFO.txt"
echo Created: %DATE% %TIME% >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo Neo4j Home: %NEO4J_HOME% >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo Qdrant Home: %QDRANT_HOME% >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo. >> "%BACKUP_PATH%\BACKUP_INFO.txt"
echo To restore, run: scripts\migrate\restore.bat >> "%BACKUP_PATH%\BACKUP_INFO.txt"

:: 使用 PowerShell 压缩
powershell -Command "Compress-Archive -Path '%BACKUP_PATH%\*' -DestinationPath '%BACKUP_PATH%.zip' -Force" >nul 2>&1
if !errorlevel! EQU 0 (
    echo        [OK] Created %BACKUP_NAME%.zip
    :: 删除未压缩的目录
    rmdir /s /q "%BACKUP_PATH%"
) else (
    echo        [WARN] Could not create zip, backup saved as folder
)

:: ============================================================
:: 完成
:: ============================================================
echo.
echo  ============================================================
echo   Backup Complete!
echo  ============================================================
echo.
echo   Location: %BACKUP_DIR%\%BACKUP_NAME%.zip
echo.
echo   To restore on another machine:
echo     1. Copy the .zip file to the new machine
echo     2. Extract to MemOS project directory
echo     3. Run: scripts\migrate\restore.bat
echo.
echo  ============================================================

pause
endlocal
