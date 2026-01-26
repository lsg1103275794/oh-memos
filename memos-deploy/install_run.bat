@echo off

cd /d "%~dp0"

set PYTHON_EXE=%~dp0conda_venv\python.exe
set PIP_EXE=%~dp0conda_venv\Scripts\pip.exe
set PATH=%~dp0conda_venv;%~dp0conda_venv\Scripts;%~dp0conda_venv\Library\bin;%PATH%

echo ========================================
echo    MemOS Windows Install and Run
echo ========================================
echo.

echo [1/5] Checking Python...
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found: %PYTHON_EXE%
    echo         Make sure conda_venv folder exists
    pause
    exit /b 1
)
"%PYTHON_EXE%" --version
echo       Python OK

echo.
echo [2/5] Creating directories...
if not exist data mkdir data
if not exist data\memos_cubes mkdir data\memos_cubes
if not exist logs mkdir logs
echo       Directories OK

echo.
echo [3/5] Installing dependencies...
"%PIP_EXE%" install -q -r docker/requirements.txt -i https://pypi.org/simple
if errorlevel 1 (
    echo [WARN] Some dependencies may have issues
)
"%PIP_EXE%" install -q "chonkie>=1.0.7" "markitdown[docx,pdf,pptx,xls,xlsx]" "langchain-text-splitters" -i https://pypi.org/simple 2>nul
echo       Dependencies OK

echo.
echo [4/5] Checking config...
if not exist .env (
    copy .env.windows.example .env >nul
    echo [INFO] Created .env file
) else (
    echo       .env exists, skipping
)

echo.
echo [5/5] Starting MemOS service...
echo.
echo ========================================
echo    Server: http://localhost:18000
echo    API Docs: http://localhost:18000/docs
echo    Press Ctrl+C to stop
echo ========================================
echo.

set PYTHONPATH=%~dp0src
"%PYTHON_EXE%" -m uvicorn memos.api.start_api:app --host 0.0.0.0 --port 18000 --reload

pause
