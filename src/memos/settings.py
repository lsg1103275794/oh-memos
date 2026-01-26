import os

from pathlib import Path

from dotenv import load_dotenv

# Load environment variables FIRST before reading any config
load_dotenv(override=True)

MEMOS_DIR = Path(os.getenv("MEMOS_BASE_PATH", Path.cwd())) / ".memos"
DEBUG = os.getenv("MEMOS_DEBUG", "false").lower() == "true"

# "memos" or "memos.submodules" ... to filter logs from specific packages
LOG_FILTER_TREE_PREFIX = ""
