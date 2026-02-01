#!/usr/bin/env python3
"""Shared utilities for MemOS scripts with cross-platform support."""

import json
import os
import platform
import re
import subprocess
import sys

from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# Configuration
MEMOS_URL = os.environ.get("MEMOS_URL") or os.environ.get("MEMOS_BASE_URL")
if not MEMOS_URL:
    raise RuntimeError("MEMOS_URL is required (set MEMOS_URL or MEMOS_BASE_URL in .env)")

DEFAULT_USER = os.environ.get("MEMOS_USER")
if not DEFAULT_USER:
    raise RuntimeError("MEMOS_USER is required (set MEMOS_USER in .env)")

CUBES_DIR = os.environ.get("MEMOS_CUBES_DIR")
if not CUBES_DIR:
    raise RuntimeError("MEMOS_CUBES_DIR is required (set MEMOS_CUBES_DIR in .env)")

# Cache file for cube ID mappings
CUBE_CACHE_FILE = os.path.expanduser("~/.memos_cube_cache.json")

# Memory types (including enhanced types)
MEMORY_TYPES = [
    "MILESTONE", "BUGFIX", "FEATURE", "DECISION", "GOTCHA", "CONFIG", "PROGRESS",
    "ERROR_PATTERN", "CODE_PATTERN", "DECISION_CHAIN", "KNOWLEDGE"
]


def detect_environment() -> str:
    """Detect the current environment."""
    system = platform.system().lower()

    # Check if running in WSL
    if system == "linux":
        try:
            with open("/proc/version") as f:
                if "microsoft" in f.read().lower():
                    return "wsl"
        except:
            pass
        return "linux"
    elif system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    return "unknown"


def wsl_to_windows_path(wsl_path: str) -> str:
    """Convert WSL path to Windows path.

    /mnt/c/Users/... -> C:/Users/...
    /home/user/... -> \\\\wsl$\\Ubuntu\\home\\user\\...
    """
    wsl_path = str(wsl_path)

    # Handle /mnt/X/... paths
    mnt_match = re.match(r'^/mnt/([a-zA-Z])(/.*)?$', wsl_path)
    if mnt_match:
        drive = mnt_match.group(1).upper()
        rest = mnt_match.group(2) or ""
        return f"{drive}:{rest}".replace("/", "\\")

    # Handle other paths (convert to UNC path)
    # Try to detect WSL distro name
    try:
        result = subprocess.run(
            ["wsl.exe", "-l", "-q"],
            capture_output=True, text=True, timeout=5
        )
        distro = result.stdout.strip().split("\n")[0].strip()
        if distro:
            return f"\\\\wsl$\\{distro}{wsl_path}".replace("/", "\\")
    except:
        pass

    # Fallback: assume Ubuntu
    return f"\\\\wsl$\\Ubuntu{wsl_path}".replace("/", "\\")


def windows_to_wsl_path(win_path: str) -> str:
    """Convert Windows path to WSL path.

    C:\\Users\\... -> /mnt/c/Users/...
    """
    win_path = str(win_path).replace("\\", "/")

    # Handle drive letter paths
    drive_match = re.match(r'^([a-zA-Z]):/(.*)$', win_path)
    if drive_match:
        drive = drive_match.group(1).lower()
        rest = drive_match.group(2)
        return f"/mnt/{drive}/{rest}"

    return win_path


def normalize_path_for_api(path: str) -> str:
    """Normalize path for MemOS API based on where API is running.

    MemOS API typically runs on Windows, so paths need to be Windows-style.
    Returns path with forward slashes for JSON compatibility.
    """
    env = detect_environment()
    path = str(path)

    if env == "wsl":
        # WSL -> Need Windows path for Windows-based API
        if path.startswith("/mnt/"):
            win_path = wsl_to_windows_path(path)
            return win_path.replace("\\", "/")  # Use forward slashes for JSON
        elif path.startswith("/home/") or path.startswith("/"):
            # Pure WSL paths - warn user
            print_warning(f"WSL path '{path}' may not work with Windows-based MemOS API")
            print_warning("Consider using /mnt/X/... format instead")

    # For Windows or if path is already Windows-style
    if re.match(r'^[a-zA-Z]:', path):
        return path.replace("\\", "/")  # Use forward slashes for JSON

    return path


# ============== Cube ID Management ==============

def load_cube_cache() -> dict[str, str]:
    """Load cube ID to full path mapping from cache."""
    try:
        if os.path.exists(CUBE_CACHE_FILE):
            with open(CUBE_CACHE_FILE) as f:
                return json.load(f)
    except:
        pass
    return {}


def save_cube_cache(cache: dict[str, str]):
    """Save cube ID to full path mapping to cache."""
    try:
        with open(CUBE_CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print_warning(f"Failed to save cube cache: {e}")


def update_cube_cache(cube_name: str, full_path: str):
    """Update cube cache with new mapping."""
    cache = load_cube_cache()
    cache[cube_name] = full_path
    # Also cache by the full path itself (for consistency)
    cache[full_path] = full_path
    save_cube_cache(cache)


def get_registered_cubes(user: str = DEFAULT_USER) -> list[dict]:
    """Get list of registered cubes by searching."""
    result = api_request("/search", {
        "user_id": user,
        "query": "*"
    })

    cubes = []
    if result.get("code") == 200:
        text_mem = result.get("data", {}).get("text_mem", [])
        for cube in text_mem:
            cube_id = cube.get("cube_id", "")
            if cube_id:
                cubes.append({
                    "cube_id": cube_id,
                    "name": os.path.basename(cube_id.rstrip("/\\")),
                    "memory_count": len(cube.get("memories", []))
                })
                # Update cache
                name = os.path.basename(cube_id.rstrip("/\\"))
                update_cube_cache(name, cube_id)
    return cubes


def resolve_cube_id(cube_name_or_path: str, user: str = DEFAULT_USER) -> str:
    """Resolve a cube name or path to the actual cube_id used by the API.

    The API uses full paths as cube IDs, so we need to:
    1. Check cache for known mapping
    2. Try common cube directories
    3. Fall back to the input if nothing found
    """
    # If it's already a full path with drive letter, normalize and return
    if re.match(r'^[a-zA-Z]:', cube_name_or_path):
        return cube_name_or_path.replace("\\", "/")

    # Check cache first
    cache = load_cube_cache()
    if cube_name_or_path in cache:
        return cache[cube_name_or_path]

    # Try to find the cube in common locations
    env = detect_environment()
    search_dirs = []

    if env == "wsl":
        # Search in both WSL and mounted Windows drives
        search_dirs = [
            "/mnt/g/test/MemOS/data/memos_cubes",
            "/mnt/g/test/MemOS/.memos_cubes",
            "/mnt/c/Users/*/memos_cubes",
            os.path.expanduser("~/.memos_cubes"),
            "./data/memos_cubes",
            "./.memos_cubes",
        ]
    else:
        search_dirs = [
            os.path.expanduser("~/.memos_cubes"),
            "./data/memos_cubes",
            "./.memos_cubes",
        ]

    for base_dir in search_dirs:
        # Handle glob patterns
        if "*" in base_dir:
            import glob
            for expanded in glob.glob(base_dir):
                cube_path = os.path.join(expanded, cube_name_or_path)
                if os.path.exists(cube_path):
                    full_path = normalize_path_for_api(os.path.abspath(cube_path))
                    update_cube_cache(cube_name_or_path, full_path)
                    return full_path
        else:
            cube_path = os.path.join(base_dir, cube_name_or_path)
            if os.path.exists(cube_path):
                full_path = normalize_path_for_api(os.path.abspath(cube_path))
                update_cube_cache(cube_name_or_path, full_path)
                return full_path

    # Try to get from API by searching
    result = api_request("/search", {"user_id": user, "query": cube_name_or_path})
    if result.get("code") == 200:
        text_mem = result.get("data", {}).get("text_mem", [])
        for cube in text_mem:
            cube_id = cube.get("cube_id", "")
            if cube_id and cube_name_or_path in cube_id:
                update_cube_cache(cube_name_or_path, cube_id)
                return cube_id

    # Last resort: return as-is
    return cube_name_or_path


# ============== API Functions ==============

def check_api_health() -> tuple[bool, str]:
    """Check if MemOS API is accessible."""
    try:
        req = Request(f"{MEMOS_URL}/users", method="GET")
        with urlopen(req, timeout=5) as resp:
            return True, "API is running"
    except HTTPError as e:
        if e.code < 500:
            return True, "API is running"
        return False, f"API returned error: {e.code}"
    except URLError as e:
        return False, f"Cannot connect to API: {e.reason}"
    except Exception as e:
        return False, f"Error: {e}"


def api_request(endpoint: str, payload: dict = None, method: str = "POST") -> dict:
    """Make API request with error handling."""
    try:
        url = f"{MEMOS_URL}{endpoint}"

        if payload:
            data = json.dumps(payload).encode("utf-8")
            req = Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
        else:
            req = Request(url, method=method)

        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        try:
            error_body = json.loads(e.read().decode("utf-8"))
            return {"code": e.code, "message": error_body.get("message", str(e)), "data": None}
        except:
            return {"code": e.code, "message": str(e), "data": None}
    except URLError as e:
        return {"code": 500, "message": f"Connection error: {e.reason}", "data": None}
    except Exception as e:
        return {"code": 500, "message": f"Error: {e}", "data": None}


def get_project_name() -> str:
    """Get project name from git root or current directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True
        )
        return os.path.basename(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return os.path.basename(os.getcwd())


def ensure_cube_registered(project: str, user: str = DEFAULT_USER) -> tuple[bool, str]:
    """Ensure a cube is registered, auto-register if needed.

    Returns (success, message) tuple.
    """
    # First, resolve the cube ID (handle name -> full path mapping)
    cube_id = resolve_cube_id(project, user)

    # Try to access the cube
    test_result = api_request("/search", {
        "user_id": user,
        "query": "test",
        "install_cube_ids": [cube_id]
    })

    # If cube is accessible, we're good
    if test_result.get("code") == 200:
        return True, f"Cube ready: {os.path.basename(cube_id)}"

    # Check if error is about cube not being loaded
    error_msg = test_result.get("message", "")
    if "not loaded" not in error_msg.lower() and "not have access" not in error_msg.lower():
        return False, f"Unexpected error: {error_msg}"

    # Try to register the cube
    # First, find the cube directory
    cube_path = None
    env = detect_environment()

    search_dirs = [
        os.path.join(CUBES_DIR, project),
        f"./data/memos_cubes/{project}",
        f"./.memos_cubes/{project}",
    ]

    if env == "wsl":
        search_dirs.extend([
            f"/mnt/g/test/MemOS/data/memos_cubes/{project}",
            f"/mnt/g/test/MemOS/.memos_cubes/{project}",
        ])

    for path in search_dirs:
        if os.path.exists(path):
            cube_path = path
            break

    if not cube_path:
        return False, f"Cube config not found for '{project}'. Run memos-init first."

    # Normalize path for API
    api_path = normalize_path_for_api(os.path.abspath(cube_path))

    register_result = api_request("/mem_cubes", {
        "user_id": user,
        "mem_cube_name_or_path": api_path
    })

    if register_result.get("code") == 200:
        # Update cache with the registered cube
        update_cube_cache(project, api_path)
        return True, f"Cube registered: {project}"
    else:
        return False, f"Failed to register cube: {register_result.get('message')}"


# ============== Output Helpers ==============

def print_status(success: bool, message: str):
    """Print status message with icon."""
    icon = "✓" if success else "✗"
    stream = sys.stdout if success else sys.stderr
    print(f"{icon} {message}", file=stream)


def print_info(message: str):
    """Print info message."""
    print(f"ℹ {message}")


def print_warning(message: str):
    """Print warning message."""
    print(f"⚠ {message}", file=sys.stderr)


# ============== Cube Configuration ==============

def create_cube_config(project: str, cube_path: Path = None) -> dict:
    """Create cube configuration with environment-based settings."""
    return {
        "model_schema": "memos.configs.mem_cube.GeneralMemCubeConfig",
        "user_id": DEFAULT_USER,
        "cube_id": project,
        "config_filename": "config.json",
        "text_mem": {
            "backend": "general_text",
            "config": {
                "cube_id": project,
                "memory_filename": "textual_memory.json",
                "extractor_llm": {
                    "backend": "openai",
                    "config": {
                        "model_name_or_path": os.environ.get("MOS_CHAT_MODEL", "gpt-4"),
                        "temperature": 0.6,
                        "max_tokens": 2048,
                        "api_key": os.environ.get("OPENAI_API_KEY", ""),
                        "api_base": os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
                    }
                },
                "vector_db": {
                    "backend": "qdrant",
                    "config": {
                        "collection_name": project,
                        "vector_dimension": int(os.environ.get("EMBEDDING_DIMENSION", 768)),
                        "distance_metric": "cosine",
                        "url": os.environ.get("QDRANT_URL", "http://localhost:6333"),
                        "api_key": os.environ.get("QDRANT_API_KEY", "")
                    }
                },
                "embedder": {
                    "backend": os.environ.get("MOS_EMBEDDER_BACKEND", "ollama"),
                    "config": {
                        "model_name_or_path": os.environ.get("MOS_EMBEDDER_MODEL", "nomic-embed-text-v2-moe:latest"),
                        "api_base": os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
                    }
                }
            }
        },
        "act_mem": {},
        "para_mem": {}
    }


if __name__ == "__main__":
    # Self-test
    print(f"Environment: {detect_environment()}")
    print(f"MEMOS_URL: {MEMOS_URL}")
    print(f"CUBES_DIR: {CUBES_DIR}")

    health, msg = check_api_health()
    print_status(health, f"API Health: {msg}")

    # Test path conversion
    if detect_environment() == "wsl":
        test_paths = [
            "/mnt/g/test/MemOS",
            "/home/user/.memos_cubes/test"
        ]
        print("\nPath conversion tests:")
        for p in test_paths:
            print(f"  {p} -> {wsl_to_windows_path(p)}")

    # Test cube resolution
    print("\nCube resolution:")
    print(f"  dev_cube -> {resolve_cube_id('dev_cube')}")

    # List registered cubes
    print("\nRegistered cubes:")
    cubes = get_registered_cubes()
    for cube in cubes:
        print(f"  - {cube['name']}: {cube['cube_id']} ({cube['memory_count']} memories)")
