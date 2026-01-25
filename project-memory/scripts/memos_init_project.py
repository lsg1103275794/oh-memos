#!/usr/bin/env python3
"""Initialize a project memory cube in MemOS."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

MEMOS_URL = os.environ.get("MEMOS_URL", "http://localhost:18000")
DEFAULT_USER = os.environ.get("MEMOS_USER", "dev_user")
CUBES_DIR = os.environ.get("MEMOS_CUBES_DIR", os.path.expanduser("~/.memos_cubes"))


def get_project_name():
    """Get project name from git root or current directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True
        )
        return os.path.basename(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return os.path.basename(os.getcwd())


def create_cube_config(project: str, cube_path: Path) -> dict:
    """Create cube configuration."""
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


def register_cube(cube_path: str, project: str, user: str):
    """Register cube with MemOS API."""
    payload = {
        "user_id": user,
        "mem_cube_name_or_path": cube_path,
        "mem_cube_id": project
    }

    try:
        req = Request(
            f"{MEMOS_URL}/mem_cubes",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        return {"code": 500, "message": f"Connection error: {e}", "data": None}


def main():
    parser = argparse.ArgumentParser(description="Initialize project memory cube")
    parser.add_argument("-p", "--project", default=None, help="Project name (auto-detected from git)")
    parser.add_argument("-u", "--user", default=DEFAULT_USER, help="User ID")
    parser.add_argument("--cubes-dir", default=CUBES_DIR, help="Directory for cube configs")

    args = parser.parse_args()
    project = args.project or get_project_name()
    cube_path = Path(args.cubes_dir) / project

    # Create cube directory and config
    cube_path.mkdir(parents=True, exist_ok=True)
    config_file = cube_path / "config.json"

    if config_file.exists():
        print(f"Config already exists: {config_file}")
        response = input("Overwrite? [y/N]: ").strip().lower()
        if response != 'y':
            print("Aborted.")
            return 1

    config = create_cube_config(project, cube_path)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"Created config: {config_file}")

    # Register with MemOS
    result = register_cube(str(cube_path), project, args.user)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get("code") == 200:
        print(f"\n✓ Project '{project}' initialized successfully!")
        print(f"  Cube path: {cube_path}")
        print(f"\nYou can now save memories with:")
        print(f"  python memos_save.py 'Your memory content' -t MILESTONE")
        return 0
    else:
        print(f"\n✗ Failed to register cube: {result.get('message')}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
