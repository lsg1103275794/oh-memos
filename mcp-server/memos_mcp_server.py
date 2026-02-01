#!/usr/bin/env python3
"""
MemOS MCP Server - Intelligent Memory Management for Claude Code

This MCP server provides tools for Claude to proactively search and save
project memories, enabling intelligent context-aware assistance.
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys

from typing import Any, Optional

import httpx
from dotenv import load_dotenv

# Import keyword enhancer module
try:
    from keyword_enhancer import (
        ALL_STOPWORDS,
        extract_keywords_enhanced,
        keyword_match_score_enhanced,
        detect_cube_from_path,
        find_fuzzy_matches,
    )
    KEYWORD_ENHANCER_AVAILABLE = True
except ImportError:
    KEYWORD_ENHANCER_AVAILABLE = False

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)
from pydantic import BaseModel


# Load .env from project root (parent of mcp-server/)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_dotenv_path = os.path.join(_project_root, ".env")
if os.path.isfile(_dotenv_path):
    load_dotenv(_dotenv_path, override=True)
else:
    load_dotenv()  # fallback: search from cwd upward


# Parse command line arguments first (WSL env vars don't pass to Windows Python)
def parse_args():
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

# Configuration: CLI args take precedence over env vars
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
# Large documents with embedding may take longer
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

# Create server instance
server = Server("memos-memory")

# Track registered cubes to avoid repeated registration attempts
_registered_cubes: set[str] = set()
_last_registration_attempt: dict[str, float] = {}  # cube_id -> timestamp
REGISTRATION_RETRY_INTERVAL = 5.0  # seconds


def list_available_cubes() -> list[dict[str, str]]:
    """
    Scan the cubes directory to find all available cubes.

    Returns:
        List of dicts with 'id' and 'path' keys for each available cube.
    """
    available = []
    cubes_dir = MEMOS_CUBES_DIR

    # Handle case where MEMOS_CUBES_DIR is a full path to a specific cube
    if cubes_dir.endswith(MEMOS_DEFAULT_CUBE):
        cubes_dir = os.path.dirname(cubes_dir)

    if not os.path.isdir(cubes_dir):
        logger.warning(f"Cubes directory does not exist: {cubes_dir}")
        return available

    try:
        for item in os.listdir(cubes_dir):
            item_path = os.path.join(cubes_dir, item)
            config_path = os.path.join(item_path, "config.json")
            # A valid cube has a config.json file
            if os.path.isdir(item_path) and os.path.isfile(config_path):
                available.append({
                    "id": item,
                    "path": item_path
                })
    except Exception as e:
        logger.warning(f"Error scanning cubes directory: {e}")

    return available


def get_cube_path(cube_id: str) -> str | None:
    """
    Get the full path for a cube ID, checking if it exists.

    Returns:
        Full path if cube exists, None otherwise.
    """
    # If cube_id is the default cube, use its configured full path
    if cube_id == MEMOS_DEFAULT_CUBE:
        if MEMOS_CUBES_DIR.endswith(MEMOS_DEFAULT_CUBE):
            cube_path = MEMOS_CUBES_DIR
        else:
            cube_path = f"{MEMOS_CUBES_DIR}/{MEMOS_DEFAULT_CUBE}"
    else:
        # For other cubes, derive path from cubes directory
        cubes_dir = MEMOS_CUBES_DIR
        if cubes_dir.endswith(MEMOS_DEFAULT_CUBE):
            cubes_dir = os.path.dirname(cubes_dir)
        cube_path = f"{cubes_dir}/{cube_id}"

    # Check if the path exists with a config.json
    config_path = os.path.join(cube_path, "config.json")
    if os.path.isdir(cube_path) and os.path.isfile(config_path):
        return cube_path

    return None


def get_cubes_base_dir() -> str:
    cubes_dir = MEMOS_CUBES_DIR
    if cubes_dir.endswith(MEMOS_DEFAULT_CUBE):
        return os.path.dirname(cubes_dir)
    return cubes_dir


def _clone_config(config: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(config))


def _update_config_for_cube(config: dict[str, Any], cube_id: str) -> dict[str, Any]:
    config["user_id"] = MEMOS_USER
    config["cube_id"] = cube_id
    config["config_filename"] = "config.json"

    text_mem = config.get("text_mem", {})
    text_cfg = text_mem.get("config", {}) if isinstance(text_mem, dict) else {}

    if isinstance(text_cfg, dict):
        if "cube_id" in text_cfg:
            text_cfg["cube_id"] = cube_id

        graph_db = text_cfg.get("graph_db", {})
        graph_cfg = graph_db.get("config", {}) if isinstance(graph_db, dict) else {}
        if isinstance(graph_cfg, dict):
            use_multi_db = graph_cfg.get("use_multi_db")
            if use_multi_db is False or "user_name" in graph_cfg:
                graph_cfg["user_name"] = cube_id
            vec_cfg = graph_cfg.get("vec_config", {}).get("config")
            if isinstance(vec_cfg, dict) and "collection_name" in vec_cfg:
                vec_cfg["collection_name"] = f"{cube_id}_graph"

        vector_db = text_cfg.get("vector_db", {})
        vector_cfg = vector_db.get("config") if isinstance(vector_db, dict) else {}
        if isinstance(vector_cfg, dict) and "collection_name" in vector_cfg:
            vector_cfg["collection_name"] = f"{cube_id}_collection"

    return config


def _build_fallback_cube_config(cube_id: str) -> dict[str, Any]:
    def _require_env(key: str) -> str:
        value = os.getenv(key)
        if value is None or value == "":
            raise RuntimeError(f"{key} is required (set {key} in .env)")
        return value

    def _get_float(key: str) -> float:
        raw = _require_env(key)
        try:
            return float(raw)
        except ValueError as exc:
            raise RuntimeError(f"{key} must be a float, got: {raw}") from exc

    def _get_int(key: str) -> int:
        raw = _require_env(key)
        try:
            return int(raw)
        except ValueError as exc:
            raise RuntimeError(f"{key} must be an int, got: {raw}") from exc

    openai_config = {
        "model_name_or_path": _require_env("MOS_CHAT_MODEL"),
        "temperature": _get_float("MOS_CHAT_TEMPERATURE"),
        "max_tokens": _get_int("MOS_MAX_TOKENS"),
        "top_p": _get_float("MOS_TOP_P"),
        "top_k": _get_int("MOS_TOP_K"),
        "remove_think_prefix": True,
        "api_key": _require_env("OPENAI_API_KEY"),
        "api_base": _require_env("OPENAI_API_BASE"),
    }

    embedder_base_url = os.getenv("MOS_EMBEDDER_API_BASE") or _require_env("OPENAI_API_BASE")

    embedder_config = {
        "backend": _require_env("MOS_EMBEDDER_BACKEND"),
        "config": {
            "provider": _require_env("MOS_EMBEDDER_PROVIDER"),
            "api_key": _require_env("OPENAI_API_KEY"),
            "model_name_or_path": _require_env("MOS_EMBEDDER_MODEL"),
            "base_url": embedder_base_url,
            "embedding_dims": _get_int("EMBEDDING_DIMENSION"),
        },
    }

    neo4j_backend = _require_env("NEO4J_BACKEND").lower()
    if neo4j_backend == "neo4j":
        graph_config = {
            "uri": _require_env("NEO4J_URI"),
            "user": _require_env("NEO4J_USER"),
            "db_name": _require_env("NEO4J_DB_NAME"),
            "password": _require_env("NEO4J_PASSWORD"),
            "auto_create": _require_env("NEO4J_AUTO_CREATE").lower() == "true",
            "use_multi_db": _require_env("NEO4J_USE_MULTI_DB").lower() == "true",
            "user_name": cube_id,
            "embedding_dimension": _get_int("EMBEDDING_DIMENSION"),
        }
    else:
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_host = None
        qdrant_port = None
        if not qdrant_url:
            qdrant_host = _require_env("QDRANT_HOST")
            qdrant_port = _get_int("QDRANT_PORT")
        graph_config = {
            "uri": _require_env("NEO4J_URI"),
            "user": _require_env("NEO4J_USER"),
            "db_name": _require_env("NEO4J_DB_NAME"),
            "password": _require_env("NEO4J_PASSWORD"),
            "user_name": cube_id,
            "auto_create": False,
            "use_multi_db": False,
            "embedding_dimension": _get_int("EMBEDDING_DIMENSION"),
            "vec_config": {
                "backend": "qdrant",
                "config": {
                    "collection_name": f"{cube_id}_graph",
                    "vector_dimension": _get_int("EMBEDDING_DIMENSION"),
                    "distance_metric": "cosine",
                    "host": qdrant_host,
                    "port": qdrant_port,
                    "path": os.getenv("QDRANT_PATH"),
                    "url": qdrant_url,
                    "api_key": os.getenv("QDRANT_API_KEY"),
                },
            },
        }

    return {
        "model_schema": "memos.configs.mem_cube.GeneralMemCubeConfig",
        "user_id": MEMOS_USER,
        "cube_id": cube_id,
        "config_filename": "config.json",
        "text_mem": {
            "backend": "tree_text",
            "config": {
                "extractor_llm": {"backend": "openai", "config": openai_config},
                "dispatcher_llm": {"backend": "openai", "config": openai_config},
                "embedder": embedder_config,
                "graph_db": {"backend": neo4j_backend, "config": graph_config},
                "reorganize": _require_env("MOS_ENABLE_REORGANIZE").lower() == "true",
                "search_strategy": {
                    "bm25": _require_env("BM25_CALL").lower() == "true",
                    "cot": _require_env("VEC_COT_CALL").lower() == "true",
                },
            },
        },
        "act_mem": {},
        "para_mem": {},
    }


def _build_cube_config(cube_id: str) -> dict[str, Any]:
    template_path = get_cube_path(MEMOS_DEFAULT_CUBE)
    if template_path is not None:
        config_path = os.path.join(template_path, "config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            config = _clone_config(config)
            return _update_config_for_cube(config, cube_id)
        except Exception as e:
            logger.warning(f"Failed to read template cube config: {e}")
    return _build_fallback_cube_config(cube_id)


def validate_and_fix_cube_config(cube_id: str, config_path: str) -> tuple[bool, str | None]:
    """
    Validate cube config and fix user_name mismatch if found.

    Returns:
        (was_fixed, error_message)
        - was_fixed: True if config was modified
        - error_message: None if OK, error string if failed
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        modified = False
        issues = []

        # Check top-level cube_id
        if config.get("cube_id") != cube_id:
            issues.append(f"cube_id mismatch: {config.get('cube_id')} -> {cube_id}")
            config["cube_id"] = cube_id
            modified = True

        # Check graph_db user_name
        text_mem = config.get("text_mem", {})
        text_cfg = text_mem.get("config", {}) if isinstance(text_mem, dict) else {}
        if isinstance(text_cfg, dict):
            # Update nested cube_id
            if text_cfg.get("cube_id") != cube_id:
                text_cfg["cube_id"] = cube_id
                modified = True

            graph_db = text_cfg.get("graph_db", {})
            graph_cfg = graph_db.get("config", {}) if isinstance(graph_db, dict) else {}
            if isinstance(graph_cfg, dict):
                current_user_name = graph_cfg.get("user_name")
                if current_user_name and current_user_name != cube_id:
                    issues.append(f"graph_db.user_name mismatch: {current_user_name} -> {cube_id}")
                    graph_cfg["user_name"] = cube_id
                    modified = True

                # Fix vec_config collection_name
                vec_cfg = graph_cfg.get("vec_config", {}).get("config", {})
                if isinstance(vec_cfg, dict):
                    expected_collection = f"{cube_id}_graph"
                    if vec_cfg.get("collection_name") and vec_cfg["collection_name"] != expected_collection:
                        vec_cfg["collection_name"] = expected_collection
                        modified = True

        if modified:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"Fixed cube config for '{cube_id}': {', '.join(issues)}")

        return modified, None
    except Exception as e:
        return False, f"Failed to validate cube config: {e}"


def ensure_cube_directory(cube_id: str) -> tuple[str | None, str | None]:
    cubes_dir = get_cubes_base_dir()
    try:
        os.makedirs(cubes_dir, exist_ok=True)
        cube_dir = os.path.join(cubes_dir, cube_id)
        config_path = os.path.join(cube_dir, "config.json")
        if os.path.isdir(cube_dir) and os.path.isfile(config_path):
            # Validate and fix existing config if needed
            validate_and_fix_cube_config(cube_id, config_path)
            return cube_dir, None
        os.makedirs(cube_dir, exist_ok=True)
        config = _build_cube_config(cube_id)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return cube_dir, None
    except Exception as e:
        return None, f"Failed to create cube '{cube_id}': {e}"


def get_default_cube_id() -> str:
    """
    Get the default cube ID based on environment or project path.

    Priority:
    1. Explicit env var MEMOS_DEFAULT_CUBE (if path exists)
    2. Derived from current working directory using smart detection
    3. Fallback to MEMOS_DEFAULT_CUBE constant
    """
    if _default_cube_from_env:
        cube_path = get_cube_path(MEMOS_DEFAULT_CUBE)
        if cube_path is not None:
            return MEMOS_DEFAULT_CUBE
    try:
        cwd = os.getcwd()
        # Use enhanced detection if available
        if KEYWORD_ENHANCER_AVAILABLE:
            return detect_cube_from_path(cwd)
        # Fallback to basic detection
        folder_name = os.path.basename(cwd)
        if not folder_name:
            return MEMOS_DEFAULT_CUBE
        cube_id = folder_name.lower()
        cube_id = re.sub(r"[\-\.\s]+", "_", cube_id)
        return f"{cube_id}_cube"
    except Exception as e:
        logger.debug(f"Failed to derive cube_id from CWD: {e}")
        return MEMOS_DEFAULT_CUBE


async def verify_cube_loaded(client: httpx.AsyncClient, cube_id: str) -> bool:
    """Verify cube is actually loaded in API (not just registered)."""
    try:
        response = await client.get(
            f"{MEMOS_URL}/memories",
            params={"user_id": MEMOS_USER, "mem_cube_id": cube_id}
        )
        if response.status_code == 200:
            data = response.json()
            # code 200 means cube is loaded, even if no memories
            return data.get("code") == 200
    except Exception:
        pass
    return False


async def ensure_cube_registered(
    client: httpx.AsyncClient,
    cube_id: str,
    force: bool = False
) -> tuple[bool, str | None]:
    """Ensure cube is registered and loaded.

    Args:
        client: HTTP client
        cube_id: Cube ID to register
        force: If True, skip cache and always try to register

    Returns:
        Tuple of (success: bool, error_message: str | None).
        If success is False, error_message contains helpful guidance.
    """
    import time
    now = time.time()

    # Check cache (unless forced)
    if not force and cube_id in _registered_cubes:
        return True, None

    # Rate limit registration attempts (unless forced)
    if not force:
        last_attempt = _last_registration_attempt.get(cube_id, 0)
        if now - last_attempt < REGISTRATION_RETRY_INTERVAL:
            if cube_id in _registered_cubes:
                return True, None
            # Don't return error yet, let it try again

    _last_registration_attempt[cube_id] = now

    try:
        # First check if already loaded
        if await verify_cube_loaded(client, cube_id):
            _registered_cubes.add(cube_id)
            logger.info(f"Cube '{cube_id}' already loaded")
            return True, None

        # Check if the cube path exists before trying to register
        cube_path = get_cube_path(cube_id)
        if cube_path is None:
            # Cube doesn't exist - provide helpful message with available cubes
            available = list_available_cubes()
            available_ids = [c["id"] for c in available]

            if available_ids:
                error_msg = (
                    f"Cube '{cube_id}' not found. Available cubes: {available_ids}. "
                    f"Use memos_list_cubes to see all available cubes, or check the cube ID."
                )
            else:
                cubes_dir = MEMOS_CUBES_DIR
                if cubes_dir.endswith(MEMOS_DEFAULT_CUBE):
                    cubes_dir = os.path.dirname(cubes_dir)
                error_msg = (
                    f"Cube '{cube_id}' not found and no cubes available in '{cubes_dir}'. "
                    f"Please create a cube first using the MemOS web interface or CLI."
                )
            logger.warning(error_msg)
            return False, error_msg

        # Try to register the cube
        response = await client.post(
            f"{MEMOS_URL}/mem_cubes",
            json={
                "user_id": MEMOS_USER,
                "mem_cube_name_or_path": cube_path,
                "mem_cube_id": cube_id
            }
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                _registered_cubes.add(cube_id)
                logger.info(f"Auto-registered cube: {cube_id}")
                return True, None
            # Already registered is also success
            if "already" in data.get("message", "").lower():
                _registered_cubes.add(cube_id)
                return True, None
            # Registration failed - provide helpful message
            api_msg = data.get("message", "Unknown error")
            available = list_available_cubes()
            available_ids = [c["id"] for c in available]
            error_msg = (
                f"Failed to register cube '{cube_id}': {api_msg}. "
                f"Available cubes: {available_ids if available_ids else 'none'}."
            )
            logger.warning(error_msg)
            return False, error_msg

    except httpx.ConnectError:
        error_msg = f"Cannot connect to MemOS API at {MEMOS_URL}. Is the server running?"
        logger.warning(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Failed to register cube '{cube_id}': {e}"
        logger.warning(error_msg)
        return False, error_msg

    return False, f"Unknown error registering cube '{cube_id}'"


async def wait_for_api_ready(max_wait: float | None = None, interval: float = 2.0) -> bool:
    """Wait for MemOS API to be ready. Returns True if ready."""
    import time
    if max_wait is None:
        max_wait = MEMOS_API_WAIT_MAX
    start = time.time()

    async with httpx.AsyncClient(timeout=MEMOS_TIMEOUT_HEALTH) as client:
        while time.time() - start < max_wait:
            try:
                response = await client.get(f"{MEMOS_URL}/users")
                if response.status_code == 200:
                    logger.info("MemOS API is ready")
                    return True
            except httpx.ConnectError:
                pass
            except Exception as e:
                logger.debug(f"API check failed: {e}")

            await asyncio.sleep(interval)

    logger.warning(f"MemOS API not ready after {max_wait}s")
    return False


class MemorySearchResult(BaseModel):
    """Structured memory search result."""
    id: str
    content: str
    relevance: float = 1.0
    metadata: dict[str, Any] = {}


def format_memories_for_display(data: dict) -> str:
    """Format memory search results for readable display."""
    results = []

    # Process text memories
    text_mems = data.get("text_mem", [])
    for cube_data in text_mems:
        cube_id = cube_data.get("cube_id", "unknown")
        memories_data = cube_data.get("memories", [])
        
        # If memories is a dict with nodes (tree_text mode), extract nodes
        memories = []
        if isinstance(memories_data, dict) and "nodes" in memories_data:
            memories = memories_data["nodes"]
        elif isinstance(memories_data, list):
            memories = memories_data

        if memories:
            results.append(f"## 📦 Cube: {cube_id}")
            results.append("")

            # Group by type
            grouped = {}
            for mem in memories:
                memory_text = mem.get("memory", "")
                # Try to extract type from [TYPE] prefix
                type_match = re.match(r"^\[([A-Z_]+)\]", memory_text)
                mem_type = type_match.group(1) if type_match else "PROGRESS"
                if mem_type not in grouped:
                    grouped[mem_type] = []
                grouped[mem_type].append(mem)

            # Display by type
            for mem_type, items in grouped.items():
                results.append(f"### 🏷️ Type: {mem_type}")
                results.append("")

                for i, mem in enumerate(items, 1):
                    memory_text = mem.get("memory", "")
                    mem_id = mem.get("id", "")  # Full UUID for delete operations

                    # Remove the [TYPE] prefix from display text if present
                    display_text = re.sub(r"^\[[A-Z_]+\]\s*", "", memory_text)

                    # Extract first line as title
                    first_line = display_text.split("\n")[0][:100]
                    if len(display_text.split("\n")) > 1 or len(display_text) > 100:
                        results.append(f"#### {i}. {first_line}")
                    else:
                        results.append(f"#### {i}. {display_text}")

                    results.append(f"ID: `{mem_id}`")
                    results.append("")
                    
                    # Detect if it's a code block (simple heuristic)
                    if "```" not in display_text and any(line.strip().startswith(("import ", "def ", "class ", "export ", "const ", "let ", "var ")) for line in display_text.split("\n")):
                        results.append("```python")
                        results.append(display_text)
                        results.append("```")
                    else:
                        results.append(display_text)
                        
                    results.append("")
                    results.append("---")
                    results.append("")

    if not results:
        return "No memories found matching your query."

    return "\n".join(results)


def format_graph_for_display(data: list) -> str:
    """Format knowledge graph results with relationships for readable display."""
    results = []

    for cube_data in data:
        cube_id = cube_data.get("cube_id", "unknown")
        memories_list = cube_data.get("memories", [])

        if not memories_list:
            continue

        results.append(f"## 🧠 Knowledge Graph: {cube_id}")
        results.append("")

        for mem_data in memories_list:
            # Extract nodes and edges
            nodes = mem_data.get("nodes", [])
            edges = mem_data.get("edges", [])

            # Build node lookup for relationship display
            node_lookup = {}
            for node in nodes:
                node_id = node.get("id", "")
                node_memory = node.get("memory", "")
                # Clean up memory text for mermaid (remove newlines and special chars)
                clean_text = node_memory.replace("\n", " ").replace('"', "'").replace("[", "(").replace("]", ")")
                node_lookup[node_id] = clean_text[:50] + "..." if len(clean_text) > 50 else clean_text

            # Display nodes
            if nodes:
                results.append("### 📝 Memory Nodes")
                results.append("")
                for i, node in enumerate(nodes[:10], 1):  # Limit to 10 nodes
                    memory = node.get("memory", "")
                    first_line = memory.split("\n")[0][:100]
                    node_id = node.get("id", "")  # Full UUID for delete operations
                    results.append(f"{i}. **{first_line}**")
                    results.append(f"   ID: `{node_id}`")
                    results.append("")

            # Display relationships with Mermaid diagram
            if edges:
                results.append("### 📊 Relationship Diagram (Mermaid)")
                results.append("")
                results.append("```mermaid")
                results.append("graph TD")
                
                # Style definitions
                results.append("    classDef cause fill:#f96,stroke:#333,stroke-width:2px;")
                results.append("    classDef relate fill:#bbf,stroke:#333,stroke-width:1px;")
                results.append("    classDef conflict fill:#f66,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;")
                
                added_edges = set()
                for edge in edges:
                    source_id = edge.get("source", "")
                    target_id = edge.get("target", "")
                    rel_type = edge.get("type", "UNKNOWN")

                    # Skip PARENT relationships, only show semantic ones
                    if rel_type == "PARENT":
                        continue
                    
                    # Avoid duplicate edges in diagram
                    edge_key = f"{source_id}-{target_id}-{rel_type}"
                    if edge_key in added_edges:
                        continue
                    added_edges.add(edge_key)

                    source_text = node_lookup.get(source_id, source_id[:8])
                    target_text = node_lookup.get(target_id, target_id[:8])
                    
                    # Sanitize IDs for mermaid (must be alphanumeric)
                    s_id = f"node_{source_id[:8]}"
                    t_id = f"node_{target_id[:8]}"

                    # Format relationship in mermaid
                    if rel_type == "CAUSE":
                        results.append(f'    {s_id}["{source_text}"] -- CAUSE --> {t_id}["{target_text}"]:::cause')
                    elif rel_type == "RELATE":
                        results.append(f'    {s_id}["{source_text}"] -. RELATE .- {t_id}["{target_text}"]:::relate')
                    elif rel_type == "CONFLICT":
                        results.append(f'    {s_id}["{source_text}"] == CONFLICT == {t_id}["{target_text}"]:::conflict')
                    elif rel_type == "CONDITION":
                        results.append(f'    {s_id}["{source_text}"] -- CONDITION --> {t_id}["{target_text}"]')
                    else:
                        results.append(f'    {s_id}["{source_text}"] -- {rel_type} --> {t_id}["{target_text}"]')

                results.append("```")
                results.append("")

                # Textual fallback for terminals that don't render mermaid
                results.append("### 🔗 Textual Relationships")
                results.append("")
                results.append("```")
                for edge in edges:
                    if edge.get("type") == "PARENT": continue
                    s_text = node_lookup.get(edge.get("source"), "???")[:40]
                    t_text = node_lookup.get(edge.get("target"), "???")[:40]
                    results.append(f"[{s_text}] --{edge.get('type')}--> [{t_text}]")
                results.append("```")
                results.append("")

        results.append("---")

    if not results:
        return "No memories or relationships found."

    return "\n".join(results)


def detect_memory_type(content: str) -> tuple[str, float]:
    """
    自动检测记忆类型，返回 (类型, 置信度)。

    置信度说明:
    - 1.0: 显式指定类型
    - 0.85-0.95: 强特征匹配（如 traceback、决定采用）
    - 0.7-0.84: 中等特征匹配
    - 0.3: 默认 PROGRESS（无特征匹配）

    当置信度 < 0.6 时，建议显式指定 memory_type 参数。
    """
    content_lower = content.lower()

    # 强特征检测模式 (pattern, confidence)
    # 按类型分组，每个模式带有置信度权重
    strong_patterns: dict[str, list[tuple[str, float]]] = {
        "ERROR_PATTERN": [
            (r"error[:\s]", 0.9),
            (r"exception[:\s]", 0.9),
            (r"traceback", 0.95),
            (r"报错[：:]", 0.9),
            (r"错误原因", 0.85),
            (r"stack\s*trace", 0.9),
            (r"异常[：:]", 0.85),
        ],
        "BUGFIX": [
            (r"修复了", 0.9),
            (r"fixed\s+(the\s+)?bug", 0.9),
            (r"根本原因.*解决", 0.85),
            (r"bug\s*fix", 0.9),
            (r"修好了", 0.85),
            (r"patch(ed)?", 0.8),
        ],
        "DECISION": [
            (r"决定采用", 0.9),
            (r"技术选型", 0.9),
            (r"架构方案", 0.85),
            (r"options?\s+considered", 0.85),
            (r"选择了.*而不是", 0.9),
            (r"权衡.*之后", 0.85),
            (r"decided\s+to\s+use", 0.9),
            (r"chose\s+.*\s+over", 0.85),
        ],
        "GOTCHA": [
            (r"注意[：:!]", 0.85),
            (r"陷阱", 0.9),
            (r"gotcha", 0.9),
            (r"小心", 0.8),
            (r"踩坑", 0.9),
            (r"坑[：:]", 0.85),
            (r"caveat", 0.85),
            (r"watch\s+out", 0.85),
            (r"警告[：:]", 0.8),
        ],
        "CODE_PATTERN": [
            (r"代码模板", 0.9),
            (r"code\s+template", 0.9),
            (r"可复用.*模式", 0.85),
            (r"reusable\s+pattern", 0.85),
            (r"snippet[：:]", 0.8),
        ],
        "CONFIG": [
            (r"环境变量", 0.9),
            (r"配置文件", 0.85),
            (r"\.env\b", 0.8),
            (r"config\s+(file|change)", 0.85),
            (r"设置.*参数", 0.8),
        ],
        "FEATURE": [
            (r"新增功能", 0.9),
            (r"implemented?\s+new", 0.85),
            (r"added\s+feature", 0.85),
            (r"新功能[：:]", 0.9),
            (r"feature\s+complete", 0.85),
        ],
        "MILESTONE": [
            (r"里程碑", 0.9),
            (r"完成了.*项目", 0.8),
            (r"release\s+v?\d", 0.85),
            (r"发布.*版本", 0.85),
            (r"milestone\s+achieved", 0.9),
            (r"项目完成", 0.85),
        ],
    }

    best_match: tuple[str, float] = ("PROGRESS", 0.3)  # 默认低置信度

    for mem_type, patterns in strong_patterns.items():
        for pattern, confidence in patterns:
            if re.search(pattern, content_lower):
                if confidence > best_match[1]:
                    best_match = (mem_type, confidence)

    return best_match


def detect_memory_type_simple(content: str) -> str:
    """
    简化版类型检测，仅返回类型字符串。
    用于向后兼容。
    """
    mem_type, _ = detect_memory_type(content)
    return mem_type


def suggest_search_queries(context: str) -> list[str]:
    """Suggest relevant search queries based on context."""
    suggestions = []
    context_lower = context.lower()

    # Error-related suggestions
    if any(word in context_lower for word in ["error", "exception", "failed", "错误", "报错", "失败"]):
        # Try to extract error type
        error_match = re.search(r"(\w+Error|\w+Exception)", context)
        if error_match:
            suggestions.append(f"ERROR_PATTERN {error_match.group(1)}")
        suggestions.append("ERROR_PATTERN solution")

    # Config-related suggestions
    if any(word in context_lower for word in ["config", "setting", "env", "配置", "环境"]):
        suggestions.append("CONFIG environment")

    # Decision-related suggestions
    if any(word in context_lower for word in ["why", "为什么", "decision", "选择", "决定", "优化"]):
        suggestions.append("DECISION architecture")

    # Gotcha-related suggestions
    if any(word in context_lower for word in ["注意", "warning", "careful", "小心", "坑"]):
        suggestions.append("GOTCHA warning")

    # History-related suggestions
    if any(word in context_lower for word in ["之前", "上次", "previously", "last time", "earlier"]):
        suggestions.append("PROGRESS history")

    return suggestions[:3]  # Return top 3 suggestions


# =============================================================================
# HTTP Client Management (Connection Reuse)
# =============================================================================

_http_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    """Get or create a shared HTTP client for connection reuse."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=MEMOS_TIMEOUT_TOOL,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
    return _http_client


async def close_http_client():
    """Close the shared HTTP client."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


# =============================================================================
# API Call with Retry Helper
# =============================================================================

async def api_call_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    cube_id: str,
    **kwargs
) -> tuple[bool, dict | None, int]:
    """
    Make API call with automatic cube re-registration on failure.

    Returns:
        tuple: (success: bool, data: dict | None, status_code: int)
    """
    # First attempt
    if method.upper() == "GET":
        response = await client.get(url, **kwargs)
    elif method.upper() == "POST":
        response = await client.post(url, **kwargs)
    elif method.upper() == "DELETE":
        response = await client.delete(url, **kwargs)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

    if response.status_code == 200:
        data = response.json()
        if data.get("code") == 200:
            return True, data, 200

        # API returned error code - try re-registration
        _registered_cubes.discard(cube_id)
        reg_success, _ = await ensure_cube_registered(client, cube_id, force=True)
        if reg_success:
            # Retry
            if method.upper() == "GET":
                retry_response = await client.get(url, **kwargs)
            elif method.upper() == "POST":
                retry_response = await client.post(url, **kwargs)
            else:
                retry_response = await client.delete(url, **kwargs)

            if retry_response.status_code == 200:
                retry_data = retry_response.json()
                if retry_data.get("code") == 200:
                    return True, retry_data, 200
                return False, retry_data, 200

        return False, data, 200

    elif response.status_code == 400:
        # 400 often means cube not loaded - force re-register and retry
        _registered_cubes.discard(cube_id)
        reg_success, _ = await ensure_cube_registered(client, cube_id, force=True)
        if reg_success:
            if method.upper() == "GET":
                retry_response = await client.get(url, **kwargs)
            elif method.upper() == "POST":
                retry_response = await client.post(url, **kwargs)
            else:
                retry_response = await client.delete(url, **kwargs)

            if retry_response.status_code == 200:
                retry_data = retry_response.json()
                if retry_data.get("code") == 200:
                    return True, retry_data, 200
        return False, None, 400

    return False, None, response.status_code


# =============================================================================
# Memory Data Extraction Helper (handles both flat and tree_text modes)
# =============================================================================

def extract_memories_from_response(data: dict) -> list[dict]:
    """
    Extract memory nodes from API response, handling both flat and tree_text modes.

    Args:
        data: API response data containing text_mem

    Returns:
        List of memory node dictionaries
    """
    memories = []
    text_mems = data.get("text_mem", [])

    for cube_data in text_mems:
        mem_data = cube_data.get("memories", [])

        # Handle tree_text mode (dict with "nodes" key)
        if isinstance(mem_data, dict) and "nodes" in mem_data:
            memories.extend(mem_data["nodes"])
        # Handle flat mode (list of memories)
        elif isinstance(mem_data, list):
            memories.extend(mem_data)

    return memories


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


def parse_memory_type_prefix(query: str) -> tuple[str | None, str]:
    if not query:
        return None, ""
    match = re.match(r"^\s*\[?([A-Z_]+)\]?\s*[:\-]?\s*(.*)$", query)
    if not match:
        return None, query.strip()
    mem_type = match.group(1)
    rest = match.group(2).strip()
    if mem_type in MEMORY_TYPES:
        return mem_type, rest
    return None, query.strip()


_KEYWORD_STOPWORDS = {
    "the", "and", "or", "a", "an", "to", "of", "for", "with", "in", "on",
    "at", "is", "are", "was", "were", "be", "this", "that", "it", "as",
    "from", "by", "about", "into", "over", "after", "before", "not",
    "的", "了", "和", "与", "在", "是", "有", "我", "你", "他", "她",
    "它", "我们", "你们", "他们", "以及", "或", "并",
}

# Use enhanced stopwords if available
if KEYWORD_ENHANCER_AVAILABLE:
    _KEYWORD_STOPWORDS = ALL_STOPWORDS


def extract_keywords(query: str) -> list[str]:
    """Extract keywords from query with stopword filtering."""
    if KEYWORD_ENHANCER_AVAILABLE:
        return extract_keywords_enhanced(query, _KEYWORD_STOPWORDS)
    # Fallback to basic implementation
    if not query:
        return []
    raw_tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", query)
    keywords: list[str] = []
    seen = set()
    for token in raw_tokens:
        if not token:
            continue
        if re.search(r"[\u4e00-\u9fff]", token):
            if len(token) < 2:
                continue
            if token in _KEYWORD_STOPWORDS:
                continue
            if token not in seen:
                keywords.append(token)
                seen.add(token)
            continue
        lowered = token.lower()
        if len(lowered) < 2:
            continue
        if lowered in _KEYWORD_STOPWORDS:
            continue
        if lowered not in seen:
            keywords.append(lowered)
            seen.add(lowered)
    return keywords


def keyword_match_score(
    text: str,
    keywords: list[str],
    metadata: Optional[dict] = None,
    enable_fuzzy: bool = True
) -> float:
    """
    Calculate keyword match score with optional fuzzy matching.

    Args:
        text: The text to match against
        keywords: List of keywords
        metadata: Optional metadata with 'key' and 'tags' fields
        enable_fuzzy: Enable fuzzy matching (default True)

    Returns:
        Match score
    """
    if KEYWORD_ENHANCER_AVAILABLE:
        return keyword_match_score_enhanced(
            text, keywords, metadata, enable_fuzzy=enable_fuzzy
        )
    # Fallback to basic implementation
    if not text or not keywords:
        return 0.0
    text_lower = text.lower()
    matched = 0
    score = 0.0
    for kw in keywords:
        if re.search(r"[\u4e00-\u9fff]", kw):
            if kw in text:
                matched += 1
                score += 2.0
            continue
        if re.search(rf"\b{re.escape(kw)}\b", text_lower):
            matched += 1
            score += 2.0
        elif kw in text_lower:
            matched += 1
            score += 1.2
    if matched:
        score += matched / max(len(keywords), 1)
    return score


def apply_keyword_rerank(data: dict, query: str, enable_fuzzy: bool = True) -> dict:
    """
    Apply keyword-based reranking to search results.

    Args:
        data: Search results data
        query: Original query string
        enable_fuzzy: Enable fuzzy matching

    Returns:
        Reranked data
    """
    keywords = extract_keywords(query)
    if not keywords:
        return data
    text_mems = data.get("text_mem", [])
    for cube_data in text_mems:
        mem_data = cube_data.get("memories", [])
        if isinstance(mem_data, dict) and "nodes" in mem_data:
            nodes = mem_data.get("nodes", [])
            nodes.sort(
                key=lambda mem: (
                    mem.get("metadata", {}).get("relativity", 0.0)
                    + keyword_match_score(
                        mem.get("memory", ""),
                        keywords,
                        mem.get("metadata"),
                        enable_fuzzy
                    )
                ),
                reverse=True,
            )
        elif isinstance(mem_data, list):
            mem_data.sort(
                key=lambda mem: (
                    mem.get("metadata", {}).get("relativity", 0.0)
                    + keyword_match_score(
                        mem.get("memory", ""),
                        keywords,
                        mem.get("metadata"),
                        enable_fuzzy
                    )
                ),
                reverse=True,
            )
    return data


def filter_memories_by_type(data: dict, mem_type: str | None) -> dict:
    if not mem_type:
        return data
    text_mems = data.get("text_mem", [])
    for cube_data in text_mems:
        mem_data = cube_data.get("memories", [])
        if isinstance(mem_data, dict) and "nodes" in mem_data:
            nodes = mem_data.get("nodes", [])
            filtered_nodes = [
                node for node in nodes
                if re.match(rf"^\[{mem_type}\]", node.get("memory", ""))
            ]
            if "edges" in mem_data:
                kept_ids = {node.get("id", "") for node in filtered_nodes}
                edges = mem_data.get("edges", [])
                mem_data["edges"] = [
                    edge for edge in edges
                    if edge.get("source") in kept_ids and edge.get("target") in kept_ids
                ]
            mem_data["nodes"] = filtered_nodes
        elif isinstance(mem_data, list):
            mem_data[:] = [
                mem for mem in mem_data
                if re.match(rf"^\[{mem_type}\]", mem.get("memory", ""))
            ]
    return data


# =============================================================================
# Stats Computation Helper
# =============================================================================

def compute_memory_stats(data: dict) -> tuple[dict[str, int], int]:
    """
    Compute memory type statistics from API response.

    Args:
        data: API response data

    Returns:
        tuple: (stats_dict: {type: count}, total_count)
    """
    memories = extract_memories_from_response(data)
    stats: dict[str, int] = {}
    total = 0

    for mem in memories:
        memory_text = mem.get("memory", "")
        total += 1
        type_match = re.match(r"^\[([A-Z_]+)\]", memory_text)
        mem_type = type_match.group(1) if type_match else "PROGRESS"
        stats[mem_type] = stats.get(mem_type, 0) + 1

    return stats, total


# Define MCP Tools

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    tools = [
        Tool(
            name="memos_search",
            description="""Search project memories for relevant context.

USE THIS TOOL PROACTIVELY when:
- You encounter an error or exception (search for ERROR_PATTERN)
- User mentions "之前", "上次", "previously", "last time"
- You need to understand past decisions (search for DECISION)
- You're about to modify code that might have gotchas (search for GOTCHA)
- You see similar code patterns (search for CODE_PATTERN)
- Working with configuration files (search for CONFIG)

The tool returns relevant memories that can help you:
- Avoid repeating past mistakes
- Follow established patterns
- Understand architectural decisions
- Find solutions to similar problems""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query. Can be natural language or prefixed with memory type (e.g., 'ERROR_PATTERN ModuleNotFoundError', 'DECISION authentication')"
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'. Example: /mnt/g/test/MemOS → 'memos_cube', ~/my-app → 'my_app_cube'",
                        "default": MEMOS_DEFAULT_CUBE
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="memos_search_context",
            description="""Context-aware memory search with LLM intent analysis.

USE THIS TOOL when you need smarter search that understands:
- The broader conversation context (what you've been discussing)
- Implied entities and concepts that aren't explicitly mentioned
- The type of information the user is really looking for

This tool analyzes the query + recent conversation to:
1. Determine search intent (factual lookup, relationship query, causal question, etc.)
2. Extract explicit AND implied entities
3. Expand the query with related terms for better recall
4. Apply smart filters based on intent

Example: If you've been discussing "login errors" and user asks "what was the solution?",
this tool understands they mean "login error solution" even without explicit mention.

Best used when:
- Query is ambiguous or refers to earlier conversation
- You want better recall through query expansion
- You need to find related concepts, not just exact matches""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - can be brief since context helps clarify intent"
                    },
                    "context": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["user", "assistant"]},
                                "content": {"type": "string"}
                            }
                        },
                        "description": "Recent conversation messages for context (last 5-10 turns)"
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path.",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="memos_save",
            description="""Save important information to project memory.

🚨 **MUST: 显式指定 memory_type 参数** - 不要依赖自动检测！

USE THIS TOOL when:
- You've solved a bug or error → **MUST use BUGFIX or ERROR_PATTERN**
- A significant decision was made → **MUST use DECISION** with rationale
- You've completed a major task → **MUST use MILESTONE**
- You discovered a non-obvious gotcha → **MUST use GOTCHA**
- You created a reusable code pattern → **MUST use CODE_PATTERN**
- Configuration was changed → **MUST use CONFIG**

Memory types (按优先级选择，PROGRESS 仅用于纯进度汇报):
- ERROR_PATTERN: Error signature + solution (有通用复用价值)
- BUGFIX: Bug fix with cause and solution (一次性修复)
- DECISION: Architectural or design choice with rationale
- GOTCHA: Non-obvious issue or workaround
- CODE_PATTERN: Reusable code template
- CONFIG: Environment or configuration change
- FEATURE: New functionality added
- MILESTONE: Significant project achievement
- PROGRESS: **仅用于纯进度更新，禁止包含错误解决方案、技术决策、陷阱警告**

❌ 错误: memos_save(content="修复了模型路径问题") → 默认 PROGRESS
✅ 正确: memos_save(content="修复了模型路径问题...", memory_type="BUGFIX")""",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Memory content to save. Be detailed - include context, rationale, and relevant code/commands."
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "**MUST specify explicitly!** Type of memory. Do NOT rely on auto-detection. Use the decision tree: Bug fix → BUGFIX/ERROR_PATTERN, Technical decision → DECISION, Gotcha → GOTCHA, etc.",
                        "enum": ["ERROR_PATTERN", "DECISION", "MILESTONE", "BUGFIX",
                                "FEATURE", "CONFIG", "CODE_PATTERN", "GOTCHA", "PROGRESS"],
                        "default": "PROGRESS"
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'. Example: /mnt/g/test/MemOS → 'memos_cube', ~/my-app → 'my_app_cube'",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="memos_list_v2",
            description="""List memories from a memory cube (v2 with improved formatting).""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'. Example: /mnt/g/test/MemOS → 'memos_cube', ~/my-app → 'my_app_cube'",
                        "default": MEMOS_DEFAULT_CUBE
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memories to return.",
                        "default": 20
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Optional: Filter by memory type (e.g., DECISION, ERROR_PATTERN).",
                        "enum": ["ERROR_PATTERN", "DECISION", "MILESTONE", "BUGFIX", "FEATURE", "CONFIG", "CODE_PATTERN", "GOTCHA", "PROGRESS"]
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memos_list",
            description="""List all memories in a project cube.

Use this to get an overview of what's been recorded for the project.
You can filter by memory type to find specific categories like decisions or errors.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'",
                        "default": MEMOS_DEFAULT_CUBE
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Filter by memory type (e.g., 'DECISION', 'ERROR_PATTERN')",
                        "enum": ["ERROR_PATTERN", "DECISION", "MILESTONE", "BUGFIX",
                                "FEATURE", "CONFIG", "CODE_PATTERN", "GOTCHA", "PROGRESS"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memories to return",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="memos_suggest",
            description="""Get smart suggestions for memory searches based on current context.

Use this when you're unsure what to search for. Provide the current context
(error message, code snippet, user question) and get relevant search suggestions.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "context": {
                        "type": "string",
                        "description": "Current context (error message, code, user question)"
                    }
                },
                "required": ["context"]
            }
        ),
        Tool(
            name="memos_list_cubes",
            description="""List all available memory cubes in the system.

USE THIS TOOL when:
- You encounter "cube not found" errors
- User asks which cubes are available
- You need to verify a cube exists before using it
- Starting a new project and want to see existing cubes

Returns:
- List of available cube IDs with their paths
- Registration status for each cube
- Helpful guidance if no cubes are found""",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_status": {
                        "type": "boolean",
                        "description": "Include registration status for each cube (requires API call)",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memos_get_stats",
            description="""Get statistics about memories in a project cube.
            
Use this to see how many memories of each type (DECISION, ERROR_PATTERN, etc.) are stored.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID (project name)",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                }
            }
        ),
        Tool(
            name="memos_trace_path",
            description="""Trace reasoning paths between two memory nodes.

USE THIS TOOL when you need to understand:
- How two concepts or events are connected
- The chain of causality or dependencies between memories
- Indirect relationships that span multiple hops

This is powerful for AI reasoning:
- "How did decision A lead to outcome B?"
- "What's the connection between error X and configuration Y?"
- "Trace the path from this bug to its root cause"

Returns:
- Whether a path exists between the two nodes
- Full path details with all intermediate nodes and edges
- The relationship types along the path (CAUSE, RELATE, CONDITION, etc.)

Example: Tracing from "Java not installed" to "API timeout error" might reveal:
  [Java not installed] ──CAUSE──> [Neo4j failed] ──CAUSE──> [DB connection lost] ──CAUSE──> [API timeout]""",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "ID of the source memory node to start from. Get this from memos_search or memos_get_graph."
                    },
                    "target_id": {
                        "type": "string",
                        "description": "ID of the target memory node to find path to. Get this from memos_search or memos_get_graph."
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum path length (hops). Default 3, max 10.",
                        "default": 3
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path.",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": ["source_id", "target_id"]
            }
        ),
        Tool(
            name="memos_get_graph",
            description="""Get memory knowledge graph with relationships.

USE THIS TOOL when you need to understand:
- How memories are connected (dependencies, causality)
- What caused a particular issue (CAUSE relationships)
- Related context around a topic (RELATE relationships)
- Conflicting information (CONFLICT relationships)

Returns:
- Memory nodes matching the query
- Relationships between memories: CAUSE, RELATE, CONFLICT, CONDITION

Example: If you search "Neo4j startup failure", you might see:
  [Java not installed] ──CAUSE──> [Neo4j failed to start]

This helps you understand the full context and dependencies.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find related memories and their relationships"
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'. Example: /mnt/g/test/MemOS → 'memos_cube', ~/my-app → 'my_app_cube'",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="memos_export_schema",
            description="""Export knowledge graph schema and statistics.

USE THIS TOOL when you need to understand:
- The overall structure of the project's memory graph
- What types of relationships exist in the knowledge base
- How well-connected the memories are
- The most common tags and memory types
- Time range of stored knowledge

This helps AI understand:
- What kind of information has been stored
- How memories relate to each other
- Whether there are gaps in the knowledge (orphan nodes)
- The overall health of the knowledge graph

Returns comprehensive statistics including:
- Total nodes and edges
- Relationship type distribution (CAUSE, RELATE, CONFLICT, etc.)
- Memory type distribution (LongTermMemory, WorkingMemory, etc.)
- Top 20 most frequent tags
- Average and max connections per node
- Number of orphan (unconnected) nodes
- Time range of data""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path.",
                        "default": MEMOS_DEFAULT_CUBE
                    },
                    "sample_size": {
                        "type": "integer",
                        "description": "Number of nodes to sample for analysis (10-1000). Default 100.",
                        "default": 100
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memos_register_cube",
            description="""Register a memory cube with the MemOS API.

USE THIS TOOL when you encounter:
- "MemCube 'xxx' is not loaded" error
- "Cube not registered" error
- After API restart when cubes need re-registration

This is the FALLBACK mechanism when auto-registration fails.

Steps to register:
1. First use memos_list_cubes() to find available cubes
2. Call this tool with the cube_id you want to register
3. Retry the original operation

The tool will:
1. Find the cube's full path from the cubes directory
2. Send registration request to MemOS API
3. Return success or detailed error message""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "ID of the cube to register (e.g., 'dev_cube', 'my_project_cube')"
                    },
                    "cube_path": {
                        "type": "string",
                        "description": "Optional: Full path to cube directory. If not provided, will be auto-detected from MEMOS_CUBES_DIR."
                    }
                },
                "required": ["cube_id"]
            }
        ),
        Tool(
            name="memos_create_user",
            description="""Create a user in MemOS.

USE THIS TOOL when you encounter:
- "User 'xxx' does not exist" error
- "User not found" error

This creates the user account needed to store and retrieve memories.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to create (e.g., 'dev_user')",
                        "default": MEMOS_USER
                    },
                    "user_name": {
                        "type": "string",
                        "description": "Display name for the user. Defaults to user_id if not provided."
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memos_validate_cubes",
            description="""Validate all cube configurations and fix namespace mismatches.

USE THIS TOOL to:
- Check if cube configs have correct user_name (should match cube_id)
- Auto-fix mismatched user_name in configs
- Detect cubes that may write to wrong namespace

This prevents the issue where memories are saved to wrong namespace
(e.g., saving to 'dev_user' instead of 'my_project_cube').

Returns:
- List of all cubes with their validation status
- Any fixes that were applied
- Warnings for potential issues""",
            inputSchema={
                "type": "object",
                "properties": {
                    "fix": {
                        "type": "boolean",
                        "description": "If true, automatically fix mismatched configs. Default: true",
                        "default": True
                    }
                },
                "required": []
            }
        )
    ]

    # Conditionally add delete tool if enabled (dangerous operation, disabled by default)
    if MEMOS_ENABLE_DELETE:
        tools.append(
            Tool(
                name="memos_delete",
                description="""⚠️ DELETE memories from project memory. USE WITH CAUTION!

This tool is DISABLED by default. User must explicitly enable it via MEMOS_ENABLE_DELETE=true.

ONLY use this tool when the user EXPLICITLY requests deletion.
NEVER use this tool proactively or without user confirmation.

Operations:
- Delete a single memory by ID
- Delete multiple memories by IDs
- Delete ALL memories in a cube (requires delete_all=true)

Before deleting, always:
1. Confirm with the user what will be deleted
2. Show the memory content that will be deleted
3. Get explicit user approval""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "ID of the specific memory to delete. Get this from memos_search or memos_list."
                        },
                        "memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of memory IDs to delete in batch."
                        },
                        "cube_id": {
                            "type": "string",
                            "description": "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'",
                            "default": MEMOS_DEFAULT_CUBE
                        },
                        "delete_all": {
                            "type": "boolean",
                            "description": "Set to true to delete ALL memories in the cube. DANGEROUS! Requires explicit user confirmation.",
                            "default": False
                        }
                    },
                    "required": []
                }
            )
        )
        logger.info("Delete tool enabled (MEMOS_ENABLE_DELETE=true)")

    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    # Use shared HTTP client for connection reuse
    client = await get_http_client()

    try:
        # Handle memos_list_cubes first (doesn't need cube_id)
        if name == "memos_list_cubes":
            include_status = arguments.get("include_status", False)
            available = list_available_cubes()

            if not available:
                cubes_dir = MEMOS_CUBES_DIR
                if cubes_dir.endswith(MEMOS_DEFAULT_CUBE):
                    cubes_dir = os.path.dirname(cubes_dir)
                return [TextContent(
                    type="text",
                    text=f"## No cubes found\n\n"
                         f"Cubes directory: `{cubes_dir}`\n\n"
                         f"To create a new cube, use the MemOS web interface at {MEMOS_URL}/docs "
                         f"or create a cube directory with a config.json file."
                )]

            result = ["## Available Memory Cubes\n"]
            result.append(f"Cubes directory: `{MEMOS_CUBES_DIR}`\n")

            for cube in available:
                cube_id = cube["id"]
                cube_path = cube["path"]

                if include_status:
                    # Check if cube is loaded
                    is_loaded = await verify_cube_loaded(client, cube_id)
                    status = "loaded" if is_loaded else "not loaded"
                    result.append(f"- **{cube_id}**: `{cube_path}` ({status})")
                else:
                    result.append(f"- **{cube_id}**: `{cube_path}`")

            result.append(f"\n**Default cube**: `{MEMOS_DEFAULT_CUBE}`")
            result.append("\n*Use `memos_list_cubes(include_status=True)` to check registration status.*")
            return [TextContent(type="text", text="\n".join(result))]

        # Determine target cube_id (explicit > derived > default)
        arg_cube_id = arguments.get("cube_id")
        cube_id = arg_cube_id if arg_cube_id else get_default_cube_id()

        if name == "memos_search":
            raw_query = arguments.get("query", "")
            top_k = arguments.get("top_k", 10)
            mem_type, cleaned_query = parse_memory_type_prefix(raw_query)
            query = cleaned_query if cleaned_query else raw_query

            # Auto-register cube if needed (with helpful error message)
            reg_success, reg_error = await ensure_cube_registered(client, cube_id)
            if not reg_success:
                return [TextContent(type="text", text=f"## Cube Registration Failed\n\n{reg_error}")]

            success, data, status = await api_call_with_retry(
                client, "POST", f"{MEMOS_URL}/search", cube_id,
                json={
                    "user_id": MEMOS_USER,
                    "query": query,
                    "install_cube_ids": [cube_id],
                    "top_k": top_k
                }
            )

            if success and data:
                result_data = data.get("data", {})
                result_data = filter_memories_by_type(result_data, mem_type)
                keyword_query = cleaned_query if mem_type else query
                result_data = apply_keyword_rerank(result_data, keyword_query)
                formatted = format_memories_for_display(result_data)
                return [TextContent(type="text", text=formatted)]
            elif data:
                return [TextContent(type="text", text=f"Search failed: {data.get('message', 'Unknown error')}")]
            else:
                return [TextContent(type="text", text=f"API error: {status}")]

        elif name == "memos_search_context":
            raw_query = arguments.get("query", "")
            context = arguments.get("context", [])
            mem_type, cleaned_query = parse_memory_type_prefix(raw_query)
            query = cleaned_query if cleaned_query else raw_query

            # Auto-register cube if needed
            reg_success, reg_error = await ensure_cube_registered(client, cube_id)
            if not reg_success:
                return [TextContent(type="text", text=f"## Cube Registration Failed\n\n{reg_error}")]

            # Format context as chat_history for the API
            chat_history = []
            for msg in context[-10:]:  # Last 10 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    chat_history.append({"role": role, "content": content})

            response = await client.post(
                f"{MEMOS_URL}/search",
                json={
                    "user_id": MEMOS_USER,
                    "query": query,
                    "readable_cube_ids": [cube_id],
                    "enable_context_analysis": True,
                    "chat_history": chat_history,
                    "top_k": 15,
                }
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    results = []
                    results.append("## 🔍 Context-Aware Search Results")
                    results.append("")
                    result_data = data.get("data", {})
                    result_data = filter_memories_by_type(result_data, mem_type)
                    keyword_query = cleaned_query if mem_type else query
                    result_data = apply_keyword_rerank(result_data, keyword_query)
                    formatted = format_memories_for_display(result_data)
                    if context:
                        results.append(f"*Analyzed with {len(context)} context messages*")
                        results.append("")
                    results.append(formatted)
                    return [TextContent(type="text", text="\n".join(results))]
                else:
                    # Fallback to standard search
                    fallback_response = await client.post(
                        f"{MEMOS_URL}/search",
                        json={
                            "user_id": MEMOS_USER,
                            "query": query,
                            "install_cube_ids": [cube_id]
                        }
                    )
                    if fallback_response.status_code == 200:
                        fallback_data = fallback_response.json()
                        if fallback_data.get("code") == 200:
                            result_data = fallback_data.get("data", {})
                            result_data = filter_memories_by_type(result_data, mem_type)
                            keyword_query = cleaned_query if mem_type else query
                            result_data = apply_keyword_rerank(result_data, keyword_query)
                            formatted = format_memories_for_display(result_data)
                            return [TextContent(type="text", text=f"## Search Results (fallback)\n\n{formatted}")]
                    return [TextContent(type="text", text=f"Search failed: {data.get('message', 'Unknown error')}")]
            else:
                return [TextContent(type="text", text=f"API error: {response.status_code}")]

        elif name == "memos_save":
            content = arguments.get("content", "")
            explicit_type = arguments.get("memory_type")

            # 检测类型和置信度
            if explicit_type:
                memory_type = explicit_type
                confidence = 1.0
            else:
                memory_type, confidence = detect_memory_type(content)

            # 低置信度警告
            warning = ""
            if confidence < 0.6 and memory_type == "PROGRESS":
                warning = (
                    f"\n\n⚠️ **类型检测置信度低** (confidence: {confidence:.0%}) - "
                    "建议显式指定 `memory_type` 参数以提高图谱质量。\n"
                    "可选类型: ERROR_PATTERN, BUGFIX, DECISION, GOTCHA, CODE_PATTERN, CONFIG, FEATURE, MILESTONE"
                )

            # Prepend memory type if not already present
            if not content.startswith(f"[{memory_type}]"):
                content = f"[{memory_type}] {content}"

            # Auto-register cube if needed
            reg_success, reg_error = await ensure_cube_registered(client, cube_id)
            if not reg_success:
                return [TextContent(type="text", text=f"## Cube Registration Failed\n\n{reg_error}")]

            success, data, status = await api_call_with_retry(
                client, "POST", f"{MEMOS_URL}/memories", cube_id,
                json={
                    "user_id": MEMOS_USER,
                    "mem_cube_id": cube_id,
                    "memory_content": content
                }
            )

            if success:
                return [TextContent(type="text", text=f"✅ Memory saved as [{memory_type}] (confidence: {confidence:.0%}){warning}")]
            elif data:
                return [TextContent(type="text", text=f"Save failed: {data.get('message', 'Unknown error')}")]
            else:
                return [TextContent(type="text", text=f"API error: {status}")]

        elif name in ("memos_list", "memos_list_v2"):
            limit = arguments.get("limit", 20)
            memory_type = arguments.get("memory_type")

            # Auto-register cube
            reg_success, reg_error = await ensure_cube_registered(client, cube_id)
            if not reg_success:
                return [TextContent(type="text", text=f"## Cube Registration Failed\n\n{reg_error}")]

            params = {
                "user_id": MEMOS_USER,
                "mem_cube_id": cube_id,
                "limit": limit
            }
            if memory_type:
                params["memory_type"] = memory_type

            success, data, status = await api_call_with_retry(
                client, "GET", f"{MEMOS_URL}/memories", cube_id,
                params=params
            )

            if success and data:
                formatted = format_memories_for_display(data.get("data", {}))
                return [TextContent(type="text", text=formatted)]
            elif data:
                return [TextContent(type="text", text=f"List failed: {data.get('message', 'Unknown error')}")]
            else:
                return [TextContent(type="text", text=f"API error: {status}")]

        elif name == "memos_suggest":
            context = arguments.get("context", "")
            suggestions = suggest_search_queries(context)

            if suggestions:
                result = ["## 🔍 Suggested Searches\n"]
                result.append("Based on your context, try these searches:\n")
                for i, suggestion in enumerate(suggestions, 1):
                    result.append(f"{i}. `{suggestion}`")
                return [TextContent(type="text", text="\n".join(result))]
            else:
                return [TextContent(type="text", text="No specific suggestions. Try searching with keywords from your context.")]

        elif name == "memos_get_stats":
            # Auto-register cube if needed
            reg_success, reg_error = await ensure_cube_registered(client, cube_id)
            if not reg_success:
                return [TextContent(type="text", text=f"## Cube Registration Failed\n\n{reg_error}")]

            success, data, status = await api_call_with_retry(
                client, "GET", f"{MEMOS_URL}/memories", cube_id,
                params={"user_id": MEMOS_USER, "mem_cube_id": cube_id}
            )

            if success and data:
                # Use helper function to compute stats
                stats, total = compute_memory_stats(data.get("data", {}))

                if not stats:
                    return [TextContent(type="text", text=f"No memories found in cube '{cube_id}'.")]

                result = [f"## 📊 Memory Stats: {cube_id}"]
                result.append(f"Total Memories: **{total}**\n")
                for mtype, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / total) * 100
                    result.append(f"- **{mtype}**: {count} ({percentage:.1f}%)")

                # 健康检查: PROGRESS 占比过高警告
                progress_count = stats.get("PROGRESS", 0)
                if total > 0 and progress_count / total > 0.7:
                    result.append("")
                    result.append("---")
                    result.append("")
                    result.append(f"⚠️ **健康警告**: PROGRESS 类型占比过高 (>{progress_count / total:.0%})")
                    result.append("")
                    result.append("这可能导致 Neo4j 知识图谱无法建立有效关系。建议:")
                    result.append("1. 保存记忆时**显式指定** `memory_type` 参数")
                    result.append("2. 参考类型选择决策树:")
                    result.append("   - 修复 Bug → `BUGFIX` 或 `ERROR_PATTERN`")
                    result.append("   - 技术决策 → `DECISION`")
                    result.append("   - 发现陷阱 → `GOTCHA`")
                    result.append("   - 新功能 → `FEATURE`")
                    result.append("   - 配置变更 → `CONFIG`")

                return [TextContent(type="text", text="\n".join(result))]
            elif data:
                return [TextContent(type="text", text=f"Stats failed: {data.get('message', 'Unknown error')}")]
            else:
                return [TextContent(type="text", text=f"API error: {status}")]

        elif name == "memos_trace_path":
            source_id = arguments.get("source_id", "")
            target_id = arguments.get("target_id", "")
            max_depth = min(arguments.get("max_depth", 3), 10)

            if not source_id or not target_id:
                return [TextContent(type="text", text="❌ Both source_id and target_id are required.")]

            # Auto-register cube if needed
            reg_success, reg_error = await ensure_cube_registered(client, cube_id)
            if not reg_success:
                return [TextContent(type="text", text=f"## Cube Registration Failed\n\n{reg_error}")]

            # Call the trace_path API endpoint
            try:
                response = await client.post(
                    f"{MEMOS_URL}/graph/trace_path",
                    json={
                        "user_id": MEMOS_USER,
                        "source_id": source_id,
                        "target_id": target_id,
                        "max_depth": max_depth,
                        "include_all_paths": False,
                        "mem_cube_id": cube_id,
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        trace_data = data.get("data", {})
                        found = trace_data.get("found", False)
                        paths = trace_data.get("paths", [])
                        source_node = trace_data.get("source", {})
                        target_node = trace_data.get("target", {})

                        results = []
                        results.append("## 🔗 Path Trace Results")
                        results.append("")

                        if source_node:
                            source_mem = source_node.get("memory", "")[:80]
                            results.append(f"**Source**: {source_mem}...")
                        if target_node:
                            target_mem = target_node.get("memory", "")[:80]
                            results.append(f"**Target**: {target_mem}...")
                        results.append("")

                        if not found:
                            results.append(f"*No path found within {max_depth} hops.*")
                            results.append("")
                            results.append("Suggestions:")
                            results.append("- Try increasing max_depth (up to 10)")
                            results.append("- Verify the node IDs are correct")
                            results.append("- The nodes may not be connected in the graph")
                        else:
                            for i, path in enumerate(paths, 1):
                                length = path.get("length", 0)
                                nodes = path.get("nodes", [])
                                edges = path.get("edges", [])

                                results.append(f"### Path {i} (Length: {length})")
                                results.append("")
                                results.append("```")

                                for j, node in enumerate(nodes):
                                    node_mem = node.get("memory", "")[:60]
                                    results.append(f"[{j+1}] {node_mem}...")

                                    if j < len(edges):
                                        edge = edges[j]
                                        edge_type = edge.get("type", "UNKNOWN")
                                        results.append("    │")
                                        results.append(f"    └── {edge_type} ──>")

                                results.append("```")
                                results.append("")

                        return [TextContent(type="text", text="\n".join(results))]
                    else:
                        return [TextContent(type="text", text=f"Trace path failed: {data.get('message', 'Unknown error')}")]
                else:
                    return [TextContent(type="text", text=f"API error: {response.status_code}")]

            except Exception as e:
                logger.warning(f"Falling back to direct Neo4j query: {e}")

                if not NEO4J_HTTP_URL or not NEO4J_USER or not NEO4J_PASSWORD:
                    return [TextContent(type="text", text="Neo4j fallback requires NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD in .env")]

                neo4j_auth = (NEO4J_USER, NEO4J_PASSWORD)

                cypher_query = f"""
                MATCH (source:Memory), (target:Memory)
                WHERE source.id = $source_id AND target.id = $target_id
                MATCH path = shortestPath((source)-[*1..{max_depth}]-(target))
                RETURN [n IN nodes(path) | {{id: n.id, memory: n.memory}}] AS nodes,
                       [r IN relationships(path) | {{type: type(r)}}] AS rels
                LIMIT 1
                """

                neo4j_response = await client.post(
                    NEO4J_HTTP_URL,
                    json={
                        "statements": [{
                            "statement": cypher_query,
                            "parameters": {"source_id": source_id, "target_id": target_id}
                        }]
                    },
                    auth=neo4j_auth
                )

                results = ["## 🔗 Path Trace (Direct Query)"]
                results.append("")

                if neo4j_response.status_code == 200:
                    neo4j_data = neo4j_response.json()
                    rows = neo4j_data.get("results", [{}])[0].get("data", [])

                    if rows:
                        row = rows[0].get("row", [[], []])
                        nodes = row[0] if len(row) > 0 else []
                        rels = row[1] if len(row) > 1 else []

                        results.append("```")
                        for j, node in enumerate(nodes):
                            node_mem = (node.get("memory") or "")[:60]
                            results.append(f"[{j+1}] {node_mem}...")
                            if j < len(rels):
                                rel_type = rels[j].get("type", "?")
                                results.append(f"    └── {rel_type} ──>")
                        results.append("```")
                    else:
                        results.append(f"*No path found within {max_depth} hops.*")
                else:
                    results.append(f"*Neo4j query error: {neo4j_response.status_code}*")

                return [TextContent(type="text", text="\n".join(results))]

        elif name == "memos_get_graph":
            query = arguments.get("query", "")

            # Auto-register cube if needed
            reg_success, reg_error = await ensure_cube_registered(client, cube_id)
            if not reg_success:
                return [TextContent(type="text", text=f"## Cube Registration Failed\n\n{reg_error}")]

            if not NEO4J_HTTP_URL or not NEO4J_USER or not NEO4J_PASSWORD:
                return [TextContent(type="text", text="Neo4j query requires NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD in .env")]

            neo4j_auth = (NEO4J_USER, NEO4J_PASSWORD)

            # First search for relevant memories using MemOS API
            search_response = await client.post(
                f"{MEMOS_URL}/search",
                json={
                    "user_id": MEMOS_USER,
                    "query": query,
                    "install_cube_ids": [cube_id]
                }
            )

            # Use helper to extract memories (handles tree_text mode)
            memories = []
            if search_response.status_code == 200:
                data = search_response.json()
                if data.get("code") == 200:
                    memories = extract_memories_from_response(data.get("data", {}))
                else:
                    # Try to re-register and search again
                    _registered_cubes.discard(cube_id)
                    retry_success, _ = await ensure_cube_registered(client, cube_id, force=True)
                    if retry_success:
                        retry_search = await client.post(
                            f"{MEMOS_URL}/search",
                            json={
                                "user_id": MEMOS_USER,
                                "query": query,
                                "install_cube_ids": [cube_id]
                            }
                        )
                        if retry_search.status_code == 200:
                            retry_data = retry_search.json()
                            if retry_data.get("code") == 200:
                                memories = extract_memories_from_response(retry_data.get("data", {}))

            # Query Neo4j for all CAUSE/RELATE/CONFLICT relationships
            cypher_query = """
            MATCH (a)-[r:CAUSE|RELATE|CONFLICT|CONDITION]->(b)
            WHERE a.memory CONTAINS $keyword OR b.memory CONTAINS $keyword
            RETURN a.id as source_id, a.memory as source_memory,
                   type(r) as relation_type,
                   b.id as target_id, b.memory as target_memory
            LIMIT 20
            """

            neo4j_response = await client.post(
                NEO4J_HTTP_URL,
                json={
                    "statements": [{
                        "statement": cypher_query,
                        "parameters": {"keyword": query}
                    }]
                },
                auth=neo4j_auth
            )

            results = []
            results.append(f"## 🧠 Knowledge Graph: {cube_id}")
            results.append(f"Query: `{query}`")
            results.append("")

            # Display memories from search
            if memories:
                results.append("### 📝 Related Memories")
                results.append("")
                for i, mem in enumerate(memories[:5], 1):
                    memory = mem.get("memory", "")
                    first_line = memory.split("\n")[0][:100]
                    results.append(f"{i}. {first_line}")
                results.append("")

            # Display relationships from Neo4j
            if neo4j_response.status_code == 200:
                neo4j_data = neo4j_response.json()
                rows = neo4j_data.get("results", [{}])[0].get("data", [])

                if rows:
                    results.append("### 🔗 Relationships")
                    results.append("```")
                    for row in rows:
                        r = row.get("row", [])
                        if len(r) >= 5:
                            source_mem = (r[1] or "")[:50]
                            rel_type = r[2]
                            target_mem = (r[4] or "")[:50]

                            if rel_type == "CAUSE":
                                arrow = "──CAUSE──>"
                            elif rel_type == "RELATE":
                                arrow = "──RELATE──"
                            elif rel_type == "CONFLICT":
                                arrow = "══CONFLICT══"
                            else:
                                arrow = f"──{rel_type}──>"

                            results.append(f"[{source_mem}...]")
                            results.append(f"    {arrow}")
                            results.append(f"[{target_mem}...]")
                            results.append("")
                    results.append("```")
                else:
                    results.append("*No relationships found for this query.*")
            else:
                results.append(f"*Neo4j query error: {neo4j_response.status_code}*")

            return [TextContent(type="text", text="\n".join(results))]

        elif name == "memos_export_schema":
            sample_size = min(max(arguments.get("sample_size", 100), 10), 1000)

            # Auto-register cube if needed
            reg_success, reg_error = await ensure_cube_registered(client, cube_id)
            if not reg_success:
                return [TextContent(type="text", text=f"## Cube Registration Failed\n\n{reg_error}")]

            try:
                response = await client.post(
                    f"{MEMOS_URL}/graph/schema",
                    json={
                        "user_id": MEMOS_USER,
                        "mem_cube_id": cube_id,
                        "sample_size": sample_size,
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        schema = data.get("data", {})

                        results = []
                        results.append("## 📊 Knowledge Graph Schema")
                        results.append("")

                        # Overview
                        results.append("### Overview")
                        results.append(f"- **Total Nodes**: {schema.get('total_nodes', 0)}")
                        results.append(f"- **Total Edges**: {schema.get('total_edges', 0)}")
                        results.append(f"- **Avg Connections/Node**: {schema.get('avg_connections_per_node', 0):.2f}")
                        results.append(f"- **Max Connections**: {schema.get('max_connections', 0)}")
                        results.append(f"- **Orphan Nodes**: {schema.get('orphan_node_count', 0)}")
                        results.append("")

                        # Time range
                        time_range = schema.get("time_range", {})
                        if time_range.get("earliest") or time_range.get("latest"):
                            results.append("### Time Range")
                            if time_range.get("earliest"):
                                results.append(f"- Earliest: {time_range['earliest']}")
                            if time_range.get("latest"):
                                results.append(f"- Latest: {time_range['latest']}")
                            results.append("")

                        # Edge types
                        edge_dist = schema.get("edge_type_distribution", {})
                        if edge_dist:
                            results.append("### Relationship Types")
                            for edge_type, count in sorted(edge_dist.items(), key=lambda x: x[1], reverse=True):
                                results.append(f"- **{edge_type}**: {count}")
                            results.append("")

                        # Memory types
                        mem_dist = schema.get("memory_type_distribution", {})
                        if mem_dist:
                            results.append("### Memory Types")
                            for mem_type, count in sorted(mem_dist.items(), key=lambda x: x[1], reverse=True):
                                results.append(f"- {mem_type}: {count}")
                            results.append("")

                        # Top tags
                        tag_freq = schema.get("tag_frequency", {})
                        if tag_freq:
                            results.append("### Top Tags")
                            tag_items = list(tag_freq.items())[:10]
                            for tag, count in tag_items:
                                results.append(f"- `{tag}`: {count}")
                            results.append("")

                        # Health assessment
                        results.append("### Health Assessment")
                        total_nodes = schema.get("total_nodes", 0)
                        orphan_count = schema.get("orphan_node_count", 0)
                        if total_nodes > 0:
                            orphan_ratio = orphan_count / total_nodes
                            if orphan_ratio > 0.5:
                                results.append("⚠️ High orphan ratio - many memories are not connected")
                            elif orphan_ratio > 0.2:
                                results.append("📋 Moderate orphan ratio - some memories could benefit from more connections")
                            else:
                                results.append("✅ Good connectivity - memories are well connected")

                        avg_conn = schema.get("avg_connections_per_node", 0)
                        if avg_conn < 1:
                            results.append("⚠️ Low average connections - consider enriching relationships")
                        elif avg_conn > 5:
                            results.append("✅ Rich relationships - good knowledge graph density")

                        return [TextContent(type="text", text="\n".join(results))]
                    else:
                        return [TextContent(type="text", text=f"Schema export failed: {data.get('message', 'Unknown error')}")]
                else:
                    return [TextContent(type="text", text=f"API error: {response.status_code}")]

            except Exception as e:
                logger.error(f"Schema export error: {e}")
                return [TextContent(type="text", text=f"Schema export error: {e!s}")]

        elif name == "memos_delete":
            # Safety check - only allow if explicitly enabled
            if not MEMOS_ENABLE_DELETE:
                return [TextContent(type="text", text="❌ Delete functionality is DISABLED. Set MEMOS_ENABLE_DELETE=true in environment to enable.")]

            memory_id = arguments.get("memory_id")
            memory_ids = arguments.get("memory_ids", [])
            delete_all = arguments.get("delete_all", False)

            # Collect all IDs to delete
            ids_to_delete = []
            if memory_id:
                ids_to_delete.append(memory_id)
            if memory_ids:
                ids_to_delete.extend(memory_ids)

            # Auto-register cube
            reg_success, reg_error = await ensure_cube_registered(client, cube_id)
            if not reg_success:
                return [TextContent(type="text", text=f"## Cube Registration Failed\n\n{reg_error}")]

            if delete_all:
                # Delete ALL memories - very dangerous!
                response = await client.delete(
                    f"{MEMOS_URL}/memories/{cube_id}",
                    params={"user_id": MEMOS_USER}
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        return [TextContent(type="text", text=f"⚠️ **ALL memories deleted** from cube: `{cube_id}`")]
                    else:
                        return [TextContent(type="text", text=f"❌ **Delete all failed**: {data.get('message', 'Unknown error')}")]
                else:
                    return [TextContent(type="text", text=f"❌ **API error** during delete all: {response.status_code}")]

            elif ids_to_delete:
                # Delete single or multiple memories
                results = []
                for mid in ids_to_delete:
                    # Optional: Try to fetch memory first to confirm it exists and show content
                    try:
                        get_resp = await client.get(
                            f"{MEMOS_URL}/memories/{cube_id}/{mid}",
                            params={"user_id": MEMOS_USER}
                        )
                        mem_content = "*(Unknown content)*"
                        if get_resp.status_code == 200:
                            g_data = get_resp.json()
                            if g_data.get("code") == 200 and g_data.get("data"):
                                # Extract memory text from the node
                                mem_node = g_data.get("data")
                                if isinstance(mem_node, dict):
                                    mem_content = mem_node.get("memory", mem_content)
                    except Exception:
                        mem_content = "*(Fetch failed)*"

                    response = await client.delete(
                        f"{MEMOS_URL}/memories/{cube_id}/{mid}",
                        params={"user_id": MEMOS_USER}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if data.get("code") == 200:
                            results.append(f"✅ Deleted: `{mid}`\n   > {mem_content[:150]}...")
                        else:
                            results.append(f"❌ Failed: `{mid}` ({data.get('message', 'Unknown error')})")
                    else:
                        results.append(f"❌ API Error: `{mid}` (Status: {response.status_code})")

                return [TextContent(type="text", text="\n".join(results))]

            else:
                return [TextContent(type="text", text="❌ Must provide either `memory_id`, `memory_ids` or `delete_all=true`")]

        elif name == "memos_register_cube":
            # Manual cube registration - fallback when auto-registration fails
            cube_id = arguments.get("cube_id")
            cube_path = arguments.get("cube_path")

            if not cube_id:
                return [TextContent(type="text", text="❌ `cube_id` is required")]

            # If path not provided, try to find it
            if not cube_path:
                cube_path = get_cube_path(cube_id)
                if not cube_path:
                    # List available cubes as helpful hint
                    available = list_available_cubes()
                    hint = ""
                    if available:
                        hint = "\n\n**Available cubes:**\n" + "\n".join([f"- `{c['id']}`" for c in available])
                    return [TextContent(
                        type="text",
                        text=f"❌ Cube `{cube_id}` not found in cubes directory.\n\n"
                             f"Cubes directory: `{get_cubes_base_dir()}`{hint}"
                    )]

            try:
                response = await client.post(
                    f"{MEMOS_URL}/mem_cubes",
                    json={
                        "user_id": MEMOS_USER,
                        "mem_cube_name_or_path": cube_path,
                        "mem_cube_id": cube_id
                    },
                    timeout=MEMOS_TIMEOUT_TOOL
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        _registered_cubes.add(cube_id)
                        return [TextContent(
                            type="text",
                            text=f"✅ **Cube registered successfully!**\n\n"
                                 f"- Cube ID: `{cube_id}`\n"
                                 f"- Path: `{cube_path}`\n\n"
                                 f"You can now use this cube with other memos_* tools."
                        )]
                    else:
                        error_msg = data.get("message", "Unknown error")
                        # Provide helpful hints based on error
                        hint = ""
                        if "reranker" in error_msg.lower():
                            hint = "\n\n**Hint**: Edit the cube's config.json and change `reranker.backend` to `http_bge` or `noop`."
                        elif "user" in error_msg.lower():
                            hint = "\n\n**Hint**: Use `memos_create_user` tool to create the user first."
                        return [TextContent(type="text", text=f"❌ Registration failed: {error_msg}{hint}")]
                else:
                    return [TextContent(type="text", text=f"❌ API error: HTTP {response.status_code}")]

            except Exception as e:
                return [TextContent(type="text", text=f"❌ Registration error: {str(e)}")]

        elif name == "memos_create_user":
            # Create user in MemOS
            user_id = arguments.get("user_id", MEMOS_USER)
            user_name = arguments.get("user_name", user_id)

            try:
                response = await client.post(
                    f"{MEMOS_URL}/users",
                    json={
                        "user_name": user_name,
                        "user_id": user_id,
                        "role": "USER"
                    },
                    timeout=MEMOS_TIMEOUT_TOOL
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        return [TextContent(
                            type="text",
                            text=f"✅ **User created successfully!**\n\n"
                                 f"- User ID: `{user_id}`\n"
                                 f"- User Name: `{user_name}`\n\n"
                                 f"You can now register cubes and store memories."
                        )]
                    else:
                        error_msg = data.get("message", "Unknown error")
                        # Check if user already exists
                        if "exist" in error_msg.lower():
                            return [TextContent(type="text", text=f"ℹ️ User `{user_id}` already exists. You can proceed with cube registration.")]
                        return [TextContent(type="text", text=f"❌ User creation failed: {error_msg}")]
                else:
                    return [TextContent(type="text", text=f"❌ API error: HTTP {response.status_code}")]

            except Exception as e:
                return [TextContent(type="text", text=f"❌ User creation error: {str(e)}")]

        elif name == "memos_validate_cubes":
            # Validate all cube configurations
            fix_issues = arguments.get("fix", True)
            cubes_dir = get_cubes_base_dir()

            if not cubes_dir or not os.path.isdir(cubes_dir):
                return [TextContent(type="text", text=f"❌ Cubes directory not found: {cubes_dir}")]

            results = ["## 🔍 Cube Configuration Validation\n"]
            fixed_count = 0
            error_count = 0
            ok_count = 0

            try:
                for cube_name in os.listdir(cubes_dir):
                    cube_path = os.path.join(cubes_dir, cube_name)
                    config_path = os.path.join(cube_path, "config.json")

                    if not os.path.isdir(cube_path) or not os.path.isfile(config_path):
                        continue

                    # Read and check config
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = json.load(f)

                        issues = []

                        # Check cube_id
                        if config.get("cube_id") != cube_name:
                            issues.append(f"cube_id: `{config.get('cube_id')}` → `{cube_name}`")

                        # Check graph_db user_name
                        text_cfg = config.get("text_mem", {}).get("config", {})
                        graph_cfg = text_cfg.get("graph_db", {}).get("config", {})
                        current_user_name = graph_cfg.get("user_name")

                        if current_user_name and current_user_name != cube_name:
                            issues.append(f"user_name: `{current_user_name}` → `{cube_name}`")

                        if issues:
                            if fix_issues:
                                was_fixed, error = validate_and_fix_cube_config(cube_name, config_path)
                                if was_fixed:
                                    results.append(f"- **{cube_name}**: ✅ Fixed - {', '.join(issues)}")
                                    fixed_count += 1
                                elif error:
                                    results.append(f"- **{cube_name}**: ❌ Error - {error}")
                                    error_count += 1
                            else:
                                results.append(f"- **{cube_name}**: ⚠️ Issues - {', '.join(issues)}")
                                error_count += 1
                        else:
                            results.append(f"- **{cube_name}**: ✅ OK")
                            ok_count += 1

                    except Exception as e:
                        results.append(f"- **{cube_name}**: ❌ Error reading config - {e}")
                        error_count += 1

                # Summary
                results.append(f"\n### Summary")
                results.append(f"- ✅ OK: {ok_count}")
                if fixed_count > 0:
                    results.append(f"- 🔧 Fixed: {fixed_count}")
                if error_count > 0:
                    results.append(f"- ⚠️ Issues: {error_count}")

                if fixed_count > 0:
                    results.append(f"\n**Note:** Fixed cubes need API restart to take effect for existing loaded cubes.")

                return [TextContent(type="text", text="\n".join(results))]

            except Exception as e:
                return [TextContent(type="text", text=f"❌ Validation error: {str(e)}")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except httpx.ConnectError:
        return [TextContent(type="text", text=f"❌ Cannot connect to MemOS API at {MEMOS_URL}. Is the server running?")]
    except Exception as e:
        logger.exception("Tool call failed")
        return [TextContent(type="text", text=f"Error: {e!s}")]


async def run_server():
    """Run the MCP server."""
    # Log timeout configuration
    logger.info(f"Timeout config: tool={MEMOS_TIMEOUT_TOOL}s, startup={MEMOS_TIMEOUT_STARTUP}s, health={MEMOS_TIMEOUT_HEALTH}s, api_wait={MEMOS_API_WAIT_MAX}s")

    # Wait for MemOS API to be ready before starting
    api_ready = await wait_for_api_ready()

    if api_ready:
        # Pre-register default cube at startup with retry
        async with httpx.AsyncClient(timeout=MEMOS_TIMEOUT_STARTUP) as client:
            for attempt in range(3):
                try:
                    reg_success, reg_error = await ensure_cube_registered(client, MEMOS_DEFAULT_CUBE, force=True)
                    if reg_success:
                        logger.info(f"Startup: Default cube '{MEMOS_DEFAULT_CUBE}' ready")
                        break
                    else:
                        logger.warning(f"Startup: Cube registration attempt {attempt + 1} failed: {reg_error}")
                        await asyncio.sleep(2.0)
                except Exception as e:
                    logger.warning(f"Startup: Registration attempt {attempt + 1} error: {e}")
                    await asyncio.sleep(2.0)
    else:
        logger.warning("Startup: API not ready, will try to register cube on first tool call")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Entry point."""
    # Log configuration at startup
    logger.info("MemOS MCP Server starting...")
    logger.info(f"  MEMOS_URL: {MEMOS_URL}")
    logger.info(f"  MEMOS_USER: {MEMOS_USER}")
    logger.info(f"  MEMOS_DEFAULT_CUBE: {MEMOS_DEFAULT_CUBE}")
    logger.info(f"  MEMOS_ENABLE_DELETE: {MEMOS_ENABLE_DELETE}")
    logger.info(f"  MEMOS_TIMEOUT_TOOL: {MEMOS_TIMEOUT_TOOL}s")
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
