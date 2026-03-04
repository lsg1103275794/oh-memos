# ============================================================
# MemOS Silent Launcher Template (PowerShell)
#
# INSTRUCTIONS:
# 1. Copy this file to scripts/local/start_silent.ps1
# 2. Edit the paths in $config below
# 3. Run with: powershell -ExecutionPolicy Bypass -File start_silent.ps1
# ============================================================

$ErrorActionPreference = "SilentlyContinue"

# ============================================================
# CONFIGURATION - EDIT THESE PATHS
# ============================================================
$config = @{
    Neo4jHome  = "D:\User\neo4j-community-5.15.0"    # Your Neo4j path
    QdrantHome = "D:\User\Qdrant"                     # Your Qdrant path
    MemOSRoot  = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
}
# ============================================================

function Test-PortInUse {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $connection
}

Write-Host "`n[MemOS] Starting database services...`n" -ForegroundColor Cyan

# Start Qdrant
if (-not (Test-PortInUse -Port 6333)) {
    $qdrantExe = Join-Path $config.QdrantHome "qdrant.exe"
    if (Test-Path $qdrantExe) {
        Start-Process -FilePath $qdrantExe -WorkingDirectory $config.QdrantHome -WindowStyle Hidden
        Write-Host "  [OK] Qdrant started" -ForegroundColor Green
    }
} else {
    Write-Host "  [OK] Qdrant already running" -ForegroundColor Yellow
}

# Start Neo4j
if (-not (Test-PortInUse -Port 7687)) {
    $neo4jBat = Join-Path $config.Neo4jHome "bin\neo4j.bat"
    if (Test-Path $neo4jBat) {
        Start-Process -FilePath "cmd.exe" `
            -ArgumentList "/c cd /d `"$($config.Neo4jHome)\bin`" && neo4j.bat console" `
            -WindowStyle Hidden
        Write-Host "  [OK] Neo4j started" -ForegroundColor Green
    }
} else {
    Write-Host "  [OK] Neo4j already running" -ForegroundColor Yellow
}

Write-Host "`n[MemOS] Services ready`n" -ForegroundColor Cyan
Write-Host "  Qdrant: http://localhost:6333/dashboard"
Write-Host "  Neo4j:  http://localhost:7474`n"

Start-Sleep -Seconds 3
