#!/usr/bin/env python3
"""
MemOS MCP Server - Intelligent Memory Management for Claude Code

This MCP server provides tools for Claude to proactively search and save
project memories, enabling intelligent context-aware assistance.
"""

import asyncio
import json
import logging
import os
import re
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memos-mcp")

# Configuration
MEMOS_URL = os.environ.get("MEMOS_URL", "http://localhost:18000")
MEMOS_USER = os.environ.get("MEMOS_USER", "dev_user")
MEMOS_DEFAULT_CUBE = os.environ.get("MEMOS_DEFAULT_CUBE", "dev_cube")
MEMOS_CUBES_DIR = os.environ.get("MEMOS_CUBES_DIR", "G:/test/MemOS/data/memos_cubes")

# Create server instance
server = Server("memos-memory")

# Track registered cubes to avoid repeated registration attempts
_registered_cubes: set[str] = set()


async def ensure_cube_registered(client: httpx.AsyncClient, cube_id: str) -> bool:
    """Ensure cube is registered, auto-register if needed. Returns True if successful."""
    if cube_id in _registered_cubes:
        return True

    try:
        # Try to register the cube
        cube_path = f"{MEMOS_CUBES_DIR}/{cube_id}"
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
                return True
            # Already registered is also success
            if "already" in data.get("message", "").lower():
                _registered_cubes.add(cube_id)
                return True
    except Exception as e:
        logger.warning(f"Failed to auto-register cube {cube_id}: {e}")

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
        memories = cube_data.get("memories", [])

        if memories:
            results.append(f"## 📦 Cube: {cube_id}")
            results.append("")

            for i, mem in enumerate(memories, 1):
                memory_text = mem.get("memory", "")
                metadata = mem.get("metadata", {})
                mem_id = mem.get("id", "")[:8]

                # Extract first line as title
                first_line = memory_text.split("\n")[0][:100]

                results.append(f"### {i}. {first_line}")
                results.append(f"ID: `{mem_id}...`")
                results.append("")
                results.append(memory_text)
                results.append("")
                results.append("---")
                results.append("")

    if not results:
        return "No memories found matching your query."

    return "\n".join(results)


def detect_memory_type(content: str) -> str:
    """Automatically detect memory type from content."""
    content_lower = content.lower()

    # Pattern matching for memory types
    patterns = {
        "ERROR_PATTERN": [r"error", r"exception", r"bug", r"fix", r"解决", r"错误"],
        "DECISION": [r"decision", r"decided", r"decide", r"决策", r"选择", r"方案", r"architecture", r"chose", r"选用"],
        "MILESTONE": [r"milestone", r"完成", r"release", r"发布", r"achieved"],
        "BUGFIX": [r"bugfix", r"fixed", r"修复", r"patch"],
        "FEATURE": [r"feature", r"新增", r"implement", r"add"],
        "CONFIG": [r"config", r"配置", r"setting", r"environment"],
        "CODE_PATTERN": [r"pattern", r"模式", r"template", r"snippet"],
        "GOTCHA": [r"gotcha", r"注意", r"warning", r"caveat", r"陷阱"],
    }

    for mem_type, keywords in patterns.items():
        for keyword in keywords:
            if re.search(keyword, content_lower):
                return mem_type

    return "PROGRESS"


def suggest_search_queries(context: str) -> list[str]:
    """Suggest relevant search queries based on context."""
    suggestions = []
    context_lower = context.lower()

    # Error-related suggestions
    if any(word in context_lower for word in ["error", "exception", "failed", "错误"]):
        # Try to extract error type
        error_match = re.search(r"(\w+Error|\w+Exception)", context)
        if error_match:
            suggestions.append(f"ERROR_PATTERN {error_match.group(1)}")
        suggestions.append("ERROR_PATTERN solution")

    # Config-related suggestions
    if any(word in context_lower for word in ["config", "setting", "env", "配置"]):
        suggestions.append("CONFIG environment")

    # Decision-related suggestions
    if any(word in context_lower for word in ["why", "为什么", "decision", "选择"]):
        suggestions.append("DECISION architecture")

    return suggestions[:3]  # Return top 3 suggestions


# Define MCP Tools

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
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
                        "description": "Memory cube ID (project name). Defaults to current project.",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="memos_save",
            description="""Save important information to project memory.

USE THIS TOOL when:
- You've solved a bug or error (save as ERROR_PATTERN with solution)
- A significant decision was made (save as DECISION with rationale)
- You've completed a major task (save as MILESTONE)
- You discovered a non-obvious gotcha (save as GOTCHA)
- You created a reusable code pattern (save as CODE_PATTERN)
- Configuration was changed (save as CONFIG)

Memory types:
- ERROR_PATTERN: Error signature + solution for future reference
- DECISION: Architectural or design choice with rationale
- MILESTONE: Significant project achievement
- BUGFIX: Bug fix with cause and solution
- FEATURE: New functionality added
- CONFIG: Environment or configuration change
- CODE_PATTERN: Reusable code template
- GOTCHA: Non-obvious issue or workaround
- PROGRESS: General progress update""",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Memory content to save. Be detailed - include context, rationale, and relevant code/commands."
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Type of memory (auto-detected if not specified)",
                        "enum": ["ERROR_PATTERN", "DECISION", "MILESTONE", "BUGFIX",
                                "FEATURE", "CONFIG", "CODE_PATTERN", "GOTCHA", "PROGRESS"],
                        "default": "PROGRESS"
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID (project name). Defaults to current project.",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="memos_list",
            description="""List all memories in a project cube.

Use this to get an overview of what's been recorded for the project.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID (project name)",
                        "default": MEMOS_DEFAULT_CUBE
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
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if name == "memos_search":
                query = arguments.get("query", "")
                cube_id = arguments.get("cube_id", MEMOS_DEFAULT_CUBE)

                # Auto-register cube if needed
                await ensure_cube_registered(client, cube_id)

                response = await client.post(
                    f"{MEMOS_URL}/search",
                    json={
                        "user_id": MEMOS_USER,
                        "query": query,
                        "install_cube_ids": [cube_id]
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        formatted = format_memories_for_display(data.get("data", {}))
                        return [TextContent(type="text", text=formatted)]
                    else:
                        return [TextContent(type="text", text=f"Search failed: {data.get('message', 'Unknown error')}")]
                else:
                    return [TextContent(type="text", text=f"API error: {response.status_code}")]

            elif name == "memos_save":
                content = arguments.get("content", "")
                memory_type = arguments.get("memory_type") or detect_memory_type(content)
                cube_id = arguments.get("cube_id", MEMOS_DEFAULT_CUBE)

                # Prepend memory type if not already present
                if not content.startswith(f"[{memory_type}]"):
                    content = f"[{memory_type}] {content}"

                # Auto-register cube if needed
                await ensure_cube_registered(client, cube_id)

                response = await client.post(
                    f"{MEMOS_URL}/memories",
                    json={
                        "user_id": MEMOS_USER,
                        "mem_cube_id": cube_id,
                        "memory_content": content
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        return [TextContent(type="text", text=f"✅ Memory saved successfully as [{memory_type}]")]
                    else:
                        return [TextContent(type="text", text=f"Save failed: {data.get('message', 'Unknown error')}")]
                else:
                    return [TextContent(type="text", text=f"API error: {response.status_code}")]

            elif name == "memos_list":
                cube_id = arguments.get("cube_id", MEMOS_DEFAULT_CUBE)
                limit = arguments.get("limit", 10)

                # Auto-register cube if needed
                await ensure_cube_registered(client, cube_id)

                response = await client.get(
                    f"{MEMOS_URL}/memories",
                    params={
                        "user_id": MEMOS_USER,
                        "mem_cube_id": cube_id
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        memories = data.get("data", {}).get("memories", [])[:limit]
                        if not memories:
                            return [TextContent(type="text", text="No memories found in this cube.")]

                        result = [f"## 📚 Memories in {cube_id} ({len(memories)} shown)\n"]
                        for i, mem in enumerate(memories, 1):
                            first_line = mem.get("memory", "").split("\n")[0][:80]
                            result.append(f"{i}. {first_line}")

                        return [TextContent(type="text", text="\n".join(result))]
                    else:
                        return [TextContent(type="text", text=f"List failed: {data.get('message', 'Unknown error')}")]
                else:
                    return [TextContent(type="text", text=f"API error: {response.status_code}")]

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

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except httpx.ConnectError:
            return [TextContent(type="text", text=f"❌ Cannot connect to MemOS API at {MEMOS_URL}. Is the server running?")]
        except Exception as e:
            logger.exception("Tool call failed")
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
