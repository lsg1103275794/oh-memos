#!/bin/bash
# MCP Server wrapper script for WSL environment
# This script ensures the MCP server runs correctly

# Set environment variables
export MEMOS_URL="${MEMOS_URL:-http://localhost:18000}"
export MEMOS_USER="${MEMOS_USER:-dev_user}"
export MEMOS_DEFAULT_CUBE="${MEMOS_DEFAULT_CUBE:-dev_cube}"
export MEMOS_CUBES_DIR="${MEMOS_CUBES_DIR:-G:/test/MemOS/data/memos_cubes}"

# Use Windows paths for Windows Python
PYTHON="/mnt/g/test/MemOS/conda_venv/python.exe"
# Windows Python needs Windows-style path
SCRIPT="G:/test/MemOS/mcp-server/memos_mcp_server.py"

exec "$PYTHON" "$SCRIPT" "$@"
