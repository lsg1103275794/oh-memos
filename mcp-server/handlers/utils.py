#!/usr/bin/env python3
"""
MemOS MCP Server Handlers Utility Module

Contains shared utilities for handlers.
"""

from typing import Any

from cube_manager import get_default_cube_id
from mcp.types import TextContent


def get_cube_id_from_args(arguments: dict[str, Any]) -> str:
    """
    Get cube_id from arguments, using default if not specified.

    Args:
        arguments: Tool call arguments

    Returns:
        Cube ID to use
    """
    arg_cube_id = arguments.get("cube_id")
    return arg_cube_id if arg_cube_id else get_default_cube_id()


def error_response(message: str) -> list[TextContent]:
    """Create an error response."""
    return [TextContent(type="text", text=message)]


def success_response(message: str) -> list[TextContent]:
    """Create a success response."""
    return [TextContent(type="text", text=message)]
