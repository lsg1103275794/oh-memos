#!/usr/bin/env python3
"""Search memories in MemOS with cross-platform support."""

import argparse
import json
import os
import sys

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


def search_memories(query: str, project: str = None, user: str = DEFAULT_USER,
                    mem_type: str = None, limit: int = 10, cube_id: str = None) -> dict:
    """Search memories via MemOS API.

    Args:
        query: Search query
        project: Project name (for reference)
        user: User ID
        mem_type: Optional memory type filter
        limit: Max results (not currently used by API)
        cube_id: Resolved cube ID (full path). If provided, uses this instead of project.
    """
    payload = {
        "user_id": user,
        "query": query
    }

    # Use resolved cube_id if provided, otherwise fall back to project name
    actual_cube_id = cube_id or project
    if actual_cube_id:
        payload["install_cube_ids"] = [actual_cube_id]

    # Add type filter to query if specified
    if mem_type:
        payload["query"] = f"[{mem_type}] {query}"

    return api_request("/search", payload)


def get_memory_type_icon(mem_type: str) -> str:
    """Get icon for memory type."""
    icons = {
        "MILESTONE": "✅",
        "BUGFIX": "🐛",
        "FEATURE": "✨",
        "DECISION": "🏗️",
        "GOTCHA": "⚠️",
        "CONFIG": "⚙️",
        "PROGRESS": "📊",
        "ERROR_PATTERN": "🔴",
        "CODE_PATTERN": "📦",
        "DECISION_CHAIN": "🔗",
        "KNOWLEDGE": "📚"
    }
    return icons.get(mem_type, "📝")


def detect_memory_type(memory_text: str) -> str:
    """Detect memory type from text content."""
    for mem_type in MEMORY_TYPES:
        if f"[{mem_type}]" in memory_text:
            return mem_type
    return "UNKNOWN"


def format_results(result: dict, compact: bool = False) -> str:
    """Format search results for display."""
    if result.get("code") != 200:
        return f"Error: {result.get('message')}"

    data = result.get("data", {})
    text_mem = data.get("text_mem", [])

    if not text_mem:
        return "No memories found."

    output = []
    total_count = 0

    for cube in text_mem:
        cube_id = cube.get("cube_id", "unknown")
        memories = cube.get("memories", [])

        if memories:
            total_count += len(memories)
            output.append(f"\n{'='*50}")
            output.append(f"  Project: {cube_id} ({len(memories)} memories)")
            output.append(f"{'='*50}\n")

            for i, mem in enumerate(memories, 1):
                memory_text = mem.get("memory", "")
                mem_id = mem.get("id", "")[:8] if mem.get("id") else "?"
                score = mem.get("score", 0)

                # Detect memory type
                mem_type = detect_memory_type(memory_text)
                icon = get_memory_type_icon(mem_type)

                if compact:
                    # Compact view: first line only
                    first_line = memory_text.split('\n')[0][:80]
                    output.append(f"{icon} [{i}] {first_line}...")
                else:
                    # Full view
                    output.append(f"{icon} [{i}] ID: {mem_id}... | Score: {score:.2f}")
                    output.append("-" * 40)
                    output.append(memory_text)
                    output.append("")

    if total_count > 0:
        output.insert(0, f"Found {total_count} memories:\n")

    return "\n".join(output) if output else "No memories found."


def main():
    parser = argparse.ArgumentParser(
        description="Search memories in MemOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Search Examples:
  memos-search "authentication"              # Search current project
  memos-search "redis" -p my-api             # Search specific project
  memos-search "error connection" --all      # Search all projects
  memos-search "decision" -t DECISION        # Filter by type
  memos-search "pattern" -t ERROR_PATTERN    # Search error patterns

Memory Type Filters:
  MILESTONE, BUGFIX, FEATURE, DECISION, GOTCHA, CONFIG, PROGRESS
  ERROR_PATTERN, CODE_PATTERN, DECISION_CHAIN, KNOWLEDGE
        """
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument("-p", "--project", default=None,
                        help="Project name to search in (auto-detected if not specified)")
    parser.add_argument("-u", "--user", default=DEFAULT_USER,
                        help="User ID")
    parser.add_argument("-t", "--type", default=None, choices=MEMORY_TYPES,
                        help="Filter by memory type")
    parser.add_argument("--all", action="store_true",
                        help="Search all projects")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON")
    parser.add_argument("--compact", "-c", action="store_true",
                        help="Compact output (first line only)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    parser.add_argument("--auto-register", action="store_true", default=True,
                        help="Auto-register cube if not found (default: True)")
    parser.add_argument("--no-auto-register", action="store_false", dest="auto_register",
                        help="Disable auto-registration")

    args = parser.parse_args()

    project = None if args.all else (args.project or get_project_name())

    if args.verbose:
        print_info(f"Query: {args.query}")
        print_info(f"Project: {project or 'all'}")
        print_info(f"User: {args.user}")
        if args.type:
            print_info(f"Type filter: {args.type}")
        print_info(f"API: {MEMOS_URL}")
        print()

    # Ensure cube is registered (if searching specific project)
    cube_id = None
    if project and args.auto_register:
        success, msg = ensure_cube_registered(project, args.user)
        if args.verbose:
            print_status(success, f"Cube registration: {msg}")
        if not success and "not found" in msg.lower():
            print_warning(f"Cube not found. Run 'memos-init -p {project}' first.")
            # Continue anyway, API will return appropriate error

        # Resolve cube ID (maps project name to full path if needed)
        cube_id = resolve_cube_id(project, args.user)
        if args.verbose and cube_id != project:
            print_info(f"Resolved cube ID: {cube_id}")

    # Search
    result = search_memories(args.query, project, args.user, args.type, cube_id=cube_id)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_results(result, compact=args.compact))

    return 0 if result.get("code") == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
