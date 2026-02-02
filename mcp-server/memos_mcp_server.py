#!/usr/bin/env python3
"""
MemOS MCP Server - Intelligent Memory Management for Claude Code

This MCP server provides tools for Claude to proactively search and save
project memories, enabling intelligent context-aware assistance.
"""

import asyncio

from typing import Any

import httpx

from api_client import get_http_client, wait_for_api_ready
from config import (
    MEMOS_API_WAIT_MAX,
    MEMOS_DEFAULT_CUBE,
    MEMOS_ENABLE_DELETE,
    MEMOS_TIMEOUT_HEALTH,
    MEMOS_TIMEOUT_STARTUP,
    MEMOS_TIMEOUT_TOOL,
    MEMOS_URL,
    MEMOS_USER,
    logger,
    server,
)
from cube_manager import ensure_cube_registered
from handlers import dispatch_tool
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from tools_registry import get_tools


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return get_tools()


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    # Use shared HTTP client for connection reuse
    client = await get_http_client()

    try:
        return await dispatch_tool(client, name, arguments)
    except httpx.ConnectError:
        return [TextContent(type="text", text=f"❌ Cannot connect to MemOS API at {MEMOS_URL}. Is the server running?")]
    except Exception as e:
        logger.exception("Tool call failed")
        return [TextContent(type="text", text=f"Error: {e!s}")]


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
                    reg_success, reg_error = await ensure_cube_registered(client, MEMOS_DEFAULT_CUBE, force=True)
                    if reg_success:
                        logger.info(f"Startup: Default cube '{MEMOS_DEFAULT_CUBE}' ready")
                        break
                    else:
                        logger.warning(f"Startup: Cube registration attempt {attempt + 1} failed: {reg_error}")
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
    logger.info("MemOS MCP Server starting...")
    logger.info(f"  MEMOS_URL: {MEMOS_URL}")
    logger.info(f"  MEMOS_USER: {MEMOS_USER}")
    logger.info(f"  MEMOS_DEFAULT_CUBE: {MEMOS_DEFAULT_CUBE}")
    logger.info(f"  MEMOS_ENABLE_DELETE: {MEMOS_ENABLE_DELETE}")
    logger.info(f"  MEMOS_TIMEOUT_TOOL: {MEMOS_TIMEOUT_TOOL}s")
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
