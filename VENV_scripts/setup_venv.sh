#!/usr/bin/env bash
# ============================================================
# MemOS Unified Venv Setup Script (Linux/macOS)
# Creates .venv and installs MemOS + memos-cli
# ============================================================
# Usage: bash VENV_scripts/setup_venv.sh
# Optional: PYTHON_BIN=python3.11 bash VENV_scripts/setup_venv.sh
# Optional: INSTALL_ALL=true bash VENV_scripts/setup_venv.sh
# Optional: CLEAN=true bash VENV_scripts/setup_venv.sh

set -euo pipefail

echo ""
echo "============================================================"
echo " MemOS Venv Setup"
echo "============================================================"
echo ""

# Configuration
PYTHON_BIN=${PYTHON_BIN:-"python3"}
INSTALL_ALL=${INSTALL_ALL:-"false"}
CLEAN=${CLEAN:-"false"}

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"
echo "[INFO] Project root: $PROJECT_ROOT"

# Clean existing venv if requested
if [ "$CLEAN" = "true" ] && [ -d ".venv" ]; then
    echo "[1/5] Removing existing .venv..."
    rm -rf .venv
    echo "      [OK] Old venv removed"
fi

# Check Python
echo "[1/5] Checking Python..."
if ! command -v "$PYTHON_BIN" &> /dev/null; then
    echo "      [ERROR] Python not found: $PYTHON_BIN"
    echo "      Please install Python 3.10+ or set PYTHON_BIN"
    exit 1
fi
PYVER=$("$PYTHON_BIN" --version 2>&1 | awk '{print $2}')
echo "      [OK] Python $PYVER"

# Create venv if not exists
if [ -f ".venv/bin/python" ]; then
    echo "[2/5] Using existing .venv"
else
    echo "[2/5] Creating virtual environment..."
    "$PYTHON_BIN" -m venv .venv
    echo "      [OK] Created .venv"
fi

# Activate venv
echo "[3/5] Activating venv..."
source .venv/bin/activate
echo "      [OK] Activated"

# Upgrade pip
echo "[4/5] Upgrading pip..."
python -m pip install --upgrade pip -q
echo "      [OK] pip upgraded"

# Install dependencies
echo "[5/5] Installing dependencies..."
if [ "$INSTALL_ALL" = "true" ]; then
    echo "      Installing main project with all extras..."
    pip install -e ".[all]" -q
else
    echo "      Installing main project (core only)..."
    pip install -e ".[tree-mem,mcp-server]" -q
fi
echo "      [OK] Main project installed"

echo "      Installing memos-cli..."
pip install -e memos-cli -q
echo "      [OK] memos-cli installed"

# Summary
echo ""
echo "============================================================"
echo " Setup Complete!"
echo "============================================================"
echo ""
echo " Venv location: $PROJECT_ROOT/.venv"
echo " Python:        .venv/bin/python"
echo ""
echo " Activate later:"
echo "   source .venv/bin/activate"
echo ""
echo " Start MemOS:"
echo "   python -m uvicorn memos.api.start_api:app --port 18000"
echo ""
echo "============================================================"
