#!/bin/bash
# Project Memory - Initialize project memory cube
# Usage: memos-init.sh [-p PROJECT] [-u USER]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$SCRIPT_DIR/memos_init_project.py" "$@"
