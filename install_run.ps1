# oh_memos Windows PowerShell Launcher

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $ScriptDir

$PythonExe = Join-Path $ScriptDir "conda_venv\python.exe"
$PipExe = Join-Path $ScriptDir "conda_venv\Scripts\pip.exe"

$env:PATH = "$ScriptDir\conda_venv;$ScriptDir\conda_venv\Scripts;$ScriptDir\conda_venv\Library\bin;$env:PATH"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   oh_memos Windows Install and Run" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Python not found: $PythonExe" -ForegroundColor Red
    Write-Host "        Make sure conda_venv folder exists" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[1/5] Checking Python..." -ForegroundColor Green
& $PythonExe --version
Write-Host "       Python OK" -ForegroundColor Gray

# Create directories
Write-Host ""
Write-Host "[2/5] Creating directories..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path "data\oh_memos_cubes" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null
Write-Host "       Directories OK" -ForegroundColor Gray

# Install dependencies
Write-Host ""
Write-Host "[3/5] Installing dependencies..." -ForegroundColor Green
& $PipExe install -q -r docker/requirements.txt 2>$null
& $PipExe install -q "chonkie>=1.0.7" "markitdown[docx,pdf,pptx,xls,xlsx]" "langchain-text-splitters" 2>$null
Write-Host "       Dependencies OK" -ForegroundColor Gray

# Config
Write-Host ""
Write-Host "[4/5] Checking config..." -ForegroundColor Green
if (-not (Test-Path ".env")) {
    Copy-Item ".env.windows.example" ".env" -Force
    Write-Host "       Created .env file" -ForegroundColor Yellow
} else {
    Write-Host "       .env exists, skipping" -ForegroundColor Gray
}

# Start service
Write-Host ""
Write-Host "[5/5] Starting oh_memos service..." -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Server: http://localhost:18000" -ForegroundColor Cyan
Write-Host "   API Docs: http://localhost:18000/docs" -ForegroundColor Cyan
Write-Host "   Press Ctrl+C to stop" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

try {
    $env:PYTHONPATH = Join-Path $ScriptDir "src"
    & $PythonExe -m uvicorn oh_memos.api.start_api:app --host 0.0.0.0 --port 18000 --reload
} catch {
    Write-Host "[ERROR] Failed to start: $_" -ForegroundColor Red
} finally {
    Write-Host ""
    Write-Host "Service stopped" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
}
