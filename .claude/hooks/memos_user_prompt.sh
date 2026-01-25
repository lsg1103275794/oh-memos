#!/bin/bash
# MemOS Hook: UserPromptSubmit
# Triggered when user submits a prompt
# Returns success message to show MCP is active

# Read input from stdin
input=$(cat)

# Extract user prompt (if available)
user_message=$(echo "$input" | jq -r '.user_message // empty' 2>/dev/null)

# Just return success - let MCP handle the actual memory operations
# This hook serves as a reminder that memory system is active
cat <<EOF
{
  "continue": true,
  "suppressOutput": false
}
EOF

exit 0
