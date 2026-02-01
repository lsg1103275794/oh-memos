#!/usr/bin/env python3
"""
MemOS MCP Server Memory Handlers

Handles memos_save, memos_list, memos_list_v2, memos_get_stats tools.
"""

from typing import Any

import httpx
from mcp.types import TextContent

from api_client import api_call_with_retry
from config import MEMOS_URL, MEMOS_USER
from cube_manager import ensure_cube_registered
from formatters import format_memories_for_display
from memory_analysis import detect_memory_type
from query_processing import compute_memory_stats
from handlers.utils import get_cube_id_from_args, error_response


async def handle_memos_save(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_save tool call."""
    cube_id = get_cube_id_from_args(arguments)
    content = arguments.get("content", "")
    explicit_type = arguments.get("memory_type")

    # Detect type and confidence
    if explicit_type:
        memory_type = explicit_type
        confidence = 1.0
    else:
        memory_type, confidence = detect_memory_type(content)

    # Reject low-confidence PROGRESS - require explicit type
    if confidence < 0.6 and memory_type == "PROGRESS":
        return error_response(
            "## 需要显式指定 memory_type\n\n"
            f"内容分析未能确定准确的记忆类型 (置信度: {confidence:.0%})，默认为 PROGRESS。\n\n"
            "**请显式指定 `memory_type` 参数**，可选类型：\n"
            "- `ERROR_PATTERN` - 错误模式 + 解决方案\n"
            "- `BUGFIX` - Bug 修复详情\n"
            "- `DECISION` - 技术决策 + 理由\n"
            "- `GOTCHA` - 非显而易见的陷阱\n"
            "- `CODE_PATTERN` - 可复用代码模板\n"
            "- `CONFIG` - 配置变更\n"
            "- `FEATURE` - 新功能\n"
            "- `MILESTONE` - 重大里程碑\n"
            "- `PROGRESS` - 仅用于纯进度汇报\n\n"
            "**示例**: `memos_save(content=\"...\", memory_type=\"BUGFIX\")`"
        )

    # Prepend memory type if not already present
    if not content.startswith(f"[{memory_type}]"):
        content = f"[{memory_type}] {content}"

    # Auto-register cube if needed
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return error_response(f"## Cube Registration Failed\n\n{reg_error}")

    success, data, status = await api_call_with_retry(
        client, "POST", f"{MEMOS_URL}/memories", cube_id,
        json={
            "user_id": MEMOS_USER,
            "mem_cube_id": cube_id,
            "memory_content": content
        }
    )

    if success:
        return [TextContent(type="text", text=f"✅ Memory saved as [{memory_type}] (confidence: {confidence:.0%})")]
    elif data:
        return error_response(f"Save failed: {data.get('message', 'Unknown error')}")
    else:
        return error_response(f"API error: {status}")


async def handle_memos_list(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_list and memos_list_v2 tool calls."""
    cube_id = get_cube_id_from_args(arguments)
    limit = arguments.get("limit", 20)
    memory_type = arguments.get("memory_type")

    # Auto-register cube
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return error_response(f"## Cube Registration Failed\n\n{reg_error}")

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
        formatted = format_memories_for_display(data.get("data", {}))
        return [TextContent(type="text", text=formatted)]
    elif data:
        return error_response(f"List failed: {data.get('message', 'Unknown error')}")
    else:
        return error_response(f"API error: {status}")


async def handle_memos_get_stats(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_get_stats tool call."""
    cube_id = get_cube_id_from_args(arguments)

    # Auto-register cube if needed
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return error_response(f"## Cube Registration Failed\n\n{reg_error}")

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
        return error_response(f"Stats failed: {data.get('message', 'Unknown error')}")
    else:
        return error_response(f"API error: {status}")
