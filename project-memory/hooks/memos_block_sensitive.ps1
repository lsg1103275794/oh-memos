# MemOS Hook: PreToolUse - Block Sensitive Files (Windows PowerShell)
# Warns when editing sensitive files like .env, credentials, etc.

# Read JSON input from stdin
$jsonInput = $input | Out-String

try {
    $data = $jsonInput | ConvertFrom-Json
    $filePath = $data.tool_input.file_path
} catch {
    $filePath = ""
}

# Sensitive patterns
$sensitivePatterns = @(
    ".env",
    "credentials",
    "secrets",
    "password",
    ".pem",
    ".key",
    "id_rsa"
)

# Check if file matches sensitive pattern
$isSensitive = $false
foreach ($pattern in $sensitivePatterns) {
    if ($filePath -like "*$pattern*") {
        $isSensitive = $true
        break
    }
}

if ($isSensitive) {
    @"
{
  "continue": true,
  "suppressOutput": false,
  "message": "Warning: Editing sensitive file: $filePath"
}
"@
} else {
    @"
{
  "continue": true,
  "suppressOutput": true
}
"@
}

exit 0
