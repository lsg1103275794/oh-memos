# MemOS Hook: PostToolUse - Log Commands (Windows PowerShell)
# Logs executed bash commands for potential memory saving

# Read JSON input from stdin
$jsonInput = $input | Out-String

try {
    $data = $jsonInput | ConvertFrom-Json
    $command = $data.tool_input.command
    $toolName = $data.tool_name
} catch {
    $command = ""
    $toolName = ""
}

# Only log Bash commands
if ($toolName -eq "Bash" -and $command) {
    $logFile = Join-Path $env:CLAUDE_PROJECT_DIR ".claude\hooks\command_history.log"
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] $command"

    try {
        Add-Content -Path $logFile -Value $logEntry -ErrorAction SilentlyContinue
    } catch {
        # Silently ignore logging errors
    }
}

# Continue without output
@"
{
  "continue": true,
  "suppressOutput": true
}
"@

exit 0
