@echo off
:: MemOS 快速状态检查 — 固定到任务栏或桌面，随时双击查看
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"Add-Type -AssemblyName System.Windows.Forms; ^
$ports = [ordered]@{6333='Qdrant';7687='Neo4j';18000='API';11434='Ollama'}; ^
$lines = @(); ^
foreach ($kv in $ports.GetEnumerator()) { ^
    $ok = (Get-NetTCPConnection -LocalPort $kv.Key -State Listen -EA SilentlyContinue) -ne $null; ^
    $lines += (if($ok){'OK'}else{'--'}) + '  ' + $kv.Value + ' (:' + $kv.Key + ')' ^
}; ^
try { ^
    $h = Invoke-RestMethod 'http://localhost:18000/health' -TimeoutSec 3; ^
    $lines += ''; ^
    $lines += 'API Health: ' + $h.data.status ^
} catch { ^
    $lines += ''; ^
    $lines += 'API Health: unreachable' ^
}; ^
$logDir = 'G:\test\MemOS\logs'; ^
if (Test-Path $logDir) { ^
    $latest = Get-Item \"$logDir\api_stderr_*.log\" -EA SilentlyContinue ^
        | Sort-Object LastWriteTime -Descending ^
        | Select-Object -First 1; ^
    if ($latest) { ^
        $tail = Get-Content $latest.FullName -Tail 5 -EA SilentlyContinue; ^
        if ($tail) { $lines += ''; $lines += '--- 最近日志 ---'; $lines += $tail } ^
    } ^
}; ^
[System.Windows.Forms.MessageBox]::Show( ^
    ($lines -join \"`n\"), ^
    'MemOS Status', ^
    [System.Windows.Forms.MessageBoxButtons]::OK, ^
    [System.Windows.Forms.MessageBoxIcon]::Information ^
) | Out-Null"
