#!/usr/bin/env python3
"""Save a memory to MemOS with proper formatting and cross-platform support."""

import argparse
import json
import os
import sys
from datetime import datetime

# Import shared utilities
try:
    from memos_utils import (
        MEMOS_URL, DEFAULT_USER, MEMORY_TYPES,
        api_request, get_project_name, ensure_cube_registered,
        resolve_cube_id, print_status, print_info, print_warning
    )
except ImportError:
    # Fallback for direct execution
    import subprocess
    MEMOS_URL = os.environ.get("MEMOS_URL", "http://localhost:18000")
    DEFAULT_USER = os.environ.get("MEMOS_USER", "dev_user")
    MEMORY_TYPES = [
        "MILESTONE", "BUGFIX", "FEATURE", "DECISION", "GOTCHA", "CONFIG", "PROGRESS",
        "ERROR_PATTERN", "CODE_PATTERN", "DECISION_CHAIN", "KNOWLEDGE"
    ]

    def get_project_name():
        try:
            result = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                    capture_output=True, text=True, check=True)
            return os.path.basename(result.stdout.strip())
        except:
            return os.path.basename(os.getcwd())

    def api_request(endpoint, payload):
        from urllib.request import Request, urlopen
        from urllib.error import URLError, HTTPError
        try:
            req = Request(f"{MEMOS_URL}{endpoint}",
                          data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"},
                          method="POST")
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

    def ensure_cube_registered(project, user):
        return True, "Skipped (fallback mode)"

    def resolve_cube_id(cube_name, user=None):
        return cube_name

    def print_status(success, msg):
        print(f"{'✓' if success else '✗'} {msg}")

    def print_info(msg):
        print(f"ℹ {msg}")

    def print_warning(msg):
        print(f"⚠ {msg}", file=sys.stderr)


def format_memory_content(content: str, mem_type: str, project: str, tags: list = None) -> str:
    """Format memory content with standard structure."""
    date = datetime.now().strftime("%Y-%m-%d")

    # Build tags string
    if tags:
        tags_str = ", ".join(tags)
    else:
        tags_str = mem_type.lower().replace("_", "-")

    # For enhanced types, use different header formats
    if mem_type in ["ERROR_PATTERN", "CODE_PATTERN", "DECISION_CHAIN"]:
        formatted = f"[{mem_type}] Project: {project} | Date: {date}\n\n{content}\n\nTags: {tags_str}"
    else:
        formatted = f"[{mem_type}] Project: {project} | Date: {date}\n\n{content}\n\nTags: {tags_str}"

    return formatted


def save_memory(content: str, mem_type: str, project: str, user: str, tags: list = None, cube_id: str = None) -> dict:
    """Save memory to MemOS API.

    Args:
        content: Memory content to save
        mem_type: Memory type (MILESTONE, BUGFIX, etc.)
        project: Project name (used for formatting)
        user: User ID
        tags: Optional tags
        cube_id: Resolved cube ID (full path). If None, uses project name.
    """
    formatted_content = format_memory_content(content, mem_type, project, tags)

    # Use resolved cube_id if provided, otherwise fall back to project name
    actual_cube_id = cube_id or project

    payload = {
        "user_id": user,
        "mem_cube_id": actual_cube_id,
        "memory_content": formatted_content
    }

    return api_request("/memories", payload)


def main():
    parser = argparse.ArgumentParser(
        description="Save memory to MemOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Memory Types:
  Standard:
    MILESTONE    - Significant achievement or completed phase
    BUGFIX       - Bug fix with solution details
    FEATURE      - New functionality implemented
    DECISION     - Architecture or design choice
    GOTCHA       - Non-obvious issue or workaround
    CONFIG       - Configuration change
    PROGRESS     - Status update or checkpoint

  Enhanced:
    ERROR_PATTERN   - Reusable error signature + solution
    CODE_PATTERN    - Reusable code template
    DECISION_CHAIN  - Decision evolution timeline
    KNOWLEDGE       - General project knowledge

Examples:
  memos-save "Fixed login redirect bug" -t BUGFIX
  memos-save "Chose PostgreSQL for ACID compliance" -t DECISION
  memos-save "Auth system complete with JWT" -t MILESTONE
  memos-save "ModuleNotFoundError fix for Windows" -t ERROR_PATTERN --tags error python windows
        """
    )
    parser.add_argument("content", help="Memory content to save")
    parser.add_argument("-t", "--type", default="PROGRESS",
                        choices=MEMORY_TYPES,
                        help="Memory type (default: PROGRESS)")
    parser.add_argument("-p", "--project", default=None,
                        help="Project name (auto-detected from git)")
    parser.add_argument("-u", "--user", default=DEFAULT_USER,
                        help="User ID")
    parser.add_argument("--tags", nargs="+", default=None,
                        help="Additional tags (space-separated)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON response")
    parser.add_argument("--auto-register", action="store_true", default=True,
                        help="Auto-register cube if not found (default: True)")
    parser.add_argument("--no-auto-register", action="store_false", dest="auto_register",
                        help="Disable auto-registration")

    args = parser.parse_args()
    project = args.project or get_project_name()

    if args.verbose:
        print_info(f"Project: {project}")
        print_info(f"User: {args.user}")
        print_info(f"Type: {args.type}")
        print_info(f"API: {MEMOS_URL}")

    # Ensure cube is registered
    if args.auto_register:
        success, msg = ensure_cube_registered(project, args.user)
        if args.verbose:
            print_status(success, f"Cube registration: {msg}")
        if not success and "not found" in msg.lower():
            print_warning(f"Cube not found. Run 'memos-init -p {project}' first.")
            return 1

    # Resolve cube ID (maps project name to full path if needed)
    cube_id = resolve_cube_id(project, args.user)
    if args.verbose:
        if cube_id != project:
            print_info(f"Resolved cube ID: {cube_id}")

    # Save memory
    result = save_memory(args.content, args.type, project, args.user, args.tags, cube_id)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.verbose:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get("code") == 200:
        print_status(True, f"Memory saved to project: {project}")
        if args.verbose:
            data = result.get("data") or {}
            mem_id = data.get("memory_id", "")
            if mem_id:
                print_info(f"Memory ID: {mem_id[:16]}...")
        return 0
    else:
        error_msg = result.get("message", "Unknown error")
        print_status(False, f"Failed to save memory: {error_msg}")

        # Provide helpful hints
        if "not loaded" in error_msg.lower() or "not have access" in error_msg.lower():
            print()
            print("Hint: The project cube may not be registered. Try:")
            print(f"  memos-init -p {project}")
        elif "connection" in error_msg.lower():
            print()
            print("Hint: Cannot connect to MemOS API. Check:")
            print(f"  1. MemOS is running at {MEMOS_URL}")
            print("  2. Network connectivity")

        return 1


if __name__ == "__main__":
    sys.exit(main())
