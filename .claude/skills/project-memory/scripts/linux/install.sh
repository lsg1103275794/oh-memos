#!/bin/bash
#===============================================
# Project Memory Skill - Linux/macOS Installer
#===============================================

set -e

SKILL_DIR="$HOME/.claude/skills/project-memory"
BIN_DIR="$HOME/.local/bin"

echo "========================================"
echo "  Project Memory Skill Installer"
echo "  Platform: Linux/macOS"
echo "========================================"
echo

# Check Python
echo "[1/4] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.8+"
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "      Python $PYTHON_VERSION found"

# Check MemOS
echo
echo "[2/4] Checking MemOS..."
MEMOS_URL="${MEMOS_URL:-http://localhost:18000}"
if curl -s --connect-timeout 3 "$MEMOS_URL" > /dev/null 2>&1; then
    echo "      MemOS available at $MEMOS_URL"
else
    echo "      WARNING: MemOS not responding at $MEMOS_URL"
    echo "      Make sure to start MemOS before using the skill"
fi

# Create symlinks
echo
echo "[3/4] Creating command shortcuts..."
mkdir -p "$BIN_DIR"

# Create wrapper scripts in PATH
cat > "$BIN_DIR/memos-save" << 'EOF'
#!/bin/bash
python3 "$HOME/.claude/skills/project-memory/scripts/memos_save.py" "$@"
EOF

cat > "$BIN_DIR/memos-search" << 'EOF'
#!/bin/bash
python3 "$HOME/.claude/skills/project-memory/scripts/memos_search.py" "$@"
EOF

cat > "$BIN_DIR/memos-init" << 'EOF'
#!/bin/bash
python3 "$HOME/.claude/skills/project-memory/scripts/memos_init_project.py" "$@"
EOF

chmod +x "$BIN_DIR/memos-save" "$BIN_DIR/memos-search" "$BIN_DIR/memos-init"
echo "      Commands installed to $BIN_DIR"

# Check PATH
echo
echo "[4/4] Checking PATH..."
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "      WARNING: $BIN_DIR is not in PATH"
    echo "      Add this line to your ~/.bashrc or ~/.zshrc:"
    echo
    echo "        export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo
else
    echo "      PATH OK"
fi

echo
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo
echo "Usage:"
echo "  memos-init                    # Initialize current project"
echo "  memos-save \"content\" -t TYPE  # Save a memory"
echo "  memos-search \"query\"          # Search memories"
echo
echo "Environment variables (optional):"
echo "  MEMOS_URL    - MemOS API URL (default: http://localhost:18000)"
echo "  MEMOS_USER   - User ID (default: dev_user)"
echo
