# ============================================================
# MemOS Unified Venv Setup Script (PowerShell)
# Creates .venv and installs MemOS + memos-cli
# ============================================================
# Usage: powershell -ExecutionPolicy Bypass -File VENV_scripts/setup_venv.ps1
# Options:
#   -Python "py -3.11"  # Specify Python executable
#   -InstallAll         # Install all optional dependencies
#   -Clean              # Remove existing .venv first

param(
    [string]$Python = "py -3.10",
    [switch]$InstallAll,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " MemOS Venv Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot
Write-Host "[INFO] Project root: $ProjectRoot" -ForegroundColor Gray

# Clean existing venv if requested
if ($Clean -and (Test-Path ".venv")) {
    Write-Host "[1/5] Removing existing .venv..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force .venv
    Write-Host "      [OK] Old venv removed" -ForegroundColor Green
}

# Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $PyVersion = & $Python.Split()[0] @($Python.Split() | Select-Object -Skip 1) --version 2>&1
    Write-Host "      [OK] $PyVersion" -ForegroundColor Green
} catch {
    Write-Host "      [ERROR] Python not found: $Python" -ForegroundColor Red
    Write-Host "      Please install Python 3.10+ or specify -Python" -ForegroundColor Red
    exit 1
}

# Create venv if not exists
if (Test-Path ".venv\Scripts\python.exe") {
    Write-Host "[2/5] Using existing .venv" -ForegroundColor Yellow
} else {
    Write-Host "[2/5] Creating virtual environment..." -ForegroundColor Yellow
    & $Python.Split()[0] @($Python.Split() | Select-Object -Skip 1) -m venv .venv
    Write-Host "      [OK] Created .venv" -ForegroundColor Green
}

# Activate venv
Write-Host "[3/5] Activating venv..." -ForegroundColor Yellow
. .\.venv\Scripts\Activate.ps1
Write-Host "      [OK] Activated" -ForegroundColor Green

# Upgrade pip
Write-Host "[4/5] Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip -q
Write-Host "      [OK] pip upgraded" -ForegroundColor Green

# Install dependencies
Write-Host "[5/5] Installing dependencies..." -ForegroundColor Yellow
if ($InstallAll) {
    Write-Host "      Installing main project with all extras..." -ForegroundColor Gray
    pip install -e ".[all]" -q
} else {
    Write-Host "      Installing main project (core only)..." -ForegroundColor Gray
    pip install -e ".[tree-mem,mcp-server]" -q
}
Write-Host "      [OK] Main project installed" -ForegroundColor Green

Write-Host "      Installing memos-cli..." -ForegroundColor Gray
pip install -e memos-cli -q
Write-Host "      [OK] memos-cli installed" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Setup Complete!" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host " Venv location: $ProjectRoot\.venv" -ForegroundColor White
Write-Host " Python:        .venv\Scripts\python.exe" -ForegroundColor White
Write-Host ""
Write-Host " Activate later:" -ForegroundColor White
Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host " Start MemOS:" -ForegroundColor White
Write-Host "   scripts\local\start.bat" -ForegroundColor Gray
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
