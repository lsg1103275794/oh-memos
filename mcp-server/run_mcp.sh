#!/bin/bash
# MCP Server wrapper script for WSL environment
# This script ensures the MCP server runs correctly

# NOTE: Claude Code env vars may not pass through to WSL bash correctly

# Set environment variables (with .env)
MEMOS_URL="${MEMOS_URL:-${MEMOS_BASE_URL:?MEMOS_URL or MEMOS_BASE_URL required}}"
MEMOS_USER="${MEMOS_USER:?MEMOS_USER required}"
MEMOS_DEFAULT_CUBE="${MEMOS_DEFAULT_CUBE:?MEMOS_DEFAULT_CUBE required}"
MEMOS_CUBES_DIR="${MEMOS_CUBES_DIR:?MEMOS_CUBES_DIR required}"
MEMOS_ENABLE_DELETE="${MEMOS_ENABLE_DELETE:?MEMOS_ENABLE_DELETE required}"
MEMOS_TIMEOUT_TOOL="${MEMOS_TIMEOUT_TOOL:?MEMOS_TIMEOUT_TOOL required}"
MEMOS_TIMEOUT_STARTUP="${MEMOS_TIMEOUT_STARTUP:?MEMOS_TIMEOUT_STARTUP required}"
MEMOS_TIMEOUT_HEALTH="${MEMOS_TIMEOUT_HEALTH:?MEMOS_TIMEOUT_HEALTH required}"
MEMOS_API_WAIT_MAX="${MEMOS_API_WAIT_MAX:?MEMOS_API_WAIT_MAX required}"

# Use Windows paths for Windows Python
PYTHON="/mnt/g/test/MemOS/conda_venv/python.exe"
# Windows Python needs Windows-style path
SCRIPT="G:/test/MemOS/mcp-server/memos_mcp_server.py"

# Pass env vars as command line args (WSL env vars don't pass to Windows Python)
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
