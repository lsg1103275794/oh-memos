#!/bin/bash
# Project Memory - Search memories in MemOS
# Usage: memos-search.sh "query" [-p PROJECT] [--all] [--json]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$SCRIPT_DIR/memos_search.py" "$@"
