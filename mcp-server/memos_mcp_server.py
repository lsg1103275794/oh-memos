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
        return [TextContent(
            type="text",
            text=(
                f"❌ [API_UNREACHABLE] Cannot connect to MemOS API at {MEMOS_URL}\n\n"
                "💡 Suggestions:\n"
                "- Check if MemOS API is running: `curl http://localhost:18000/health`\n"
                "- Start with: `scripts/local/start.bat`\n"
                "- Check port availability"
            )
        )]
    except Exception as e:
        logger.exception("Tool call failed")
        return [TextContent(
            type="text",
            text=(
                f"❌ [UNEXPECTED_ERROR] {e!s}\n\n"
                "💡 Suggestions:\n"
                "- Check MCP server logs for details\n"
                "- Verify MemOS API is healthy: `curl http://localhost:18000/health/detail`"
            )
        )]


async def _background_init():
    """Background initialization: wait for API and register default cube."""
    try:
        api_ready = await wait_for_api_ready()

        if api_ready:
            async with httpx.AsyncClient(timeout=MEMOS_TIMEOUT_STARTUP) as client:
                for attempt in range(3):
                    try:
                        reg_success, reg_error = await ensure_cube_registered(client, MEMOS_DEFAULT_CUBE, force=True)
                        if reg_success:
                            logger.debug(f"Default cube '{MEMOS_DEFAULT_CUBE}' ready")
                            return
                        else:
                            logger.warning(f"Cube registration attempt {attempt + 1} failed: {reg_error}")
                            await asyncio.sleep(2.0)
                    except Exception as e:
                        logger.warning(f"Registration attempt {attempt + 1} error: {e}")
                        await asyncio.sleep(2.0)
        else:
            logger.warning("API not ready, will register cube on first tool call")
    except Exception as e:
        logger.warning(f"Background init failed: {e}")


async def run_server():
    """Run the MCP server."""
    logger.debug(f"Timeout config: tool={MEMOS_TIMEOUT_TOOL}s, startup={MEMOS_TIMEOUT_STARTUP}s, health={MEMOS_TIMEOUT_HEALTH}s, api_wait={MEMOS_API_WAIT_MAX}s")

    # Start stdio server FIRST to complete MCP handshake immediately,
    # then do API health check and cube registration in background.
    # This prevents Claude Code from timing out waiting for MCP handshake.
    async with stdio_server() as (read_stream, write_stream):
        init_task = asyncio.create_task(_background_init())
        try:
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
        finally:
            init_task.cancel()
            try:
                await init_task
            except asyncio.CancelledError:
                pass


def main():
    """Entry point."""
    logger.debug(f"MemOS MCP Server: URL={MEMOS_URL}, user={MEMOS_USER}, cube={MEMOS_DEFAULT_CUBE}")
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
