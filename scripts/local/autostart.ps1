# ============================================================
#  MemOS Auto-Start Script
#  Called by Task Scheduler at logon - starts all services silently
# ============================================================
$ErrorActionPreference = "SilentlyContinue"

# Paths
$MemOSRoot   = "G:\test\MemOS"
$neo4jHome   = "D:\User\neo4j-community-5.15.0"
$qdrantHome  = "D:\User\Qdrant"
$pythonExe   = "$MemOSRoot\.venv\Scripts\python.exe"
$logDir      = "$MemOSRoot\logs"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# ============================================================
# Helpers
# ============================================================
function Test-Port($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
}

function Show-Balloon($title, $message, $type = "Info") {
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $notify = New-Object System.Windows.Forms.NotifyIcon
        $notify.Icon = [System.Drawing.SystemIcons]::Application
        $notify.Visible = $true
        $notify.ShowBalloonTip(8000, $title, $message, $type)
        Start-Sleep -Seconds 9
        $notify.Dispose()
    } catch {}
}

# ============================================================
# Phase 1: Start Qdrant
# ============================================================
if (-not (Test-Port 6333)) {
    $qdrantExe = "$qdrantHome\qdrant.exe"
    if (Test-Path $qdrantExe) {
        Start-Process -FilePath $qdrantExe -WorkingDirectory $qdrantHome -WindowStyle Hidden
        Start-Sleep -Seconds 2
    }
}

# ============================================================
# Phase 2: Start Neo4j
# ============================================================
if (-not (Test-Port 7687)) {
    $neo4jBat = "$neo4jHome\bin\neo4j.bat"
    if (Test-Path $neo4jBat) {
        Start-Process -FilePath "cmd.exe" `
            -ArgumentList "/c cd /d `"$neo4jHome\bin`" && neo4j.bat console" `
            -WindowStyle Hidden
        Start-Sleep -Seconds 12
    }
}

# ============================================================
# Phase 3: Start MemOS API (hidden, log to file)
# ============================================================
if (-not (Test-Port 18000)) {
    # Keep last 3 log files
    Get-Item "$logDir\api_stdout_*.log" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -Skip 3 |
        Remove-Item -Force -ErrorAction SilentlyContinue

    $ts = Get-Date -Format "yyyyMMdd_HHmmss"

    $apiProc = Start-Process `
        -FilePath $pythonExe `
        -ArgumentList "-m", "uvicorn", "oh_memos.api.start_api:app", "--host", "0.0.0.0", "--port", "18000" `
        -WorkingDirectory "$MemOSRoot\src" `
        -WindowStyle Hidden `
        -RedirectStandardOutput "$logDir\api_stdout_$ts.log" `
        -RedirectStandardError  "$logDir\api_stderr_$ts.log" `
        -PassThru

    if ($apiProc) {
        $apiProc.Id | Out-File "$logDir\api.pid" -Force
    }
}

# ============================================================
# Phase 4: Wait for API to be healthy (max 40s)
# ============================================================
$waited  = 0
$healthy = $false
while ($waited -lt 40) {
    Start-Sleep -Seconds 3
    $waited += 3
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:18000/health" -TimeoutSec 3 -UseBasicParsing
        if ($resp.StatusCode -eq 200) { $healthy = $true; break }
    } catch {}
}

# ============================================================
# Phase 5: Balloon notification with result
# ============================================================
$qdrantOk = Test-Port 6333
$neo4jOk  = Test-Port 7687
$apiOk    = Test-Port 18000

$lines = @(
    "$(if($qdrantOk){'[OK]'}else{'[!!]'}) Qdrant  :6333",
    "$(if($neo4jOk) {'[OK]'}else{'[!!]'}) Neo4j   :7687",
    "$(if($apiOk)   {'[OK]'}else{'[!!]'}) API     :18000"
)
$body = $lines -join "`n"

if ($healthy) {
    Show-Balloon "MemOS Started" $body "Info"
} else {
    $body += "`n`nCheck logs: $logDir"
    Show-Balloon "MemOS - Startup Warning" $body "Warning"
}
