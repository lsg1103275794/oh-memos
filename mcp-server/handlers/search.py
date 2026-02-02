#!/usr/bin/env python3
"""
MemOS MCP Server Search Handlers

Handles memos_search, memos_search_context, memos_suggest tools.
"""

from typing import Any

import httpx

from api_client import api_call_with_retry
from config import MEMOS_URL, MEMOS_USER
from cube_manager import ensure_cube_registered
from formatters import format_memories_for_display
from mcp.types import TextContent
from memory_analysis import suggest_search_queries
from query_processing import (
    apply_keyword_rerank,
    detect_query_intent,
    filter_edges_by_intent,
    filter_memories_by_type,
    get_intent_description,
    parse_memory_type_prefix,
)

from handlers.utils import error_response, get_cube_id_from_args


async def handle_memos_search(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_search tool call with multi-graph view routing."""
    cube_id = get_cube_id_from_args(arguments)
    raw_query = arguments.get("query", "")
    top_k = arguments.get("top_k", 10)
    mem_type, cleaned_query = parse_memory_type_prefix(raw_query)
    query = cleaned_query if cleaned_query else raw_query

    # Multi-graph view routing: detect query intent
    intent = detect_query_intent(query)

    # Auto-register cube if needed (with helpful error message)
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return error_response(f"## Cube Registration Failed\n\n{reg_error}")

    success, data, status = await api_call_with_retry(
        client, "POST", f"{MEMOS_URL}/search", cube_id,
        json={
            "user_id": MEMOS_USER,
            "query": query,
            "install_cube_ids": [cube_id],
            "top_k": top_k
        }
    )

    if success and data:
        result_data = data.get("data", {})

        # Apply multi-graph view filtering based on intent
        result_data = filter_edges_by_intent(result_data, intent)

        result_data = filter_memories_by_type(result_data, mem_type)
        keyword_query = cleaned_query if mem_type else query
        result_data = apply_keyword_rerank(result_data, keyword_query)
        formatted = format_memories_for_display(result_data)

        # Add intent indicator if not default
        if intent != "default":
            intent_desc = get_intent_description(intent)
            formatted = f"*{intent_desc}*\n\n{formatted}"

        return [TextContent(type="text", text=formatted)]
    elif data:
        return error_response(f"Search failed: {data.get('message', 'Unknown error')}")
    else:
        return error_response(f"API error: {status}")


async def handle_memos_search_context(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_search_context tool call with multi-graph view routing."""
    cube_id = get_cube_id_from_args(arguments)
    raw_query = arguments.get("query", "")
    context = arguments.get("context", [])
    mem_type, cleaned_query = parse_memory_type_prefix(raw_query)
    query = cleaned_query if cleaned_query else raw_query

    # Multi-graph view routing: detect intent from query + context
    context_text = " ".join(msg.get("content", "") for msg in context[-5:])
    intent = detect_query_intent(f"{query} {context_text}")

    # Auto-register cube if needed
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return error_response(f"## Cube Registration Failed\n\n{reg_error}")

    # Format context as chat_history for the API
    chat_history = []
    for msg in context[-10:]:  # Last 10 messages
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content:
            chat_history.append({"role": role, "content": content})

    response = await client.post(
        f"{MEMOS_URL}/search",
        json={
            "user_id": MEMOS_USER,
            "query": query,
            "readable_cube_ids": [cube_id],
            "enable_context_analysis": True,
            "chat_history": chat_history,
            "top_k": 15,
        }
    )

    if response.status_code == 200:
        data = response.json()
        if data.get("code") == 200:
            results = []
            intent_desc = get_intent_description(intent)
            results.append(f"## {intent_desc}")
            results.append("")
            result_data = data.get("data", {})

            # Apply multi-graph view filtering
            result_data = filter_edges_by_intent(result_data, intent)

            result_data = filter_memories_by_type(result_data, mem_type)
            keyword_query = cleaned_query if mem_type else query
            result_data = apply_keyword_rerank(result_data, keyword_query)
            formatted = format_memories_for_display(result_data)
            if context:
                results.append(f"*Analyzed with {len(context)} context messages*")
                results.append("")
            results.append(formatted)
            return [TextContent(type="text", text="\n".join(results))]
        else:
            # Fallback to standard search
            fallback_response = await client.post(
                f"{MEMOS_URL}/search",
                json={
                    "user_id": MEMOS_USER,
                    "query": query,
                    "install_cube_ids": [cube_id]
                }
            )
            if fallback_response.status_code == 200:
                fallback_data = fallback_response.json()
                if fallback_data.get("code") == 200:
                    result_data = fallback_data.get("data", {})
                    result_data = filter_edges_by_intent(result_data, intent)
                    result_data = filter_memories_by_type(result_data, mem_type)
                    keyword_query = cleaned_query if mem_type else query
                    result_data = apply_keyword_rerank(result_data, keyword_query)
                    formatted = format_memories_for_display(result_data)
                    return [TextContent(type="text", text=f"## Search Results (fallback)\n\n{formatted}")]
            return error_response(f"Search failed: {data.get('message', 'Unknown error')}")
    else:
        return error_response(f"API error: {response.status_code}")


async def handle_memos_suggest(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_suggest tool call."""
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
