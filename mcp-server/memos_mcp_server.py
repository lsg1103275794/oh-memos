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


def format_graph_for_display(data: list) -> str:
    """Format knowledge graph results with relationships for readable display."""
    results = []

    for cube_data in data:
        cube_id = cube_data.get("cube_id", "unknown")
        memories_list = cube_data.get("memories", [])

        if not memories_list:
            continue

        results.append(f"## 🧠 Knowledge Graph: {cube_id}")
        results.append("")

        for mem_data in memories_list:
            # Extract nodes and edges
            nodes = mem_data.get("nodes", [])
            edges = mem_data.get("edges", [])

            # Build node lookup for relationship display
            node_lookup = {}
            for node in nodes:
                node_id = node.get("id", "")
                node_memory = node.get("memory", "")
                node_lookup[node_id] = node_memory[:80] + "..." if len(node_memory) > 80 else node_memory

            # Display nodes
            if nodes:
                results.append("### 📝 Memory Nodes")
                results.append("")
                for i, node in enumerate(nodes[:10], 1):  # Limit to 10 nodes
                    memory = node.get("memory", "")
                    first_line = memory.split("\n")[0][:100]
                    node_id = node.get("id", "")[:8]
                    results.append(f"{i}. **{first_line}**")
                    results.append(f"   ID: `{node_id}...`")
                    results.append("")

            # Display relationships - THIS IS THE KEY PART
            if edges:
                results.append("### 🔗 Relationships (CAUSE/RELATE/CONFLICT)")
                results.append("")
                results.append("```")
                for edge in edges:
                    source_id = edge.get("source", "")
                    target_id = edge.get("target", "")
                    rel_type = edge.get("type", "UNKNOWN")

                    # Skip PARENT relationships, only show semantic ones
                    if rel_type == "PARENT":
                        continue

                    source_text = node_lookup.get(source_id, source_id[:8])[:50]
                    target_text = node_lookup.get(target_id, target_id[:8])[:50]

                    # Format relationship with arrow
                    if rel_type == "CAUSE":
                        arrow = "──CAUSE──>"
                    elif rel_type == "RELATE":
                        arrow = "──RELATE──"
                    elif rel_type == "CONFLICT":
                        arrow = "══CONFLICT══"
                    elif rel_type == "CONDITION":
                        arrow = "──CONDITION──>"
                    else:
                        arrow = f"──{rel_type}──"

                    results.append(f"[{source_text}]")
                    results.append(f"    {arrow}")
                    results.append(f"[{target_text}]")
                    results.append("")

                results.append("```")
                results.append("")

        results.append("---")

    if not results:
        return "No memories or relationships found."

    return "\n".join(results)


def detect_memory_type(content: str) -> str:
    """Automatically detect memory type from content."""
    content_lower = content.lower()

    # Pattern matching for memory types (Chinese + English)
    patterns = {
        "ERROR_PATTERN": [r"error", r"exception", r"bug", r"fix", r"解决", r"错误", r"报错", r"失败"],
        "DECISION": [r"decision", r"decided", r"decide", r"决策", r"选择", r"方案", r"architecture", r"chose", r"选用", r"优化方案", r"optimization"],
        "MILESTONE": [r"milestone", r"完成", r"release", r"发布", r"achieved", r"里程碑", r"搞定"],
        "BUGFIX": [r"bugfix", r"fixed", r"修复", r"patch", r"修好"],
        "FEATURE": [r"feature", r"新增", r"implement", r"add", r"功能", r"新功能"],
        "CONFIG": [r"config", r"配置", r"setting", r"environment", r"环境变量", r"\.env"],
        "CODE_PATTERN": [r"pattern", r"模式", r"template", r"snippet", r"代码模板"],
        "GOTCHA": [r"gotcha", r"注意", r"warning", r"caveat", r"陷阱", r"小心", r"坑", r"当心"],
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
    if any(word in context_lower for word in ["error", "exception", "failed", "错误", "报错", "失败"]):
        # Try to extract error type
        error_match = re.search(r"(\w+Error|\w+Exception)", context)
        if error_match:
            suggestions.append(f"ERROR_PATTERN {error_match.group(1)}")
        suggestions.append("ERROR_PATTERN solution")

    # Config-related suggestions
    if any(word in context_lower for word in ["config", "setting", "env", "配置", "环境"]):
        suggestions.append("CONFIG environment")

    # Decision-related suggestions
    if any(word in context_lower for word in ["why", "为什么", "decision", "选择", "决定", "优化"]):
        suggestions.append("DECISION architecture")

    # Gotcha-related suggestions
    if any(word in context_lower for word in ["注意", "warning", "careful", "小心", "坑"]):
        suggestions.append("GOTCHA warning")

    # History-related suggestions
    if any(word in context_lower for word in ["之前", "上次", "previously", "last time", "earlier"]):
        suggestions.append("PROGRESS history")

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
        ),
        Tool(
            name="memos_get_graph",
            description="""Get memory knowledge graph with relationships.

USE THIS TOOL when you need to understand:
- How memories are connected (dependencies, causality)
- What caused a particular issue (CAUSE relationships)
- Related context around a topic (RELATE relationships)
- Conflicting information (CONFLICT relationships)

Returns:
- Memory nodes matching the query
- Relationships between memories: CAUSE, RELATE, CONFLICT, CONDITION

Example: If you search "Neo4j startup failure", you might see:
  [Java not installed] ──CAUSE──> [Neo4j failed to start]

This helps you understand the full context and dependencies.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find related memories and their relationships"
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID (project name). Defaults to current project.",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": ["query"]
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

            elif name == "memos_get_graph":
                query = arguments.get("query", "")
                cube_id = arguments.get("cube_id", MEMOS_DEFAULT_CUBE)

                # Auto-register cube if needed
                await ensure_cube_registered(client, cube_id)

                # Query Neo4j directly for relationships
                neo4j_url = "http://localhost:7474/db/neo4j/tx/commit"
                neo4j_auth = ("neo4j", "12345678")

                # First search for relevant memories using MemOS API
                search_response = await client.post(
                    f"{MEMOS_URL}/search",
                    json={
                        "user_id": MEMOS_USER,
                        "query": query,
                        "install_cube_ids": [cube_id]
                    }
                )

                memories = []
                if search_response.status_code == 200:
                    data = search_response.json()
                    if data.get("code") == 200:
                        text_mems = data.get("data", {}).get("text_mem", [])
                        for cube_data in text_mems:
                            memories.extend(cube_data.get("memories", []))

                # Query Neo4j for all CAUSE/RELATE/CONFLICT relationships
                cypher_query = """
                MATCH (a)-[r:CAUSE|RELATE|CONFLICT|CONDITION]->(b)
                WHERE a.memory CONTAINS $keyword OR b.memory CONTAINS $keyword
                RETURN a.id as source_id, a.memory as source_memory,
                       type(r) as relation_type,
                       b.id as target_id, b.memory as target_memory
                LIMIT 20
                """

                neo4j_response = await client.post(
                    neo4j_url,
                    json={
                        "statements": [{
                            "statement": cypher_query,
                            "parameters": {"keyword": query}
                        }]
                    },
                    auth=neo4j_auth
                )

                results = []
                results.append(f"## 🧠 Knowledge Graph: {cube_id}")
                results.append(f"Query: `{query}`")
                results.append("")

                # Display memories from search
                if memories:
                    results.append("### 📝 Related Memories")
                    results.append("")
                    for i, mem in enumerate(memories[:5], 1):
                        memory = mem.get("memory", "")
                        first_line = memory.split("\n")[0][:100]
                        results.append(f"{i}. {first_line}")
                    results.append("")

                # Display relationships from Neo4j
                if neo4j_response.status_code == 200:
                    neo4j_data = neo4j_response.json()
                    rows = neo4j_data.get("results", [{}])[0].get("data", [])

                    if rows:
                        results.append("### 🔗 Relationships")
                        results.append("```")
                        for row in rows:
                            r = row.get("row", [])
                            if len(r) >= 5:
                                source_mem = (r[1] or "")[:50]
                                rel_type = r[2]
                                target_mem = (r[4] or "")[:50]

                                if rel_type == "CAUSE":
                                    arrow = "──CAUSE──>"
                                elif rel_type == "RELATE":
                                    arrow = "──RELATE──"
                                elif rel_type == "CONFLICT":
                                    arrow = "══CONFLICT══"
                                else:
                                    arrow = f"──{rel_type}──>"

                                results.append(f"[{source_mem}...]")
                                results.append(f"    {arrow}")
                                results.append(f"[{target_mem}...]")
                                results.append("")
                        results.append("```")
                    else:
                        results.append("*No relationships found for this query.*")
                else:
                    results.append(f"*Neo4j query error: {neo4j_response.status_code}*")

                return [TextContent(type="text", text="\n".join(results))]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except httpx.ConnectError:
            return [TextContent(type="text", text=f"❌ Cannot connect to MemOS API at {MEMOS_URL}. Is the server running?")]
        except Exception as e:
            logger.exception("Tool call failed")
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def run_server():
    """Run the MCP server."""
    # Pre-register default cube at startup
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await ensure_cube_registered(client, MEMOS_DEFAULT_CUBE)
            logger.info(f"Startup: Default cube '{MEMOS_DEFAULT_CUBE}' ready")
        except Exception as e:
            logger.warning(f"Startup: Could not pre-register cube: {e}")

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
