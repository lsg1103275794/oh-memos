#!/usr/bin/env python3
"""
MemOS MCP Server Handlers Package

Provides handler dispatch functionality for all MCP tools.
"""

from typing import Any

import httpx

from mcp.types import TextContent

from handlers.admin import (
    handle_memos_create_user,
    handle_memos_delete,
    handle_memos_list_cubes,
    handle_memos_register_cube,
    handle_memos_validate_cubes,
)
from handlers.calendar import handle_memos_calendar
from handlers.graph import (
    handle_memos_export_schema,
    handle_memos_get_graph,
    handle_memos_trace_path,
)
from handlers.memory import (
    handle_memos_get,
    handle_memos_get_stats,
    handle_memos_list,
    handle_memos_save,
)
from handlers.search import (
    handle_memos_search,
    handle_memos_search_context,
    handle_memos_suggest,
)


# Handler registry: maps tool name to handler function
HANDLER_REGISTRY = {
    # Search handlers
    "memos_search": handle_memos_search,
    "memos_search_context": handle_memos_search_context,
    "memos_suggest": handle_memos_suggest,

    # Memory handlers
    "memos_save": handle_memos_save,
    "memos_list_v2": handle_memos_list,
    "memos_get": handle_memos_get,
    "memos_get_stats": handle_memos_get_stats,

    # Graph handlers
    "memos_trace_path": handle_memos_trace_path,
    "memos_get_graph": handle_memos_get_graph,
    "memos_export_schema": handle_memos_export_schema,

    # Admin handlers
    "memos_list_cubes": handle_memos_list_cubes,
    "memos_register_cube": handle_memos_register_cube,
    "memos_create_user": handle_memos_create_user,
    "memos_validate_cubes": handle_memos_validate_cubes,
    "memos_delete": handle_memos_delete,

    # Calendar handler (student mode)
    "memos_calendar": handle_memos_calendar,
}


async def dispatch_tool(
    client: httpx.AsyncClient,
    name: str,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """
    Dispatch a tool call to the appropriate handler.

    Args:
        client: HTTP client for API calls
        name: Tool name
        arguments: Tool arguments

    Returns:
        List of TextContent responses
    """
    handler = HANDLER_REGISTRY.get(name)
    if handler:
        return await handler(client, arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
