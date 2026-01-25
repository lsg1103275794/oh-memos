#!/usr/bin/env python3
"""Initialize a project memory cube in MemOS."""

import argparse
import json
import os
import sys
from pathlib import Path

# Import shared utilities
try:
    from memos_utils import (
        MEMOS_URL, DEFAULT_USER, CUBES_DIR, MEMORY_TYPES,
        detect_environment, normalize_path_for_api, check_api_health,
        api_request, get_project_name, create_cube_config,
        update_cube_cache, print_status, print_info, print_warning
    )
except ImportError:
    # Fallback for direct execution
    import subprocess
    MEMOS_URL = os.environ.get("MEMOS_URL", "http://localhost:18000")
    DEFAULT_USER = os.environ.get("MEMOS_USER", "dev_user")
    CUBES_DIR = os.environ.get("MEMOS_CUBES_DIR", os.path.expanduser("~/.memos_cubes"))

    def get_project_name():
        try:
            result = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                    capture_output=True, text=True, check=True)
            return os.path.basename(result.stdout.strip())
        except:
            return os.path.basename(os.getcwd())

    def detect_environment():
        import platform
        return platform.system().lower()

    def normalize_path_for_api(path):
        return str(path)

    def check_api_health():
        return True, "Skipped"

    def api_request(endpoint, payload):
        from urllib.request import Request, urlopen
        req = Request(f"{MEMOS_URL}{endpoint}",
                      data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json"},
                      method="POST")
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def create_cube_config(project, cube_path):
        return {
            "model_schema": "memos.configs.mem_cube.GeneralMemCubeConfig",
            "user_id": DEFAULT_USER,
            "cube_id": project,
            "config_filename": "config.json",
            "text_mem": {"backend": "general_text", "config": {"cube_id": project, "memory_filename": "textual_memory.json"}}
        }

    def print_status(success, msg):
        print(f"{'✓' if success else '✗'} {msg}")

    def print_info(msg):
        print(f"ℹ {msg}")

    def print_warning(msg):
        print(f"⚠ {msg}")

    def update_cube_cache(cube_name, full_path):
        pass  # Fallback: no caching


def register_cube(cube_path: str, project: str, user: str) -> dict:
    """Register cube with MemOS API using normalized path."""
    # Normalize path for the API (handles WSL -> Windows conversion)
    api_path = normalize_path_for_api(cube_path)

    print_info(f"Registering cube with path: {api_path}")

    payload = {
        "user_id": user,
        "mem_cube_name_or_path": api_path,
        "mem_cube_id": project
    }

    return api_request("/mem_cubes", payload)


def main():
    parser = argparse.ArgumentParser(
        description="Initialize project memory cube",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  memos-init                    # Auto-detect project name from git
  memos-init -p my-project      # Specify project name
  memos-init --check            # Check API health only
        """
    )
    parser.add_argument("-p", "--project", default=None, help="Project name (auto-detected from git)")
    parser.add_argument("-u", "--user", default=DEFAULT_USER, help="User ID")
    parser.add_argument("--cubes-dir", default=CUBES_DIR, help="Directory for cube configs")
    parser.add_argument("--force", "-f", action="store_true", help="Overwrite existing config without asking")
    parser.add_argument("--check", action="store_true", help="Check API health and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Check API health
    if args.check or args.verbose:
        print_info(f"Environment: {detect_environment()}")
        print_info(f"API URL: {MEMOS_URL}")

        health, msg = check_api_health()
        print_status(health, f"API Health: {msg}")

        if args.check:
            return 0 if health else 1

        if not health:
            print_warning("API not available. Cube config will be created but not registered.")

    project = args.project or get_project_name()
    cube_path = Path(args.cubes_dir) / project

    print_info(f"Project: {project}")
    print_info(f"Cube path: {cube_path}")

    # Create cube directory and config
    cube_path.mkdir(parents=True, exist_ok=True)
    config_file = cube_path / "config.json"

    if config_file.exists() and not args.force:
        print_warning(f"Config already exists: {config_file}")
        try:
            response = input("Overwrite? [y/N]: ").strip().lower()
            if response != 'y':
                print("Aborted.")
                return 1
        except EOFError:
            print("\nUse --force to overwrite without asking.")
            return 1

    config = create_cube_config(project, cube_path)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print_status(True, f"Created config: {config_file}")

    # Register with MemOS
    result = register_cube(str(cube_path), project, args.user)

    if args.verbose:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get("code") == 200:
        # Cache the cube ID mapping for future use
        api_path = normalize_path_for_api(str(cube_path))
        update_cube_cache(project, api_path)

        print_status(True, f"Project '{project}' initialized successfully!")
        print()
        print("You can now save memories with:")
        print(f"  memos-save 'Your memory content' -t MILESTONE -p {project}")
        print()
        print("Or search memories with:")
        print(f"  memos-search 'query' -p {project}")
        return 0
    else:
        print_status(False, f"Failed to register cube: {result.get('message')}")
        print()
        print("Config file was created. You may need to:")
        print("  1. Ensure MemOS API is running at", MEMOS_URL)
        print("  2. Check that the path is accessible from the API server")
        print("  3. If using WSL, ensure the path is correctly converted")
        return 1


if __name__ == "__main__":
    sys.exit(main())
