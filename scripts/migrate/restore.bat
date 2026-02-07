@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: MemOS 数据库恢复脚本
:: 从备份包恢复 Neo4j + Qdrant + 配置文件
:: ============================================================

title MemOS - Database Restore

echo.
echo  ============================================================
echo   MemOS Database Restore Tool
echo  ============================================================
echo.

:: 获取脚本目录和项目根目录
set "SCRIPT_DIR=%~dp0"
set "MEMOS_ROOT=%SCRIPT_DIR%..\.."
cd /d "%MEMOS_ROOT%"

:: 配置路径 - 根据你的实际安装位置修改
set "NEO4J_HOME=D:\User\neo4j-community-5.15.0"
set "QDRANT_HOME=D:\User\Qdrant"

:: 备份文件路径
set "BACKUP_FILE=%~1"
if "%BACKUP_FILE%"=="" (
    echo  [ERROR] Please specify backup file path
    echo.
    echo  Usage: restore.bat ^<backup.zip^>
    echo  Example: restore.bat backups\memos_backup_20260208.zip
    echo.

    :: 列出可用的备份
    if exist "%MEMOS_ROOT%\backups" (
        echo  Available backups:
        for %%f in ("%MEMOS_ROOT%\backups\*.zip") do (
            echo    - %%~nxf
        )
    )
    echo.
    pause
    exit /b 1
)

:: 检查备份文件是否存在
if not exist "%BACKUP_FILE%" (
    echo  [ERROR] Backup file not found: %BACKUP_FILE%
    pause
    exit /b 1
)

echo  [INFO] Restoring from: %BACKUP_FILE%
echo.

:: ============================================================
:: 1. 检查服务状态
:: ============================================================
echo  [1/6] Checking services...

:: 检查 Neo4j
netstat -ano 2>nul | findstr ":7687 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! EQU 0 (
    echo        [ERROR] Neo4j is running! Please stop it first.
    echo        Run: %NEO4J_HOME%\bin\neo4j stop
    pause
    exit /b 1
)

:: 检查 Qdrant
netstat -ano 2>nul | findstr ":6333 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! EQU 0 (
    echo        [ERROR] Qdrant is running! Please stop it first.
    echo        Stop Qdrant process before restoring.
    pause
    exit /b 1
)

echo        [OK] Services stopped

:: ============================================================
:: 2. 解压备份
:: ============================================================
echo  [2/6] Extracting backup...

set "RESTORE_TEMP=%MEMOS_ROOT%\backups\_restore_temp"
if exist "%RESTORE_TEMP%" rmdir /s /q "%RESTORE_TEMP%"
mkdir "%RESTORE_TEMP%"

powershell -Command "Expand-Archive -Path '%BACKUP_FILE%' -DestinationPath '%RESTORE_TEMP%' -Force" >nul 2>&1
if !errorlevel! NEQ 0 (
    echo        [ERROR] Failed to extract backup
    pause
    exit /b 1
)
echo        [OK] Backup extracted

:: ============================================================
:: 3. 恢复 Neo4j 数据
:: ============================================================
echo  [3/6] Restoring Neo4j...

if exist "%RESTORE_TEMP%\neo4j\data" (
    :: 备份现有数据
    if exist "%NEO4J_HOME%\data" (
        echo        Backing up existing Neo4j data...
        if exist "%NEO4J_HOME%\data_old" rmdir /s /q "%NEO4J_HOME%\data_old"
        rename "%NEO4J_HOME%\data" "data_old"
    )

    :: 恢复数据
    echo        Restoring Neo4j data...
    xcopy /E /I /H /Y "%RESTORE_TEMP%\neo4j\data" "%NEO4J_HOME%\data" >nul 2>&1
    if !errorlevel! EQU 0 (
        echo        [OK] Neo4j data restored
    ) else (
        echo        [ERROR] Neo4j restore failed
    )
) else (
    echo        [SKIP] No Neo4j data in backup
)

:: ============================================================
:: 4. 恢复 Qdrant 数据
:: ============================================================
echo  [4/6] Restoring Qdrant...

if exist "%RESTORE_TEMP%\qdrant\storage" (
    :: 备份现有数据
    if exist "%QDRANT_HOME%\storage" (
        echo        Backing up existing Qdrant data...
        if exist "%QDRANT_HOME%\storage_old" rmdir /s /q "%QDRANT_HOME%\storage_old"
        rename "%QDRANT_HOME%\storage" "storage_old"
    )

    :: 恢复数据
    echo        Restoring Qdrant storage...
    xcopy /E /I /H /Y "%RESTORE_TEMP%\qdrant\storage" "%QDRANT_HOME%\storage" >nul 2>&1
    if !errorlevel! EQU 0 (
        echo        [OK] Qdrant data restored
    ) else (
        echo        [ERROR] Qdrant restore failed
    )
) else (
    echo        [SKIP] No Qdrant data in backup
)

:: ============================================================
:: 5. 恢复配置文件
:: ============================================================
echo  [5/6] Restoring configuration...

:: .env 文件
if exist "%RESTORE_TEMP%\config\.env" (
    if exist "%MEMOS_ROOT%\.env" (
        copy /Y "%MEMOS_ROOT%\.env" "%MEMOS_ROOT%\.env.bak" >nul
    )
    copy /Y "%RESTORE_TEMP%\config\.env" "%MEMOS_ROOT%\.env" >nul
    echo        [OK] .env restored (old saved as .env.bak)
)

:: Cube 配置
if exist "%RESTORE_TEMP%\config\memos_cubes" (
    if not exist "%MEMOS_ROOT%\data" mkdir "%MEMOS_ROOT%\data"
    xcopy /E /I /H /Y "%RESTORE_TEMP%\config\memos_cubes" "%MEMOS_ROOT%\data\memos_cubes" >nul 2>&1
    echo        [OK] Cube configs restored
)

:: 用户 MCP 配置
if exist "%RESTORE_TEMP%\config\user_memos" (
    echo        [INFO] User MCP config found in backup
    echo        Location: %RESTORE_TEMP%\config\user_memos
    echo        Manually copy to %USERPROFILE%\.memos if needed
)

:: ============================================================
:: 6. 清理
:: ============================================================
echo  [6/6] Cleaning up...
rmdir /s /q "%RESTORE_TEMP%"
echo        [OK] Temporary files removed

:: ============================================================
:: 完成
:: ============================================================
echo.
echo  ============================================================
echo   Restore Complete!
echo  ============================================================
echo.
echo   Next steps:
echo     1. Review .env and update paths if needed
echo     2. Start Neo4j:  %NEO4J_HOME%\bin\neo4j console
echo     3. Start Qdrant: %QDRANT_HOME%\qdrant.exe
echo     4. Start MemOS:  scripts\local\start.bat
echo.
echo   Note: Old data backed up as *_old directories
echo.
echo  ============================================================

pause
endlocal
