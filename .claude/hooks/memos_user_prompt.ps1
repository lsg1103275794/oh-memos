# MemOS Hook: UserPromptSubmit (Windows PowerShell)
# Triggered when user submits a prompt

# Read input from stdin
$input = $input | Out-String

# Return success JSON
@"
{
  "continue": true,
  "suppressOutput": true
}
"@

exit 0
