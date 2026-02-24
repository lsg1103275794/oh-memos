#!/usr/bin/env python3
"""
MemOS MCP Server Memory Handlers

Handles memos_save, memos_list, memos_list_v2, memos_get, memos_get_stats tools.

Phase 1 Enhancement: Context compression for efficient token usage.
Phase 1.1: Deduplication to prevent duplicate saves from hooks + manual calls.
"""

import hashlib
import time
from typing import Any

import httpx

from api_client import api_call_with_retry
from config import MEMOS_URL, MEMOS_USER, logger
from cube_manager import ensure_cube_registered
from formatters import format_memories_for_display
from mcp.types import TextContent
from models import (
    COMPACTION_THRESHOLD,
    PREVIEW_COUNT,
    CompactedSearchResult,
    should_compact,
    to_full,
    to_minimal,
)
from query_processing import compute_memory_stats

from handlers.utils import (
    ERR_PARAM_MISSING,
    api_error_response,
    cube_registration_error,
    error_response,
    get_cube_id_from_args,
)

# ============================================================================
# Deduplication Cache
# ============================================================================
# Prevents duplicate saves within a short time window (e.g., hook + manual save)

# Cache: {content_hash: (cube_id, timestamp)}
_save_dedup_cache: dict[str, tuple[str, float]] = {}
DEDUP_TTL_SECONDS = 60  # Ignore duplicate saves within 60 seconds


def _content_hash(content: str, cube_id: str) -> str:
    """Generate hash for content + cube_id combination."""
    key = f"{cube_id}:{content}"
    return hashlib.md5(key.encode()).hexdigest()


def _is_duplicate_save(content: str, cube_id: str) -> bool:
    """
    Check if this content was recently saved (within TTL).
    Returns True if duplicate, False if new.
    """
    content_key = _content_hash(content, cube_id)
    now = time.time()

    # Clean expired entries
    expired = [k for k, (_, ts) in _save_dedup_cache.items() if now - ts > DEDUP_TTL_SECONDS]
    for k in expired:
        del _save_dedup_cache[k]

    # Check if duplicate
    if content_key in _save_dedup_cache:
        _, saved_at = _save_dedup_cache[content_key]
        if now - saved_at < DEDUP_TTL_SECONDS:
            logger.debug(f"Duplicate save detected (within {DEDUP_TTL_SECONDS}s), skipping")
            return True

    return False


def _mark_saved(content: str, cube_id: str) -> None:
    """Mark content as saved in dedup cache."""
    content_key = _content_hash(content, cube_id)
    _save_dedup_cache[content_key] = (cube_id, time.time())


async def handle_memos_save(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_save tool call with deduplication."""
    cube_id = get_cube_id_from_args(arguments)
    content = arguments.get("content", "")
    memory_type = arguments.get("memory_type")

    # memory_type is now REQUIRED - reject if not provided
    if not memory_type:
        return error_response(
            "memory_type parameter is required",
            error_code=ERR_PARAM_MISSING,
            suggestions=[
                "Bug fix -> `BUGFIX` or `ERROR_PATTERN`",
                "Technical decision -> `DECISION`",
                "Gotcha/trap -> `GOTCHA`",
                "Code template -> `CODE_PATTERN`",
                "Config change -> `CONFIG`",
                "New feature -> `FEATURE`",
                "Major achievement -> `MILESTONE`",
                "Pure progress update -> `PROGRESS`",
                "Example: `memos_save(content=\"...\", memory_type=\"BUGFIX\")`",
            ],
        )

    # Prepend memory type if not already present
    if not content.startswith(f"[{memory_type}]"):
        content = f"[{memory_type}] {content}"

    # Deduplication check - prevent duplicate saves within TTL
    if _is_duplicate_save(content, cube_id):
        return [TextContent(
            type="text",
            text=f"⏭️ Skipped: Same content was saved within {DEDUP_TTL_SECONDS}s (dedup protection)"
        )]

    # Auto-register cube if needed
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return cube_registration_error(cube_id, reg_error)

    success, data, status = await api_call_with_retry(
        client, "POST", f"{MEMOS_URL}/memories", cube_id,
        json={
            "user_id": MEMOS_USER,
            "mem_cube_id": cube_id,
            "memory_content": content
        }
    )

    if success:
        # Mark as saved in dedup cache
        _mark_saved(content, cube_id)
        return [TextContent(type="text", text=f"Memory saved as [{memory_type}] in cube '{cube_id}'")]
    elif data:
        return api_error_response("Save", data.get("message", "Unknown error"))
    else:
        return api_error_response("Save", f"HTTP {status}")


async def handle_memos_list(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_list and memos_list_v2 tool calls with context compression."""
    cube_id = get_cube_id_from_args(arguments)
    limit = arguments.get("limit", 20)
    memory_type = arguments.get("memory_type")
    compact = arguments.get("compact", True)  # Default to compact mode

    # Auto-register cube
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return cube_registration_error(cube_id, reg_error)

    params = {
        "user_id": MEMOS_USER,
        "mem_cube_id": cube_id,
        "limit": limit
    }
    if memory_type:
        params["memory_type"] = memory_type

    success, data, status = await api_call_with_retry(
        client, "GET", f"{MEMOS_URL}/memories", cube_id,
        params=params
    )

    if success and data:
        result_data = data.get("data", {})

        # Extract all memories for counting
        all_memories = _extract_memories_from_data(result_data)
        total_count = len(all_memories)

        # Apply context compression if enabled and threshold exceeded
        if compact and should_compact(total_count):
            logger.debug(f"Compacting list results: {total_count} > {COMPACTION_THRESHOLD}")
            preview = [to_minimal(m) for m in all_memories[:PREVIEW_COUNT]]
            compacted = CompactedSearchResult(
                preview=preview,
                total_count=total_count,
                omitted_count=total_count - len(preview),
                message="Use memos_get(memory_id=\"<id>\") for full details",
                query=f"list (type={memory_type})" if memory_type else "list all",
                cube_id=cube_id,
            )
            return [TextContent(type="text", text=compacted.to_display_text())]

        # Standard full display
        formatted = format_memories_for_display(result_data)
        return [TextContent(type="text", text=formatted)]
    elif data:
        return api_error_response("List", data.get("message", "Unknown error"))
    else:
        return api_error_response("List", f"HTTP {status}")


async def handle_memos_get_stats(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_get_stats tool call."""
    cube_id = get_cube_id_from_args(arguments)

    # Auto-register cube if needed
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return cube_registration_error(cube_id, reg_error)

    success, data, status = await api_call_with_retry(
        client, "GET", f"{MEMOS_URL}/memories", cube_id,
        params={"user_id": MEMOS_USER, "mem_cube_id": cube_id}
    )

    if success and data:
        # Use helper function to compute stats
        stats, total = compute_memory_stats(data.get("data", {}))

        if not stats:
            return [TextContent(type="text", text=f"No memories found in cube '{cube_id}'.")]

        result = [f"## 📊 Memory Stats: {cube_id}"]
        result.append(f"Total Memories: **{total}**\n")
        for mtype, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            result.append(f"- **{mtype}**: {count} ({percentage:.1f}%)")

        # Health check: High PROGRESS ratio warning
        progress_count = stats.get("PROGRESS", 0)
        if total > 0 and progress_count / total > 0.7:
            result.append("")
            result.append("---")
            result.append("")
            result.append(f"⚠️ **健康警告**: PROGRESS 类型占比过高 (>{progress_count / total:.0%})")
            result.append("")
            result.append("这可能导致 Neo4j 知识图谱无法建立有效关系。建议:")
            result.append("1. 保存记忆时**显式指定** `memory_type` 参数")
            result.append("2. 参考类型选择决策树:")
            result.append("   - 修复 Bug → `BUGFIX` 或 `ERROR_PATTERN`")
            result.append("   - 技术决策 → `DECISION`")
            result.append("   - 发现陷阱 → `GOTCHA`")
            result.append("   - 新功能 → `FEATURE`")
            result.append("   - 配置变更 → `CONFIG`")

        return [TextContent(type="text", text="\n".join(result))]
    elif data:
        return api_error_response("Stats", data.get("message", "Unknown error"))
    else:
        return api_error_response("Stats", f"HTTP {status}")


def _extract_memories_from_data(data: dict) -> list[dict]:
    """
    Extract flat list of memories from API response data.

    Handles both tree_text mode (nested nodes) and flat list responses.
    """
    memories = []

    text_mems = data.get("text_mem", [])
    for cube_data in text_mems:
        memories_data = cube_data.get("memories", [])

        # Handle tree_text mode (dict with nodes)
        if isinstance(memories_data, dict) and "nodes" in memories_data:
            memories.extend(memories_data["nodes"])
        elif isinstance(memories_data, list):
            memories.extend(memories_data)

    return memories


async def handle_memos_get(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """
    Handle memos_get tool call - get full details of a single memory by ID.

    This is the complement to compacted search/list results.
    When search returns a CompactedSearchResult, use this to get full details.
    """
    cube_id = get_cube_id_from_args(arguments)
    memory_id = arguments.get("memory_id", "")

    if not memory_id:
        return error_response(
            "memory_id parameter is required",
            error_code=ERR_PARAM_MISSING,
            suggestions=[
                "Get memory_id from memos_search or memos_list_v2 results",
                "Example: `memos_get(memory_id=\"abc123-...\")`",
            ],
        )

    # Auto-register cube if needed
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return cube_registration_error(cube_id, reg_error)

    # Use direct API endpoint: GET /memories/{mem_cube_id}/{memory_id}
    success, data, status = await api_call_with_retry(
        client, "GET", f"{MEMOS_URL}/memories/{cube_id}/{memory_id}", cube_id
    )

    if success and data:
        result_data = data.get("data", {})

        if result_data:
            # Convert to full model and format
            full_mem = to_full(result_data, cube_id=cube_id, user_id=MEMOS_USER)

            lines = [
                f"## 📝 Memory Details",
                f"",
                f"**ID**: `{full_mem.id}`",
                f"**Type**: {full_mem.memory_type}",
                f"**Cube**: {full_mem.cube_id}",
            ]

            if full_mem.key:
                lines.append(f"**Key**: {full_mem.key}")
            if full_mem.tags:
                lines.append(f"**Tags**: {', '.join(full_mem.tags)}")
            if full_mem.created_at:
                lines.append(f"**Created**: {full_mem.created_at}")

            lines.append("")
            lines.append("### Content")
            lines.append("")
            lines.append(full_mem.content)

            if full_mem.background:
                lines.append("")
                lines.append("### Background")
                lines.append("")
                lines.append(full_mem.background)

            if full_mem.relations:
                lines.append("")
                lines.append("### Relations")
                lines.append("")
                for rel in full_mem.relations[:5]:  # Limit relations
                    lines.append(f"- {rel}")

            return [TextContent(type="text", text="\n".join(lines))]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Memory not found: `{memory_id}`\n\n"
                     f"💡 **Tips**:\n"
                     f"- Verify the ID is correct (copy from memos_search results)\n"
                     f"- The memory may have been deleted\n"
                     f"- Try `memos_search` to find the memory again"
            )]
    elif data:
        error_msg = data.get("message", "Unknown error")
        if "not found" in error_msg.lower() or status == 404:
            return [TextContent(
                type="text",
                text=f"❌ Memory not found: `{memory_id}`\n\n"
                     f"💡 **Tips**:\n"
                     f"- Verify the ID is correct (copy from memos_search results)\n"
                     f"- The memory may have been deleted\n"
                     f"- Try `memos_search` to find the memory again"
            )]
        return api_error_response("Get", error_msg)
    else:
        return api_error_response("Get", f"HTTP {status}")
