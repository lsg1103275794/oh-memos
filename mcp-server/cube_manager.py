#!/usr/bin/env python3
"""
MemOS MCP Server Cube Management Module

Contains all cube management functions for listing, registering, and configuring memory cubes.
"""

import json
import os
import re
import time

from typing import Any

import httpx

from config import (
    KEYWORD_ENHANCER_AVAILABLE,
    MEMOS_CUBES_DIR,
    MEMOS_DEFAULT_CUBE,
    MEMOS_URL,
    MEMOS_USER,
    REGISTRATION_RETRY_INTERVAL,
    _last_registration_attempt,
    _registered_cubes,
    detect_cube_from_path,
    is_default_cube_from_env,
    logger,
)


# ============================================================================
# Cube Discovery Functions
# ============================================================================

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
    """Get the base directory containing all cubes."""
    cubes_dir = MEMOS_CUBES_DIR
    if cubes_dir.endswith(MEMOS_DEFAULT_CUBE):
        return os.path.dirname(cubes_dir)
    return cubes_dir


# ============================================================================
# Cube Configuration Functions
# ============================================================================

def _clone_config(config: dict[str, Any]) -> dict[str, Any]:
    """Deep clone a configuration dictionary."""
    return json.loads(json.dumps(config))


def _update_config_for_cube(config: dict[str, Any], cube_id: str) -> dict[str, Any]:
    """Update config values to match the given cube_id."""
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
    """Build a cube config from environment variables when no template is available."""
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
    """Build a cube config, using template from default cube if available."""
    template_path = get_cube_path(MEMOS_DEFAULT_CUBE)
    if template_path is not None:
        config_path = os.path.join(template_path, "config.json")
        try:
            with open(config_path, encoding="utf-8") as f:
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
        with open(config_path, encoding="utf-8") as f:
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
            logger.debug(f"Fixed cube config for '{cube_id}': {', '.join(issues)}")

        return modified, None
    except Exception as e:
        return False, f"Failed to validate cube config: {e}"


def ensure_cube_directory(cube_id: str) -> tuple[str | None, str | None]:
    """
    Ensure cube directory exists with valid config.

    Returns:
        (cube_dir, error_message)
    """
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
    if is_default_cube_from_env():
        cube_path = get_cube_path(MEMOS_DEFAULT_CUBE)
        if cube_path is not None:
            return MEMOS_DEFAULT_CUBE
    try:
        cwd = os.getcwd()
        # Use enhanced detection if available
        if KEYWORD_ENHANCER_AVAILABLE and detect_cube_from_path is not None:
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


# ============================================================================
# Cube Registration Functions
# ============================================================================

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
            logger.debug(f"Cube '{cube_id}' already loaded")
            return True, None

        # Check if the cube path exists before trying to register
        cube_path = get_cube_path(cube_id)
        if cube_path is None:
            # Cube doesn't exist - try to auto-create it
            logger.debug(f"Cube '{cube_id}' not found, attempting auto-creation...")

            # Check if we have a template cube to clone from
            template_path = get_cube_path(MEMOS_DEFAULT_CUBE)
            if template_path is None:
                # No template available - cannot auto-create
                available = list_available_cubes()
                available_ids = [c["id"] for c in available]

                if available_ids:
                    error_msg = (
                        f"Cube '{cube_id}' not found and no template cube available for auto-creation. "
                        f"Available cubes: {available_ids}. "
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

            # Auto-create the cube directory with config cloned from template
            cube_path, create_error = ensure_cube_directory(cube_id)
            if cube_path is None:
                error_msg = f"Failed to auto-create cube '{cube_id}': {create_error}"
                logger.error(error_msg)
                return False, error_msg

            logger.debug(f"Auto-created cube '{cube_id}' at {cube_path}")

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
                logger.debug(f"Auto-registered cube: {cube_id}")
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
