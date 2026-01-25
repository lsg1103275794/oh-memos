#!/bin/bash
# MemOS Hook: PostToolUse (Bash)
# Log executed commands for potential memory saving

# Read input from stdin
input=$(cat)

# Extract command and result
command=$(echo "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)
tool_name=$(echo "$input" | jq -r '.tool_name // empty' 2>/dev/null)

# Only log Bash commands
if [[ "$tool_name" == "Bash" && -n "$command" ]]; then
    # Log to file with timestamp
    log_file="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/command_history.log"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $command" >> "$log_file" 2>/dev/null
fi

# Continue without output
cat <<EOF
{
  "continue": true,
  "suppressOutput": true
}
EOF

exit 0
