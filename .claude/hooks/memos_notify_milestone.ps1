# MemOS Hook: PostToolUse - Notify Milestone (Windows PowerShell)
# Suggests saving milestones when editing important files

# Read JSON input from stdin
$jsonInput = $input | Out-String

try {
    $data = $jsonInput | ConvertFrom-Json
    $filePath = $data.tool_input.file_path
    $toolName = $data.tool_name
} catch {
    $filePath = ""
    $toolName = ""
}

# Files that indicate milestone completion
$milestoneFiles = @(
    "README.md",
    "CHANGELOG.md",
    "package.json",
    "pyproject.toml",
    "config.json"
)

# Check if edited file is a milestone indicator
$isMilestone = $false
foreach ($mf in $milestoneFiles) {
    if ($filePath -like "*$mf") {
        $isMilestone = $true
        break
    }
}

if ($isMilestone) {
    @"
{
  "continue": true,
  "suppressOutput": false,
  "message": "Consider saving this as a MILESTONE if it's a significant change"
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
