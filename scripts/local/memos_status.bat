@echo off
:: MemOS Status Check - pin to taskbar or desktop shortcut
:: Shows all service ports + API health + recent error log

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"Add-Type -AssemblyName System.Windows.Forms; ^
$ports = [ordered]@{6333='Qdrant';7687='Neo4j';18000='API';11434='Ollama'}; ^
$lines = @(); ^
foreach ($kv in $ports.GetEnumerator()) { ^
    $ok = (Get-NetTCPConnection -LocalPort $kv.Key -State Listen -EA SilentlyContinue) -ne $null; ^
    $lines += (if($ok){'[OK] '}else{'[--] '}) + $kv.Value + ' (:' + $kv.Key + ')' ^
}; ^
try { ^
    $h = Invoke-RestMethod 'http://localhost:18000/health' -TimeoutSec 3; ^
    $lines += ''; $lines += 'API Health: ' + $h.data.status ^
} catch { ^
    $lines += ''; $lines += 'API Health: unreachable' ^
}; ^
$logDir = 'G:\test\MemOS\logs'; ^
$latest = Get-Item ""$logDir\api_stderr_*.log"" -EA SilentlyContinue ^
    | Sort-Object LastWriteTime -Descending | Select-Object -First 1; ^
if ($latest) { ^
    $tail = Get-Content $latest.FullName -Tail 5 -EA SilentlyContinue; ^
    if ($tail) { $lines += ''; $lines += '--- Recent log ---'; $lines += $tail } ^
}; ^
[System.Windows.Forms.MessageBox]::Show( ^
    ($lines -join ""`n""), 'MemOS Status', ^
    [System.Windows.Forms.MessageBoxButtons]::OK, ^
    [System.Windows.Forms.MessageBoxIcon]::Information ^
) | Out-Null"
