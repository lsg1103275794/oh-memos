#!/bin/bash
# Project Memory - Save memory to MemOS
# Usage: memos-save.sh "content" [-t TYPE] [-p PROJECT] [--tags tag1 tag2]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$SCRIPT_DIR/memos_save.py" "$@"
