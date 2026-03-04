#!/bin/bash
# MemOS Hook: PostToolUse - Smart Auto-Save Suggestions
# Analyzes tool results and suggests appropriate memory types

# Read input from stdin
input=$(cat)

# Extract fields using jq if available, otherwise basic parsing
if command -v jq &> /dev/null; then
    tool_name=$(echo "$input" | jq -r '.tool_name // ""' 2>/dev/null)
    file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""' 2>/dev/null)
    command=$(echo "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)
    result=$(echo "$input" | jq -r '.tool_result // ""' 2>/dev/null)
else
    tool_name=$(echo "$input" | grep -oP '"tool_name"\s*:\s*"\K[^"]*' 2>/dev/null)
    file_path=$(echo "$input" | grep -oP '"file_path"\s*:\s*"\K[^"]*' 2>/dev/null)
    command=$(echo "$input" | grep -oP '"command"\s*:\s*"\K[^"]*' 2>/dev/null)
    result=$(echo "$input" | grep -oP '"tool_result"\s*:\s*"\K[^"]*' 2>/dev/null)
fi

file_path_lower=$(echo "$file_path" | tr '[:upper:]' '[:lower:]')
result_lower=$(echo "$result" | tr '[:upper:]' '[:lower:]')
cmd_lower=$(echo "$command" | tr '[:upper:]' '[:lower:]')

suggestion=""

# === Handle Edit/Write operations ===
if [[ "$tool_name" == "Edit" || "$tool_name" == "Write" ]]; then
    # Config files → CONFIG
    config_patterns=(".env" "config.json" "config.yaml" "config.yml" "settings.json" "tsconfig.json" "docker-compose" "dockerfile")
    for pattern in "${config_patterns[@]}"; do
        if [[ "$file_path_lower" == *"$pattern"* ]]; then
            suggestion="⚙️ Config file modified → Consider: oh-memos_save(..., memory_type=\"CONFIG\")"
            break
        fi
    done

    # Milestone files → MILESTONE
    if [ -z "$suggestion" ]; then
        milestone_files=("readme.md" "changelog.md" "package.json" "pyproject.toml" "cargo.toml" "go.mod")
        for pattern in "${milestone_files[@]}"; do
            if [[ "$file_path_lower" == *"$pattern" ]]; then
                suggestion="📌 Project file updated → Consider: oh-memos_save(..., memory_type=\"MILESTONE\")"
                break
            fi
        done
    fi

    # Test files → might be BUGFIX
    if [ -z "$suggestion" ]; then
        if [[ "$file_path_lower" == *"test"* || "$file_path_lower" == *"spec"* ]]; then
            suggestion="🧪 Test file modified → If fixing a bug: oh-memos_save(..., memory_type=\"BUGFIX\")"
        fi
    fi
fi

# === Handle Bash commands ===
if [[ "$tool_name" == "Bash" ]]; then
    # Detect failures
    if echo "$result_lower" | grep -qiE "error:|failed|exception|traceback|fatal:|command not found|permission denied"; then
        suggestion="❌ Command failed → Consider: oh-memos_search(query=\"ERROR_PATTERN <error>\") for solutions"
    fi

    # Detect successful fixes
    if [ -z "$suggestion" ]; then
        if echo "$cmd_lower" | grep -qiE "git commit" && echo "$result_lower" | grep -qiE "fix|bug|resolve"; then
            suggestion="✅ Fix committed → Consider: oh-memos_save(..., memory_type=\"BUGFIX\")"
        fi
    fi

    # Detect successful tests
    if [ -z "$suggestion" ]; then
        if echo "$cmd_lower" | grep -qiE "pytest|npm test|cargo test|go test"; then
            if echo "$result_lower" | grep -qiE "passed|ok|success"; then
                suggestion="✅ Tests passed → If this fixed something: oh-memos_save(..., memory_type=\"BUGFIX\")"
            fi
        fi
    fi

    # Package install
    if [ -z "$suggestion" ]; then
        if echo "$cmd_lower" | grep -qiE "pip install|npm install|cargo add"; then
            if ! echo "$result_lower" | grep -qiE "error:|failed"; then
                suggestion="📦 Dependencies changed → Consider: oh-memos_save(..., memory_type=\"CONFIG\")"
            fi
        fi
    fi
fi

# Output result
if [ -n "$suggestion" ]; then
    echo "{\"continue\":true,\"suppressOutput\":false,\"message\":\"$suggestion\"}"
else
    echo '{"continue":true,"suppressOutput":true}'
fi
