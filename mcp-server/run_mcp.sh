#!/bin/bash
# MCP Server wrapper script for WSL environment
# This script ensures the MCP server runs correctly
#
# NOTE: Claude Code env vars may NOT pass through to WSL bash.
# We load .env from project root as the source of truth.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

# Load .env as defaults (won't override already-set env vars)
if [ -f "$ENV_FILE" ]; then
    while IFS= read -r line; do
        # Skip comments and blank lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        # Extract key=value (strip inline comments)
        key="${line%%=*}"
        val="${line#*=}"
        val="${val%%#*}"      # strip inline comment
        val="${val%"${val##*[! ]}"}"  # rtrim
        # Only set if not already in environment
        if [ -n "$key" ] && [ -z "${!key+x}" ]; then
            export "$key=$val"
        fi
    done < "$ENV_FILE"
fi

# Apply defaults for any still-missing vars
MEMOS_URL="${MEMOS_URL:-${MEMOS_BASE_URL:-http://localhost:18000}}"
MEMOS_USER="${MEMOS_USER:-dev_user}"
MEMOS_DEFAULT_CUBE="${MEMOS_DEFAULT_CUBE:-dev_cube}"
MEMOS_CUBES_DIR="${MEMOS_CUBES_DIR:-G:/test/oh-memos/data/oh-memos_cubes}"
MEMOS_ENABLE_DELETE="${MEMOS_ENABLE_DELETE:-true}"
MEMOS_TIMEOUT_TOOL="${MEMOS_TIMEOUT_TOOL:-120.0}"
MEMOS_TIMEOUT_STARTUP="${MEMOS_TIMEOUT_STARTUP:-30.0}"
MEMOS_TIMEOUT_HEALTH="${MEMOS_TIMEOUT_HEALTH:-5.0}"
MEMOS_API_WAIT_MAX="${MEMOS_API_WAIT_MAX:-60.0}"

# Use Windows Python from venv (preferred) or conda_venv fallback
if [ -f "/mnt/g/test/oh-memos/.venv/Scripts/python.exe" ]; then
    PYTHON="/mnt/g/test/oh-memos/.venv/Scripts/python.exe"
else
    PYTHON="/mnt/g/test/oh-memos/conda_venv/python.exe"
fi

# Windows Python needs Windows-style path
SCRIPT="G:/test/oh-memos/mcp-server/oh_memos_mcp_server.py"

# Pass config as CLI args (WSL env vars don't pass through to Windows Python)
exec "$PYTHON" "$SCRIPT" \
    --memos-url "$MEMOS_URL" \
    --memos-user "$MEMOS_USER" \
    --memos-default-cube "$MEMOS_DEFAULT_CUBE" \
    --memos-cubes-dir "$MEMOS_CUBES_DIR" \
    --memos-enable-delete "$MEMOS_ENABLE_DELETE" \
    --memos-timeout-tool "$MEMOS_TIMEOUT_TOOL" \
    --memos-timeout-startup "$MEMOS_TIMEOUT_STARTUP" \
    --memos-timeout-health "$MEMOS_TIMEOUT_HEALTH" \
    --memos-api-wait-max "$MEMOS_API_WAIT_MAX" \
    "$@"
