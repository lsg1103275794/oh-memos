#!/usr/bin/env python3
"""Save a memory to MemOS with proper formatting."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

MEMOS_URL = os.environ.get("MEMOS_URL", "http://localhost:18000")
DEFAULT_USER = os.environ.get("MEMOS_USER", "dev_user")


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


def save_memory(content: str, mem_type: str, project: str, user: str, tags: list[str] = None):
    """Save memory to MemOS API."""
    date = datetime.now().strftime("%Y-%m-%d")
    tags_str = ", ".join(tags) if tags else mem_type.lower()

    formatted_content = f"""[{mem_type.upper()}] Project: {project} | Date: {date}

{content}

Tags: {tags_str}"""

    payload = {
        "user_id": user,
        "mem_cube_id": project,
        "memory_content": formatted_content
    }

    try:
        req = Request(
            f"{MEMOS_URL}/memories",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result
    except URLError as e:
        return {"code": 500, "message": f"Connection error: {e}", "data": None}


def main():
    parser = argparse.ArgumentParser(description="Save memory to MemOS")
    parser.add_argument("content", help="Memory content to save")
    parser.add_argument("-t", "--type", default="PROGRESS",
                        choices=["MILESTONE", "BUGFIX", "FEATURE", "DECISION", "GOTCHA", "CONFIG", "PROGRESS"],
                        help="Memory type")
    parser.add_argument("-p", "--project", default=None, help="Project name (auto-detected from git)")
    parser.add_argument("-u", "--user", default=DEFAULT_USER, help="User ID")
    parser.add_argument("--tags", nargs="+", default=None, help="Additional tags")

    args = parser.parse_args()
    project = args.project or get_project_name()

    result = save_memory(args.content, args.type, project, args.user, args.tags)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get("code") == 200:
        print(f"\n✓ Memory saved to project: {project}")
        return 0
    else:
        print(f"\n✗ Failed to save memory: {result.get('message')}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
