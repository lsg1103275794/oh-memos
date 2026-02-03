#!/bin/bash
# MemOS Hook: PreToolUse - Smart Sensitive File Guard
# Enhanced detection with tiered warnings

# Read input from stdin
input=$(cat)

# Extract file_path using jq if available, otherwise basic parsing
if command -v jq &> /dev/null; then
    file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""' 2>/dev/null)
else
    file_path=$(echo "$input" | grep -oP '"file_path"\s*:\s*"\K[^"]*' 2>/dev/null)
fi

file_path_lower=$(echo "$file_path" | tr '[:upper:]' '[:lower:]')

message=""
continue_op="true"

# === CRITICAL: Should never edit ===
critical_patterns=(
    "id_rsa" "id_ed25519" ".pem" ".p12" ".pfx"
    "aws_credentials" "gcloud/credentials"
    ".npmrc" ".pypirc" "keystore" "vault.json" "serviceaccount"
)

for pattern in "${critical_patterns[@]}"; do
    if [[ "$file_path_lower" == *"$pattern"* ]]; then
        message="🚨 CRITICAL: Editing sensitive file!\n   File: $file_path\n   → NEVER commit this file to git!"
        break
    fi
done

# === HIGH: Secrets and credentials ===
if [ -z "$message" ]; then
    high_patterns=(".env" "credentials" "secrets" "password" "api_key" "auth.json" "private" ".htpasswd")
    for pattern in "${high_patterns[@]}"; do
        if [[ "$file_path_lower" == *"$pattern"* ]]; then
            message="⚠️ Warning: Editing sensitive file\n   File: $file_path\n   → Consider: memos_save(..., memory_type=\"CONFIG\") after changes"
            break
        fi
    done
fi

# === MEDIUM: Config files ===
if [ -z "$message" ]; then
    config_patterns=("config.json" "config.yaml" "config.yml" "settings.json" "docker-compose" "dockerfile" "nginx.conf")
    for pattern in "${config_patterns[@]}"; do
        if [[ "$file_path_lower" == *"$pattern"* ]] && [[ "$file_path_lower" != *".claude/settings.json"* ]]; then
            message="⚙️ Config file edit → Remember to save important changes with memos_save(..., memory_type=\"CONFIG\")"
            break
        fi
    done
fi

# === LOW: Auto-generated files ===
if [ -z "$message" ]; then
    generated_patterns=("package-lock.json" "yarn.lock" "pnpm-lock.yaml" "poetry.lock" ".min.js" ".min.css" "dist/" "build/")
    for pattern in "${generated_patterns[@]}"; do
        if [[ "$file_path_lower" == *"$pattern"* ]]; then
            message="📦 Note: This appears to be an auto-generated file. Manual edits may be overwritten."
            break
        fi
    done
fi

# Output result
if [ -n "$message" ]; then
    echo "{\"continue\":$continue_op,\"suppressOutput\":false,\"message\":\"$message\"}"
else
    echo '{"continue":true,"suppressOutput":true}'
fi
