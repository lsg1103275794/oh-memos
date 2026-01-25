#!/bin/bash
# MemOS Hook: PostToolUse (Write/Edit)
# Detect potential milestones based on file changes

# Read input from stdin
input=$(cat)

# Extract file path
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
tool_name=$(echo "$input" | jq -r '.tool_name // empty' 2>/dev/null)

# Files that might indicate milestone completion
milestone_files=(
    "README.md"
    "CHANGELOG.md"
    "package.json"
    "pyproject.toml"
    "config.json"
)

# Check if edited file is a milestone indicator
for mf in "${milestone_files[@]}"; do
    if [[ "$file_path" == *"$mf" ]]; then
        cat <<EOF
{
  "continue": true,
  "suppressOutput": false,
  "message": "💡 Consider saving this as a MILESTONE if it's a significant change"
}
EOF
        exit 0
    fi
done

# Silent continue
cat <<EOF
{
  "continue": true,
  "suppressOutput": true
}
EOF

exit 0
