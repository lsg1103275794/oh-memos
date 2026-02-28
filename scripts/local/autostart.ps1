# ============================================================
#  MemOS 开机自动启动脚本
#  Task Scheduler 调用此脚本，静默启动所有服务并通知结果
# ============================================================
$ErrorActionPreference = "SilentlyContinue"

# 路径配置
$memosRoot   = "G:\test\MemOS"
$neo4jHome   = "D:\User\neo4j-community-5.15.0"
$qdrantHome  = "D:\User\Qdrant"
$pythonExe   = "$memosRoot\.venv\Scripts\python.exe"
$logDir      = "$memosRoot\logs"
$pidFile     = "$logDir\api.pid"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# ============================================================
# 工具函数
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
# Phase 1：启动 Qdrant
# ============================================================
if (-not (Test-Port 6333)) {
    $qdrantExe = "$qdrantHome\qdrant.exe"
    if (Test-Path $qdrantExe) {
        Start-Process -FilePath $qdrantExe -WorkingDirectory $qdrantHome -WindowStyle Hidden
        Start-Sleep -Seconds 2
    }
}

# ============================================================
# Phase 2：启动 Neo4j
# ============================================================
if (-not (Test-Port 7687)) {
    $neo4jBat = "$neo4jHome\bin\neo4j.bat"
    if (Test-Path $neo4jBat) {
        Start-Process -FilePath "cmd.exe" `
            -ArgumentList "/c cd /d `"$neo4jHome\bin`" && neo4j.bat console" `
            -WindowStyle Hidden
        # Neo4j 启动较慢，多等一会儿
        Start-Sleep -Seconds 12
    }
}

# ============================================================
# Phase 3：启动 MemOS API（隐藏窗口，日志写文件）
# ============================================================
if (-not (Test-Port 18000)) {
    # 清理旧日志（保留最近 3 次）
    Get-Item "$logDir\api_stdout_*.log" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -Skip 3 |
        Remove-Item -Force -ErrorAction SilentlyContinue

    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    $stdoutLog = "$logDir\api_stdout_$ts.log"
    $stderrLog = "$logDir\api_stderr_$ts.log"

    $apiProc = Start-Process `
        -FilePath $pythonExe `
        -ArgumentList "-m", "uvicorn", "memos.api.start_api:app", "--host", "0.0.0.0", "--port", "18000" `
        -WorkingDirectory "$memosRoot\src" `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError  $stderrLog `
        -PassThru

    if ($apiProc) {
        $apiProc.Id | Out-File $pidFile -Force
    }
}

# ============================================================
# Phase 4：等待 API 就绪，最多 40 秒
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
# Phase 5：气泡通知启动结果
# ============================================================
$qdrantOk = Test-Port 6333
$neo4jOk  = Test-Port 7687
$apiOk    = Test-Port 18000

$lines = @(
    "$(if($qdrantOk){'[OK]'}else{'[!]'}) Qdrant  :6333",
    "$(if($neo4jOk) {'[OK]'}else{'[!]'}) Neo4j   :7687",
    "$(if($apiOk)   {'[OK]'}else{'[!]'}) API     :18000"
)
$body = $lines -join "`n"

if ($healthy) {
    Show-Balloon "MemOS 已启动" $body "Info"
} else {
    $body += "`n`n日志: $logDir"
    Show-Balloon "MemOS 启动异常" $body "Warning"
}
