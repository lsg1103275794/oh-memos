#!/usr/bin/env python3
"""Shared utilities for MemOS scripts with cross-platform support."""

import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path, PureWindowsPath, PurePosixPath
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from typing import Optional, Tuple

# Configuration
MEMOS_URL = os.environ.get("MEMOS_URL", "http://localhost:18000")
DEFAULT_USER = os.environ.get("MEMOS_USER", "dev_user")
CUBES_DIR = os.environ.get("MEMOS_CUBES_DIR", os.path.expanduser("~/.memos_cubes"))

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
            with open("/proc/version", "r") as f:
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
    """
    env = detect_environment()
    path = str(path)

    if env == "wsl":
        # WSL -> Need Windows path for Windows-based API
        if path.startswith("/mnt/") or path.startswith("/home/"):
            return wsl_to_windows_path(path)

    # For Windows or if path is already Windows-style
    if re.match(r'^[a-zA-Z]:', path):
        return path.replace("\\", "/")  # Use forward slashes for JSON

    return path


def check_api_health() -> Tuple[bool, str]:
    """Check if MemOS API is accessible."""
    try:
        req = Request(f"{MEMOS_URL}/docs", method="GET")
        with urlopen(req, timeout=5) as resp:
            return True, "API is running"
    except HTTPError as e:
        if e.code == 200:
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

        with urlopen(req, timeout=30) as resp:
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


def ensure_cube_registered(project: str, user: str = DEFAULT_USER) -> Tuple[bool, str]:
    """Ensure a cube is registered, auto-register if needed."""
    # Try to access the cube first
    test_result = api_request("/search", {
        "user_id": user,
        "query": "test",
        "install_cube_ids": [project]
    })

    # If cube is accessible, we're good
    if test_result.get("code") == 200:
        return True, "Cube already registered"

    # Check if error is about cube not being loaded
    error_msg = test_result.get("message", "")
    if "not loaded" not in error_msg.lower() and "not have access" not in error_msg.lower():
        return False, f"Unexpected error: {error_msg}"

    # Try to register the cube
    cube_path = Path(CUBES_DIR) / project

    if not cube_path.exists():
        return False, f"Cube config not found: {cube_path}. Run memos-init first."

    # Normalize path for API
    api_path = normalize_path_for_api(str(cube_path))

    register_result = api_request("/mem_cubes", {
        "user_id": user,
        "mem_cube_name_or_path": api_path,
        "mem_cube_id": project
    })

    if register_result.get("code") == 200:
        return True, f"Cube registered: {project}"
    else:
        return False, f"Failed to register cube: {register_result.get('message')}"


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


# For backward compatibility
def create_cube_config(project: str, cube_path: Path) -> dict:
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
                        "model_name_or_path": os.environ.get("MOS_EMBEDDER_MODEL", "nomic-embed-text"),
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
