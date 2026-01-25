#!/bin/bash
# MemOS Hook: PreToolUse (Edit/Write)
# Block edits to sensitive files without confirmation

# Read input from stdin
input=$(cat)

# Extract file path
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# List of sensitive patterns
sensitive_patterns=(
    ".env"
    "credentials"
    "secrets"
    "password"
    ".pem"
    ".key"
    "id_rsa"
)

# Check if file matches any sensitive pattern
for pattern in "${sensitive_patterns[@]}"; do
    if [[ "$file_path" == *"$pattern"* ]]; then
        # Output warning but don't block (exit 0 with message)
        cat <<EOF
{
  "continue": true,
  "suppressOutput": false,
  "message": "⚠️ Warning: Editing sensitive file: $file_path"
}
EOF
        exit 0
    fi
done

# Allow the operation
cat <<EOF
{
  "continue": true,
  "suppressOutput": true
}
EOF

exit 0
