#!/usr/bin/env python3
"""
MemOS MCP Server - Intelligent Memory Management for Claude Code

This MCP server provides tools for Claude to proactively search and save
project memories, enabling intelligent context-aware assistance.
"""

import argparse
import asyncio
import json
import logging
import os
import re
from typing import Any

import sys
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)
from pydantic import BaseModel

# Parse command line arguments first (WSL env vars don't pass to Windows Python)
def parse_args():
    parser = argparse.ArgumentParser(description='MemOS MCP Server')
    parser.add_argument('--memos-url', default=None, help='MemOS API URL')
    parser.add_argument('--memos-user', default=None, help='Default user ID')
    parser.add_argument('--memos-default-cube', default=None, help='Default cube ID')
    parser.add_argument('--memos-cubes-dir', default=None, help='Cubes directory path')
    parser.add_argument('--memos-enable-delete', default=None, help='Enable delete tool (true/false)')
    parser.add_argument('--memos-timeout-tool', default=None, help='Tool call timeout in seconds')
    parser.add_argument('--memos-timeout-startup', default=None, help='Startup timeout in seconds')
    parser.add_argument('--memos-timeout-health', default=None, help='Health check timeout in seconds')
    parser.add_argument('--memos-api-wait-max', default=None, help='Max API wait time in seconds')
    return parser.parse_known_args()[0]

_args = parse_args()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("memos-mcp")

# Configuration: CLI args take precedence over env vars
MEMOS_URL = _args.memos_url or os.environ.get("MEMOS_URL", "http://localhost:18000")
MEMOS_USER = _args.memos_user or os.environ.get("MEMOS_USER", "dev_user")
MEMOS_DEFAULT_CUBE = _args.memos_default_cube or os.environ.get("MEMOS_DEFAULT_CUBE", "dev_cube")
MEMOS_CUBES_DIR = _args.memos_cubes_dir or os.environ.get("MEMOS_CUBES_DIR", "G:/test/MemOS/data/memos_cubes")

# Timeout configuration (in seconds)
# Large documents with embedding may take longer
MEMOS_TIMEOUT_TOOL = float(_args.memos_timeout_tool or os.environ.get("MEMOS_TIMEOUT_TOOL", "120.0"))
MEMOS_TIMEOUT_STARTUP = float(_args.memos_timeout_startup or os.environ.get("MEMOS_TIMEOUT_STARTUP", "30.0"))
MEMOS_TIMEOUT_HEALTH = float(_args.memos_timeout_health or os.environ.get("MEMOS_TIMEOUT_HEALTH", "5.0"))
MEMOS_API_WAIT_MAX = float(_args.memos_api_wait_max or os.environ.get("MEMOS_API_WAIT_MAX", "60.0"))

# Safety configuration - dangerous operations disabled by default
# Set to "true" to enable delete functionality (user must explicitly enable)
_enable_delete_val = _args.memos_enable_delete or os.environ.get("MEMOS_ENABLE_DELETE", "false")
MEMOS_ENABLE_DELETE = _enable_delete_val.lower() == "true"

# Create server instance
server = Server("memos-memory")

# Track registered cubes to avoid repeated registration attempts
_registered_cubes: set[str] = set()
_last_registration_attempt: dict[str, float] = {}  # cube_id -> timestamp
REGISTRATION_RETRY_INTERVAL = 5.0  # seconds


async def verify_cube_loaded(client: httpx.AsyncClient, cube_id: str) -> bool:
    """Verify cube is actually loaded in API (not just registered)."""
    try:
        response = await client.get(
            f"{MEMOS_URL}/memories",
            params={"user_id": MEMOS_USER, "mem_cube_id": cube_id}
        )
        if response.status_code == 200:
            data = response.json()
            # code 200 means cube is loaded, even if no memories
            return data.get("code") == 200
    except Exception:
        pass
    return False


async def ensure_cube_registered(client: httpx.AsyncClient, cube_id: str, force: bool = False) -> bool:
    """Ensure cube is registered and loaded. Returns True if successful.

    Args:
        client: HTTP client
        cube_id: Cube ID to register
        force: If True, skip cache and always try to register
    """
    import time
    now = time.time()

    # Check cache (unless forced)
    if not force and cube_id in _registered_cubes:
        return True

    # Rate limit registration attempts (unless forced)
    if not force:
        last_attempt = _last_registration_attempt.get(cube_id, 0)
        if now - last_attempt < REGISTRATION_RETRY_INTERVAL:
            return cube_id in _registered_cubes

    _last_registration_attempt[cube_id] = now

    try:
        # First check if already loaded
        if await verify_cube_loaded(client, cube_id):
            _registered_cubes.add(cube_id)
            logger.info(f"Cube '{cube_id}' already loaded")
            return True

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
            # Registration failed - don't cache
            logger.warning(f"Cube registration returned: {data.get('message')}")
    except httpx.ConnectError:
        logger.warning(f"API not available, cannot register cube {cube_id}")
    except Exception as e:
        logger.warning(f"Failed to auto-register cube {cube_id}: {e}")

    return False


async def wait_for_api_ready(max_wait: float | None = None, interval: float = 2.0) -> bool:
    """Wait for MemOS API to be ready. Returns True if ready."""
    import time
    if max_wait is None:
        max_wait = MEMOS_API_WAIT_MAX
    start = time.time()

    async with httpx.AsyncClient(timeout=MEMOS_TIMEOUT_HEALTH) as client:
        while time.time() - start < max_wait:
            try:
                response = await client.get(f"{MEMOS_URL}/users")
                if response.status_code == 200:
                    logger.info("MemOS API is ready")
                    return True
            except httpx.ConnectError:
                pass
            except Exception as e:
                logger.debug(f"API check failed: {e}")

            await asyncio.sleep(interval)

    logger.warning(f"MemOS API not ready after {max_wait}s")
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
        memories_data = cube_data.get("memories", [])
        
        # If memories is a dict with nodes (tree_text mode), extract nodes
        memories = []
        if isinstance(memories_data, dict) and "nodes" in memories_data:
            memories = memories_data["nodes"]
        elif isinstance(memories_data, list):
            memories = memories_data

        if memories:
            results.append(f"## 📦 Cube: {cube_id}")
            results.append("")

            # Group by type
            grouped = {}
            for mem in memories:
                memory_text = mem.get("memory", "")
                # Try to extract type from [TYPE] prefix
                type_match = re.match(r"^\[([A-Z_]+)\]", memory_text)
                mem_type = type_match.group(1) if type_match else "PROGRESS"
                if mem_type not in grouped:
                    grouped[mem_type] = []
                grouped[mem_type].append(mem)

            # Display by type
            for mem_type, items in grouped.items():
                results.append(f"### 🏷️ Type: {mem_type}")
                results.append("")

                for i, mem in enumerate(items, 1):
                    memory_text = mem.get("memory", "")
                    mem_id = mem.get("id", "")  # Full UUID for delete operations

                    # Remove the [TYPE] prefix from display text if present
                    display_text = re.sub(r"^\[[A-Z_]+\]\s*", "", memory_text)

                    # Extract first line as title
                    first_line = display_text.split("\n")[0][:100]
                    if len(display_text.split("\n")) > 1 or len(display_text) > 100:
                        results.append(f"#### {i}. {first_line}")
                    else:
                        results.append(f"#### {i}. {display_text}")

                    results.append(f"ID: `{mem_id}`")
                    results.append("")
                    
                    # Detect if it's a code block (simple heuristic)
                    if "```" not in display_text and any(line.strip().startswith(("import ", "def ", "class ", "export ", "const ", "let ", "var ")) for line in display_text.split("\n")):
                        results.append("```python")
                        results.append(display_text)
                        results.append("```")
                    else:
                        results.append(display_text)
                        
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
                # Clean up memory text for mermaid (remove newlines and special chars)
                clean_text = node_memory.replace("\n", " ").replace('"', "'").replace("[", "(").replace("]", ")")
                node_lookup[node_id] = clean_text[:50] + "..." if len(clean_text) > 50 else clean_text

            # Display nodes
            if nodes:
                results.append("### 📝 Memory Nodes")
                results.append("")
                for i, node in enumerate(nodes[:10], 1):  # Limit to 10 nodes
                    memory = node.get("memory", "")
                    first_line = memory.split("\n")[0][:100]
                    node_id = node.get("id", "")  # Full UUID for delete operations
                    results.append(f"{i}. **{first_line}**")
                    results.append(f"   ID: `{node_id}`")
                    results.append("")

            # Display relationships with Mermaid diagram
            if edges:
                results.append("### 📊 Relationship Diagram (Mermaid)")
                results.append("")
                results.append("```mermaid")
                results.append("graph TD")
                
                # Style definitions
                results.append("    classDef cause fill:#f96,stroke:#333,stroke-width:2px;")
                results.append("    classDef relate fill:#bbf,stroke:#333,stroke-width:1px;")
                results.append("    classDef conflict fill:#f66,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;")
                
                added_edges = set()
                for edge in edges:
                    source_id = edge.get("source", "")
                    target_id = edge.get("target", "")
                    rel_type = edge.get("type", "UNKNOWN")

                    # Skip PARENT relationships, only show semantic ones
                    if rel_type == "PARENT":
                        continue
                    
                    # Avoid duplicate edges in diagram
                    edge_key = f"{source_id}-{target_id}-{rel_type}"
                    if edge_key in added_edges:
                        continue
                    added_edges.add(edge_key)

                    source_text = node_lookup.get(source_id, source_id[:8])
                    target_text = node_lookup.get(target_id, target_id[:8])
                    
                    # Sanitize IDs for mermaid (must be alphanumeric)
                    s_id = f"node_{source_id[:8]}"
                    t_id = f"node_{target_id[:8]}"

                    # Format relationship in mermaid
                    if rel_type == "CAUSE":
                        results.append(f'    {s_id}["{source_text}"] -- CAUSE --> {t_id}["{target_text}"]:::cause')
                    elif rel_type == "RELATE":
                        results.append(f'    {s_id}["{source_text}"] -. RELATE .- {t_id}["{target_text}"]:::relate')
                    elif rel_type == "CONFLICT":
                        results.append(f'    {s_id}["{source_text}"] == CONFLICT == {t_id}["{target_text}"]:::conflict')
                    elif rel_type == "CONDITION":
                        results.append(f'    {s_id}["{source_text}"] -- CONDITION --> {t_id}["{target_text}"]')
                    else:
                        results.append(f'    {s_id}["{source_text}"] -- {rel_type} --> {t_id}["{target_text}"]')

                results.append("```")
                results.append("")

                # Textual fallback for terminals that don't render mermaid
                results.append("### 🔗 Textual Relationships")
                results.append("")
                results.append("```")
                for edge in edges:
                    if edge.get("type") == "PARENT": continue
                    s_text = node_lookup.get(edge.get("source"), "???")[:40]
                    t_text = node_lookup.get(edge.get("target"), "???")[:40]
                    results.append(f"[{s_text}] --{edge.get('type')}--> [{t_text}]")
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
    tools = [
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
            name="memos_list_v2",
            description="""List memories from a memory cube (v2 with improved formatting).""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID (project name). Defaults to current project.",
                        "default": MEMOS_DEFAULT_CUBE
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memories to return.",
                        "default": 20
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Optional: Filter by memory type (e.g., DECISION, ERROR_PATTERN).",
                        "enum": ["ERROR_PATTERN", "DECISION", "MILESTONE", "BUGFIX", "FEATURE", "CONFIG", "CODE_PATTERN", "GOTCHA", "PROGRESS"]
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memos_list",
            description="""List all memories in a project cube.

Use this to get an overview of what's been recorded for the project.
You can filter by memory type to find specific categories like decisions or errors.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID (project name)",
                        "default": MEMOS_DEFAULT_CUBE
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Filter by memory type (e.g., 'DECISION', 'ERROR_PATTERN')",
                        "enum": ["ERROR_PATTERN", "DECISION", "MILESTONE", "BUGFIX",
                                "FEATURE", "CONFIG", "CODE_PATTERN", "GOTCHA", "PROGRESS"]
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
            name="memos_get_stats",
            description="""Get statistics about memories in a project cube.
            
Use this to see how many memories of each type (DECISION, ERROR_PATTERN, etc.) are stored.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID (project name)",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                }
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

    # Conditionally add delete tool if enabled (dangerous operation, disabled by default)
    if MEMOS_ENABLE_DELETE:
        tools.append(
            Tool(
                name="memos_delete",
                description="""⚠️ DELETE memories from project memory. USE WITH CAUTION!

This tool is DISABLED by default. User must explicitly enable it via MEMOS_ENABLE_DELETE=true.

ONLY use this tool when the user EXPLICITLY requests deletion.
NEVER use this tool proactively or without user confirmation.

Operations:
- Delete a single memory by ID
- Delete multiple memories by IDs
- Delete ALL memories in a cube (requires delete_all=true)

Before deleting, always:
1. Confirm with the user what will be deleted
2. Show the memory content that will be deleted
3. Get explicit user approval""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "ID of the specific memory to delete. Get this from memos_search or memos_list."
                        },
                        "memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of memory IDs to delete in batch."
                        },
                        "cube_id": {
                            "type": "string",
                            "description": "Memory cube ID (project name). Defaults to current project.",
                            "default": MEMOS_DEFAULT_CUBE
                        },
                        "delete_all": {
                            "type": "boolean",
                            "description": "Set to true to delete ALL memories in the cube. DANGEROUS! Requires explicit user confirmation.",
                            "default": False
                        }
                    },
                    "required": []
                }
            )
        )
        logger.info("Delete tool enabled (MEMOS_ENABLE_DELETE=true)")

    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    async with httpx.AsyncClient(timeout=MEMOS_TIMEOUT_TOOL) as client:
        try:
            if name == "memos_search":
                query = arguments.get("query", "")
                cube_id = arguments.get("cube_id", MEMOS_DEFAULT_CUBE)

                # Auto-register cube if needed (with force retry on first call)
                if not await ensure_cube_registered(client, cube_id):
                    # Force retry registration
                    await ensure_cube_registered(client, cube_id, force=True)

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

                # Auto-register cube with retry on failure
                if not await ensure_cube_registered(client, cube_id):
                    await ensure_cube_registered(client, cube_id, force=True)

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
                        # Try force re-register and retry once
                        _registered_cubes.discard(cube_id)
                        if await ensure_cube_registered(client, cube_id, force=True):
                            retry_response = await client.post(
                                f"{MEMOS_URL}/memories",
                                json={
                                    "user_id": MEMOS_USER,
                                    "mem_cube_id": cube_id,
                                    "memory_content": content
                                }
                            )
                            if retry_response.status_code == 200:
                                retry_data = retry_response.json()
                                if retry_data.get("code") == 200:
                                    return [TextContent(type="text", text=f"✅ Memory saved successfully as [{memory_type}] (after re-registration)")]
                        return [TextContent(type="text", text=f"Save failed: {data.get('message', 'Unknown error')}")]
                elif response.status_code == 400:
                    # 400 often means cube not loaded, force re-register and retry
                    _registered_cubes.discard(cube_id)
                    if await ensure_cube_registered(client, cube_id, force=True):
                        retry_response = await client.post(
                            f"{MEMOS_URL}/memories",
                            json={
                                "user_id": MEMOS_USER,
                                "mem_cube_id": cube_id,
                                "memory_content": content
                            }
                        )
                        if retry_response.status_code == 200:
                            retry_data = retry_response.json()
                            if retry_data.get("code") == 200:
                                return [TextContent(type="text", text=f"✅ Memory saved successfully as [{memory_type}] (after re-registration)")]
                    return [TextContent(type="text", text=f"API error: 400 - Cube may not be loaded. Try again.")]
                else:
                    return [TextContent(type="text", text=f"API error: {response.status_code}")]

            elif name in ("memos_list", "memos_list_v2"):
                cube_id = arguments.get("cube_id", MEMOS_DEFAULT_CUBE)
                limit = arguments.get("limit", 20)
                memory_type = arguments.get("memory_type")

                # Auto-register cube
                await ensure_cube_registered(client, cube_id)

                params = {
                    "user_id": MEMOS_USER,
                    "mem_cube_id": cube_id,
                    "limit": limit
                }
                if memory_type:
                    params["memory_type"] = memory_type

                response = await client.get(
                    f"{MEMOS_URL}/memories",
                    params=params
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        formatted = format_memories_for_display(data.get("data", {}))
                        return [TextContent(type="text", text=formatted)]
                    else:
                        # Force re-register and retry
                        _registered_cubes.discard(cube_id)
                        if await ensure_cube_registered(client, cube_id, force=True):
                            retry_response = await client.get(
                                f"{MEMOS_URL}/memories",
                                params=params
                            )
                            if retry_response.status_code == 200:
                                retry_data = retry_response.json()
                                if retry_data.get("code") == 200:
                                    formatted = format_memories_for_display(retry_data.get("data", {}))
                                    return [TextContent(type="text", text=formatted)]
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

            elif name == "memos_get_stats":
                cube_id = arguments.get("cube_id", MEMOS_DEFAULT_CUBE)
                
                # Auto-register cube if needed
                if not await ensure_cube_registered(client, cube_id):
                    await ensure_cube_registered(client, cube_id, force=True)

                response = await client.get(
                    f"{MEMOS_URL}/memories",
                    params={"user_id": MEMOS_USER, "mem_cube_id": cube_id}
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 200:
                        # Extract memories correctly from text_mem and handle nodes
                        text_mems = data.get("data", {}).get("text_mem", [])
                        stats = {}
                        total = 0
                        
                        for cube_data in text_mems:
                            mem_data = cube_data.get("memories", [])
                            memories = []
                            if isinstance(mem_data, dict) and "nodes" in mem_data:
                                memories = mem_data["nodes"]
                            elif isinstance(mem_data, list):
                                memories = mem_data
                                
                            for mem in memories:
                                memory_text = mem.get("memory", "")
                                total += 1
                                type_match = re.match(r"^\[([A-Z_]+)\]", memory_text)
                                mem_type = type_match.group(1) if type_match else "PROGRESS"
                                stats[mem_type] = stats.get(mem_type, 0) + 1
                        
                        if not stats:
                            return [TextContent(type="text", text=f"No memories found in cube '{cube_id}'.")]
                            
                        result = [f"## 📊 Memory Stats: {cube_id}"]
                        result.append(f"Total Memories: **{total}**\n")
                        for mtype, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                            percentage = (count / total) * 100
                            result.append(f"- **{mtype}**: {count} ({percentage:.1f}%)")
                        
                        return [TextContent(type="text", text="\n".join(result))]
                    else:
                        return [TextContent(type="text", text=f"Stats failed: {data.get('message', 'Unknown error')}")]
                else:
                    return [TextContent(type="text", text=f"API error: {response.status_code}")]

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

            elif name == "memos_delete":
                # Safety check - only allow if explicitly enabled
                if not MEMOS_ENABLE_DELETE:
                    return [TextContent(type="text", text="❌ Delete functionality is DISABLED. Set MEMOS_ENABLE_DELETE=true in environment to enable.")]

                memory_id = arguments.get("memory_id")
                memory_ids = arguments.get("memory_ids", [])
                cube_id = arguments.get("cube_id", MEMOS_DEFAULT_CUBE)
                delete_all = arguments.get("delete_all", False)

                # Collect all IDs to delete
                ids_to_delete = []
                if memory_id:
                    ids_to_delete.append(memory_id)
                if memory_ids:
                    ids_to_delete.extend(memory_ids)

                # Auto-register cube
                await ensure_cube_registered(client, cube_id)

                if delete_all:
                    # Delete ALL memories - very dangerous!
                    response = await client.delete(
                        f"{MEMOS_URL}/memories/{cube_id}",
                        params={"user_id": MEMOS_USER}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if data.get("code") == 200:
                            return [TextContent(type="text", text=f"⚠️ **ALL memories deleted** from cube: `{cube_id}`")]
                        else:
                            return [TextContent(type="text", text=f"❌ **Delete all failed**: {data.get('message', 'Unknown error')}")]
                    else:
                        return [TextContent(type="text", text=f"❌ **API error** during delete all: {response.status_code}")]

                elif ids_to_delete:
                    # Delete single or multiple memories
                    results = []
                    for mid in ids_to_delete:
                        # Optional: Try to fetch memory first to confirm it exists and show content
                        try:
                            get_resp = await client.get(
                                f"{MEMOS_URL}/memories/{cube_id}/{mid}",
                                params={"user_id": MEMOS_USER}
                            )
                            mem_content = "*(Unknown content)*"
                            if get_resp.status_code == 200:
                                g_data = get_resp.json()
                                if g_data.get("code") == 200 and g_data.get("data"):
                                    # Extract memory text from the node
                                    mem_node = g_data.get("data")
                                    if isinstance(mem_node, dict):
                                        mem_content = mem_node.get("memory", mem_content)
                        except Exception:
                            mem_content = "*(Fetch failed)*"

                        response = await client.delete(
                            f"{MEMOS_URL}/memories/{cube_id}/{mid}",
                            params={"user_id": MEMOS_USER}
                        )

                        if response.status_code == 200:
                            data = response.json()
                            if data.get("code") == 200:
                                results.append(f"✅ Deleted: `{mid}`\n   > {mem_content[:150]}...")
                            else:
                                results.append(f"❌ Failed: `{mid}` ({data.get('message', 'Unknown error')})")
                        else:
                            results.append(f"❌ API Error: `{mid}` (Status: {response.status_code})")

                    return [TextContent(type="text", text="\n".join(results))]

                else:
                    return [TextContent(type="text", text="❌ Must provide either `memory_id`, `memory_ids` or `delete_all=true`")]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except httpx.ConnectError:
            return [TextContent(type="text", text=f"❌ Cannot connect to MemOS API at {MEMOS_URL}. Is the server running?")]
        except Exception as e:
            logger.exception("Tool call failed")
            return [TextContent(type="text", text=f"Error: {str(e)}")]


async def run_server():
    """Run the MCP server."""
    # Log timeout configuration
    logger.info(f"Timeout config: tool={MEMOS_TIMEOUT_TOOL}s, startup={MEMOS_TIMEOUT_STARTUP}s, health={MEMOS_TIMEOUT_HEALTH}s, api_wait={MEMOS_API_WAIT_MAX}s")

    # Wait for MemOS API to be ready before starting
    api_ready = await wait_for_api_ready()

    if api_ready:
        # Pre-register default cube at startup with retry
        async with httpx.AsyncClient(timeout=MEMOS_TIMEOUT_STARTUP) as client:
            for attempt in range(3):
                try:
                    if await ensure_cube_registered(client, MEMOS_DEFAULT_CUBE, force=True):
                        logger.info(f"Startup: Default cube '{MEMOS_DEFAULT_CUBE}' ready")
                        break
                    else:
                        logger.warning(f"Startup: Cube registration attempt {attempt + 1} failed, retrying...")
                        await asyncio.sleep(2.0)
                except Exception as e:
                    logger.warning(f"Startup: Registration attempt {attempt + 1} error: {e}")
                    await asyncio.sleep(2.0)
    else:
        logger.warning("Startup: API not ready, will try to register cube on first tool call")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Entry point."""
    # Log configuration at startup
    logger.info(f"MemOS MCP Server starting...")
    logger.info(f"  MEMOS_URL: {MEMOS_URL}")
    logger.info(f"  MEMOS_USER: {MEMOS_USER}")
    logger.info(f"  MEMOS_DEFAULT_CUBE: {MEMOS_DEFAULT_CUBE}")
    logger.info(f"  MEMOS_ENABLE_DELETE: {MEMOS_ENABLE_DELETE}")
    logger.info(f"  MEMOS_TIMEOUT_TOOL: {MEMOS_TIMEOUT_TOOL}s")
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
