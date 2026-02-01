#!/usr/bin/env python3
"""
MemOS MCP Server Configuration Module

Contains all configuration constants, CLI argument parsing, and global state.
"""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv
from mcp.server import Server


# Load .env from project root (parent of mcp-server/)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_dotenv_path = os.path.join(_project_root, ".env")
if os.path.isfile(_dotenv_path):
    load_dotenv(_dotenv_path, override=True)
else:
    load_dotenv()  # fallback: search from cwd upward


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='MemOS MCP Server')
    parser.add_argument('--memos-url', default=None, help='MemOS API URL')
    parser.add_argument('--memos-user', default=None, help='Default user ID')
    parser.add_argument('--memos-default-cube', default=None, help='Default cube ID')
    parser.add_argument('--memos-cubes-dir', default=None, help='Cubes directory path')
    parser.add_argument('--memos-enable-delete', default=None, help='Enable delete tool (true/false)')
    parser.add_argument('--memos-timeout-tool', default=None, help='Tool call timeout in seconds')
    parser.add_argument('--memos-timeout-startup', default=None, help='Startup timeout in seconds')
    parser.add_argument('--memos-timeout-health', default=None, help='Health check timeout in seconds')
    parser.add_argument('--memos-api-wait-max', default=None, help='Max API wait time in seconds')
    return parser.parse_known_args()[0]


_args = parse_args()


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("memos-mcp")


# ============================================================================
# Helper functions for required values
# ============================================================================

def _require_env_value(name: str, value: str | None) -> str:
    if value is None or value == "":
        raise RuntimeError(f"{name} is required (set {name} in .env)")
    return value


def _require_float(name: str, value: str | None) -> float:
    raw = _require_env_value(name, value)
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a float, got: {raw}") from exc


# ============================================================================
# Configuration: CLI args take precedence over env vars
# ============================================================================

MEMOS_URL = _args.memos_url or os.environ.get("MEMOS_URL") or os.environ.get("MEMOS_BASE_URL")
if not MEMOS_URL:
    raise RuntimeError("MEMOS_URL is required (set MEMOS_URL or MEMOS_BASE_URL in .env)")

MEMOS_USER = _args.memos_user or os.environ.get("MEMOS_USER")
if not MEMOS_USER:
    raise RuntimeError("MEMOS_USER is required (set MEMOS_USER in .env)")

_default_cube_from_env = _args.memos_default_cube is not None or os.environ.get("MEMOS_DEFAULT_CUBE") is not None
MEMOS_DEFAULT_CUBE = _args.memos_default_cube or os.environ.get("MEMOS_DEFAULT_CUBE")
if not MEMOS_DEFAULT_CUBE:
    raise RuntimeError("MEMOS_DEFAULT_CUBE is required (set MEMOS_DEFAULT_CUBE in .env)")

MEMOS_CUBES_DIR = _args.memos_cubes_dir or os.environ.get("MEMOS_CUBES_DIR")
if not MEMOS_CUBES_DIR:
    raise RuntimeError("MEMOS_CUBES_DIR is required (set MEMOS_CUBES_DIR in .env)")


# Timeout configuration (in seconds)
MEMOS_TIMEOUT_TOOL = _require_float("MEMOS_TIMEOUT_TOOL", _args.memos_timeout_tool or os.environ.get("MEMOS_TIMEOUT_TOOL"))
MEMOS_TIMEOUT_STARTUP = _require_float("MEMOS_TIMEOUT_STARTUP", _args.memos_timeout_startup or os.environ.get("MEMOS_TIMEOUT_STARTUP"))
MEMOS_TIMEOUT_HEALTH = _require_float("MEMOS_TIMEOUT_HEALTH", _args.memos_timeout_health or os.environ.get("MEMOS_TIMEOUT_HEALTH"))
MEMOS_API_WAIT_MAX = _require_float("MEMOS_API_WAIT_MAX", _args.memos_api_wait_max or os.environ.get("MEMOS_API_WAIT_MAX"))

_enable_delete_val = _require_env_value("MEMOS_ENABLE_DELETE", _args.memos_enable_delete or os.environ.get("MEMOS_ENABLE_DELETE"))
MEMOS_ENABLE_DELETE = _enable_delete_val.lower() == "true"


# Neo4j configuration (for fallback direct queries)
NEO4J_HTTP_URL = os.environ.get("NEO4J_HTTP_URL")
NEO4J_USER = os.environ.get("NEO4J_USER")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")


# ============================================================================
# MCP Server instance
# ============================================================================

server = Server("memos-memory")


# ============================================================================
# Cube registration tracking
# ============================================================================

_registered_cubes: set[str] = set()
_last_registration_attempt: dict[str, float] = {}  # cube_id -> timestamp
REGISTRATION_RETRY_INTERVAL = 5.0  # seconds


# ============================================================================
# Memory types
# ============================================================================

MEMORY_TYPES = {
    "ERROR_PATTERN",
    "DECISION",
    "MILESTONE",
    "BUGFIX",
    "FEATURE",
    "CONFIG",
    "CODE_PATTERN",
    "GOTCHA",
    "PROGRESS",
}


# ============================================================================
# Keyword stopwords (basic set, can be overridden by keyword_enhancer)
# ============================================================================

_KEYWORD_STOPWORDS = {
    "the", "and", "or", "a", "an", "to", "of", "for", "with", "in", "on",
    "at", "is", "are", "was", "were", "be", "this", "that", "it", "as",
    "from", "by", "about", "into", "over", "after", "before", "not",
    "的", "了", "和", "与", "在", "是", "有", "我", "你", "他", "她",
    "它", "我们", "你们", "他们", "以及", "或", "并",
}


# ============================================================================
# Keyword enhancer availability check
# ============================================================================

try:
    from keyword_enhancer import (
        ALL_STOPWORDS,
        extract_keywords_enhanced,
        keyword_match_score_enhanced,
        detect_cube_from_path,
        find_fuzzy_matches,
    )
    KEYWORD_ENHANCER_AVAILABLE = True
    # Use enhanced stopwords if available
    _KEYWORD_STOPWORDS = ALL_STOPWORDS
except ImportError:
    KEYWORD_ENHANCER_AVAILABLE = False
    extract_keywords_enhanced = None
    keyword_match_score_enhanced = None
    detect_cube_from_path = None
    find_fuzzy_matches = None


def is_default_cube_from_env() -> bool:
    """Check if default cube was explicitly set from environment."""
    return _default_cube_from_env
