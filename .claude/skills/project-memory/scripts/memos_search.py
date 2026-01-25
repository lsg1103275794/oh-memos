#!/usr/bin/env python3
"""Search memories in MemOS."""

import argparse
import json
import os
import subprocess
import sys
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


def search_memories(query: str, project: str = None, user: str = DEFAULT_USER):
    """Search memories via MemOS API."""
    payload = {
        "user_id": user,
        "query": query
    }
    if project:
        payload["install_cube_ids"] = [project]

    try:
        req = Request(
            f"{MEMOS_URL}/search",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        return {"code": 500, "message": f"Connection error: {e}", "data": None}


def format_results(result: dict) -> str:
    """Format search results for display."""
    if result.get("code") != 200:
        return f"Error: {result.get('message')}"

    data = result.get("data", {})
    text_mem = data.get("text_mem", [])

    if not text_mem:
        return "No memories found."

    output = []
    for cube in text_mem:
        cube_id = cube.get("cube_id", "unknown")
        memories = cube.get("memories", [])

        if memories:
            output.append(f"\n=== Project: {cube_id} ({len(memories)} memories) ===\n")
            for i, mem in enumerate(memories, 1):
                memory_text = mem.get("memory", "")
                mem_id = mem.get("id", "")[:8]
                output.append(f"--- [{i}] ID: {mem_id}... ---")
                output.append(memory_text)
                output.append("")

    return "\n".join(output) if output else "No memories found."


def main():
    parser = argparse.ArgumentParser(description="Search memories in MemOS")
    parser.add_argument("query", help="Search query")
    parser.add_argument("-p", "--project", default=None,
                        help="Project name to search in (auto-detected if not specified)")
    parser.add_argument("-u", "--user", default=DEFAULT_USER, help="User ID")
    parser.add_argument("--all", action="store_true", help="Search all projects")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    project = None if args.all else (args.project or get_project_name())
    result = search_memories(args.query, project, args.user)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_results(result))

    return 0 if result.get("code") == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
