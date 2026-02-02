#!/usr/bin/env python3
"""
MemOS MCP Server Configuration Module

Contains all configuration constants, CLI argument parsing, and global state.

Configuration priority: CLI args > environment variables > defaults
All environment variables are loaded from .env file in project root.
"""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv
from mcp.server import Server


# ============================================================================
# .env Loading
# ============================================================================

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_dotenv_path = os.path.join(_project_root, ".env")
if os.path.isfile(_dotenv_path):
    load_dotenv(_dotenv_path, override=True)
else:
    load_dotenv()  # fallback: search from cwd upward


# ============================================================================
# CLI Argument Parsing
# ============================================================================

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


# ============================================================================
# Logging
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("memos-mcp")


# ============================================================================
# Configuration Helpers
# ============================================================================

def _get_env(key: str, *alternatives: str, default: str | None = None) -> str | None:
    """Get environment variable, checking alternatives. Returns None for empty strings."""
    val = os.environ.get(key, "").strip()
    if val:
        return val
    for alt in alternatives:
        val = os.environ.get(alt, "").strip()
        if val:
            return val
    return default


def _require(name: str, value: str | None) -> str:
    """Require a non-empty value."""
    if not value:
        raise RuntimeError(f"{name} is required (set {name} in .env)")
    return value


def _require_float(name: str, value: str | None, default: float | None = None) -> float:
    """Require a float value, with optional default."""
    if not value and default is not None:
        return default
    raw = _require(name, value)
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a float, got: {raw}") from exc


# ============================================================================
# Core Configuration (CLI args > env vars > defaults)
# ============================================================================

# -- API Connection --
MEMOS_URL = _require("MEMOS_URL",
    _args.memos_url or _get_env("MEMOS_URL", "MEMOS_BASE_URL"))

MEMOS_USER = _require("MEMOS_USER",
    _args.memos_user or _get_env("MEMOS_USER", "MOS_USER_ID"))

_default_cube_from_env = _args.memos_default_cube is not None or os.environ.get("MEMOS_DEFAULT_CUBE") is not None
MEMOS_DEFAULT_CUBE = _require("MEMOS_DEFAULT_CUBE",
    _args.memos_default_cube or _get_env("MEMOS_DEFAULT_CUBE"))

MEMOS_CUBES_DIR = _require("MEMOS_CUBES_DIR",
    _args.memos_cubes_dir or _get_env("MEMOS_CUBES_DIR"))

# -- Timeouts (seconds) --
MEMOS_TIMEOUT_TOOL = _require_float("MEMOS_TIMEOUT_TOOL",
    _args.memos_timeout_tool or _get_env("MEMOS_TIMEOUT_TOOL"), default=120.0)
MEMOS_TIMEOUT_STARTUP = _require_float("MEMOS_TIMEOUT_STARTUP",
    _args.memos_timeout_startup or _get_env("MEMOS_TIMEOUT_STARTUP"), default=30.0)
MEMOS_TIMEOUT_HEALTH = _require_float("MEMOS_TIMEOUT_HEALTH",
    _args.memos_timeout_health or _get_env("MEMOS_TIMEOUT_HEALTH"), default=5.0)
MEMOS_API_WAIT_MAX = _require_float("MEMOS_API_WAIT_MAX",
    _args.memos_api_wait_max or _get_env("MEMOS_API_WAIT_MAX"), default=60.0)

# -- Feature Flags --
_enable_delete_raw = _args.memos_enable_delete or _get_env("MEMOS_ENABLE_DELETE", default="false")
MEMOS_ENABLE_DELETE = _enable_delete_raw.lower() == "true"

# -- Neo4j (for fallback direct graph queries) --
NEO4J_HTTP_URL = _get_env("NEO4J_HTTP_URL")
NEO4J_USER = _get_env("NEO4J_USER")
NEO4J_PASSWORD = _get_env("NEO4J_PASSWORD")


# ============================================================================
# MCP Server Instance
# ============================================================================

server = Server("memos-memory")


# ============================================================================
# Cube Registration Tracking
# ============================================================================

_registered_cubes: set[str] = set()
_last_registration_attempt: dict[str, float] = {}  # cube_id -> timestamp
REGISTRATION_RETRY_INTERVAL = 5.0  # seconds


# ============================================================================
# Memory Types
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
# Keyword Stopwords
# ============================================================================

_KEYWORD_STOPWORDS = {
    "the", "and", "or", "a", "an", "to", "of", "for", "with", "in", "on",
    "at", "is", "are", "was", "were", "be", "this", "that", "it", "as",
    "from", "by", "about", "into", "over", "after", "before", "not",
    "的", "了", "和", "与", "在", "是", "有", "我", "你", "他", "她",
    "它", "我们", "你们", "他们", "以及", "或", "并",
}


# ============================================================================
# Keyword Enhancer
# ============================================================================

try:
    from keyword_enhancer import (
        ALL_STOPWORDS,
        detect_cube_from_path,
        extract_keywords_enhanced,
        find_fuzzy_matches,
        keyword_match_score_enhanced,
    )
    KEYWORD_ENHANCER_AVAILABLE = True
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
