#!/bin/bash
# MCP Server wrapper script for WSL environment
# This script ensures the MCP server runs correctly

# NOTE: Claude Code env vars may not pass through to WSL bash correctly
# Hardcode MEMOS_ENABLE_DELETE=true if you want delete functionality
# Or set it in the environment before starting Claude Code

# Set environment variables (with defaults)
MEMOS_URL="${MEMOS_URL:-http://localhost:18000}"
MEMOS_USER="${MEMOS_USER:-dev_user}"
MEMOS_DEFAULT_CUBE="${MEMOS_DEFAULT_CUBE:-dev_cube}"
MEMOS_CUBES_DIR="${MEMOS_CUBES_DIR:-G:/test/MemOS/data/memos_cubes}"
# Enable delete by default in this dev environment
MEMOS_ENABLE_DELETE="${MEMOS_ENABLE_DELETE:-true}"
MEMOS_TIMEOUT_TOOL="${MEMOS_TIMEOUT_TOOL:-120.0}"
MEMOS_TIMEOUT_STARTUP="${MEMOS_TIMEOUT_STARTUP:-30.0}"
MEMOS_TIMEOUT_HEALTH="${MEMOS_TIMEOUT_HEALTH:-5.0}"
MEMOS_API_WAIT_MAX="${MEMOS_API_WAIT_MAX:-60.0}"

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
