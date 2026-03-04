#!/usr/bin/env python3
"""
MemOS MCP Server Handlers Utility Module

Contains shared utilities for handlers including standardized error formatting.
"""

from typing import Any

from cube_manager import get_default_cube_id
from mcp.types import TextContent


# ─── Error Codes ────────────────────────────────────────────────────────────────

ERR_API_UNREACHABLE = "API_UNREACHABLE"
ERR_API_ERROR = "API_ERROR"
ERR_CUBE_NOT_FOUND = "CUBE_NOT_FOUND"
ERR_CUBE_REGISTRATION = "CUBE_REGISTRATION_FAILED"
ERR_PARAM_MISSING = "PARAM_MISSING"
ERR_PARAM_INVALID = "PARAM_INVALID"
ERR_NEO4J_CONFIG = "NEO4J_CONFIG_MISSING"
ERR_OPERATION_FAILED = "OPERATION_FAILED"
ERR_DELETE_DISABLED = "DELETE_DISABLED"
ERR_USER_ERROR = "USER_ERROR"


def get_cube_id_from_args(arguments: dict[str, Any]) -> str:
    """
    Get cube_id from arguments with smart project path derivation.

    Priority:
    1. Explicit cube_id (if not "dev_cube" when project_path is also provided)
    2. Derived from project_path using detect_cube_from_path()
    3. Explicit cube_id as-is
    4. Default from config

    Args:
        arguments: Tool call arguments

    Returns:
        Cube ID to use
    """
    arg_cube_id = arguments.get("cube_id")
    project_path = arguments.get("project_path")

    # If project_path is provided, derive cube_id from it
    if project_path:
        try:
            from keyword_enhancer import detect_cube_from_path
            derived = detect_cube_from_path(project_path)
            if derived:
                return derived
        except Exception:
            pass

    # Fall back to explicit cube_id or default
    return arg_cube_id if arg_cube_id else get_default_cube_id()


def error_response(
    message: str,
    error_code: str | None = None,
    suggestions: list[str] | None = None,
) -> list[TextContent]:
    """
    Create a standardized error response.

    Format:
        [ERROR] [ERROR_CODE] Error message

        [TIP] Suggestions:
        - suggestion 1
        - suggestion 2

    Args:
        message: Human-readable error description
        error_code: Machine-readable error code (e.g. ERR_API_ERROR)
        suggestions: List of actionable suggestions for recovery
    """
    parts = []

    if error_code:
        parts.append(f"[ERROR] [{error_code}] {message}")
    else:
        parts.append(f"[ERROR] {message}")

    if suggestions:
        parts.append("")
        parts.append("[TIP] Suggestions:")
        for s in suggestions:
            parts.append(f"- {s}")

    return [TextContent(type="text", text="\n".join(parts))]


def success_response(message: str) -> list[TextContent]:
    """Create a success response."""
    return [TextContent(type="text", text=message)]


def cube_registration_error(cube_id: str, detail: str) -> list[TextContent]:
    """Standardized cube registration failure error."""
    return error_response(
        f"Cube '{cube_id}' registration failed: {detail}",
        error_code=ERR_CUBE_REGISTRATION,
        suggestions=[
            "Check if MemOS API is running: `curl http://localhost:18000/health`",
            "Verify cube exists: `memos_list_cubes(include_status=True)`",
            "Try manual registration: `memos_register_cube(cube_id=\"...\")`",
        ],
    )


def api_error_response(operation: str, status_or_msg: str | int) -> list[TextContent]:
    """Standardized API error response."""
    return error_response(
        f"{operation} failed: {status_or_msg}",
        error_code=ERR_API_ERROR,
        suggestions=[
            "Check API health: `curl http://localhost:18000/health/detail`",
            "Check API logs for details",
        ],
    )
