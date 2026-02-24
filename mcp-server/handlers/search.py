#!/usr/bin/env python3
"""
MemOS MCP Server Search Handlers

Handles memos_search, memos_search_context, memos_suggest tools.
Enhanced with P2: Temporal Graph Search for time-based queries.
Phase 1 Enhancement: Context compression for efficient token usage.
"""

from typing import Any

import re

import httpx

from api_client import api_call_with_retry
from config import MEMOS_URL, MEMOS_USER, NEO4J_HTTP_URL, NEO4J_PASSWORD, NEO4J_USER, logger
from cube_manager import ensure_cube_registered
from formatters import format_memories_for_display
from mcp.types import TextContent
from memory_analysis import suggest_search_queries
from models import (
    COMPACTION_THRESHOLD,
    PREVIEW_COUNT,
    CompactedSearchResult,
    should_compact,
    to_minimal,
)
from query_processing import (
    apply_keyword_rerank,
    detect_query_intent,
    filter_edges_by_intent,
    filter_memories_by_type,
    get_intent_description,
    parse_memory_type_prefix,
)

from handlers.utils import (
    api_error_response,
    cube_registration_error,
    get_cube_id_from_args,
)


async def _get_temporal_memories(
    client: httpx.AsyncClient,
    cube_id: str,
    top_k: int = 10,
    time_window_hours: int | None = None,
) -> list[dict]:
    """
    Query Neo4j for time-ordered memories (P2: Temporal Graph Enhancement).

    Args:
        client: httpx client
        cube_id: Memory cube ID (used for logging, actual filter uses MEMOS_USER)
        top_k: Number of results
        time_window_hours: Optional time window filter (last N hours)

    Returns:
        List of memory dicts with temporal_rank metadata
    """
    if not NEO4J_HTTP_URL or not NEO4J_USER or not NEO4J_PASSWORD:
        logger.debug("Neo4j config missing, skipping temporal query")
        return []

    neo4j_auth = (NEO4J_USER, NEO4J_PASSWORD)

    # Build time window filter
    time_filter = ""
    if time_window_hours:
        time_filter = f"""
        AND n.updated_at >= datetime() - duration({{hours: {time_window_hours}}})
        """

    # Use MEMOS_USER as the user_name filter (consistent with how memories are stored)
    # Note: status is 'activated' in MemOS tree_text mode (not 'LongTermMemory')
    cypher_query = f"""
    MATCH (n:Memory)
    WHERE n.user_name = $user_name
    AND n.status = 'activated'
    {time_filter}
    RETURN n.id AS id, n.memory AS memory, n.key AS key,
           n.updated_at AS updated_at, n.background AS background,
           n.tags AS tags
    ORDER BY n.updated_at DESC
    LIMIT $top_k
    """

    try:
        response = await client.post(
            NEO4J_HTTP_URL,
            json={
                "statements": [{
                    "statement": cypher_query,
                    "parameters": {"user_name": MEMOS_USER, "top_k": top_k}
                }]
            },
            auth=neo4j_auth
        )

        if response.status_code == 200:
            data = response.json()
            errors = data.get("errors", [])
            if errors:
                logger.warning(f"Neo4j temporal query errors: {errors}")
                return []

            rows = data.get("results", [{}])[0].get("data", [])
            memories = []
            for i, row in enumerate(rows):
                r = row.get("row", [])
                if len(r) >= 4:
                    mem = {
                        "id": r[0],
                        "memory": r[1],
                        "key": r[2],
                        "updated_at": r[3],
                        "background": r[4] if len(r) > 4 else "",
                        "tags": r[5] if len(r) > 5 else [],
                        "metadata": {
                            "relativity": 0.8 - (i * 0.05),  # Decay by rank
                            "temporal_rank": i + 1,
                            "source": "temporal_query",
                        }
                    }
                    memories.append(mem)
            logger.info(f"Temporal query returned {len(memories)} memories")
            return memories
        else:
            logger.warning(f"Neo4j temporal query failed: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"Temporal query error: {e}")
        return []


def _merge_temporal_results(
    search_data: dict,
    temporal_memories: list[dict],
    intent: str,
) -> dict:
    """
    Merge temporal query results with standard search results.

    For temporal intent, temporal results are prioritized.
    Duplicates (by id) are removed, keeping the higher-scored version.

    Args:
        search_data: Standard search API response data
        temporal_memories: Results from temporal Neo4j query
        intent: Query intent type

    Returns:
        Merged data dict
    """
    if not temporal_memories:
        return search_data

    # Get existing memory IDs from search results
    existing_ids = set()
    text_mem = search_data.get("text_mem", [])

    for bucket in text_mem:
        for mem in bucket.get("memories", []):
            mem_id = mem.get("id") or mem.get("metadata", {}).get("id")
            if mem_id:
                existing_ids.add(mem_id)

    # Filter out duplicates from temporal results
    new_temporal = []
    for mem in temporal_memories:
        if mem.get("id") not in existing_ids:
            new_temporal.append(mem)

    if not new_temporal:
        return search_data

    # For temporal intent, prepend temporal results as a special bucket
    if intent == "temporal":
        temporal_bucket = {
            "cube_id": "temporal",
            "memories": new_temporal,
            "_source": "temporal_graph_query",
        }
        # Insert at beginning for temporal priority
        search_data["text_mem"] = [temporal_bucket] + text_mem

    return search_data


async def handle_memos_search(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_search tool call with multi-graph view routing, temporal enhancement, and context compression."""
    cube_id = get_cube_id_from_args(arguments)
    raw_query = arguments.get("query", "")
    top_k = arguments.get("top_k", 10)
    compact = arguments.get("compact", True)  # Default to compact mode
    mem_type, cleaned_query = parse_memory_type_prefix(raw_query)
    query = cleaned_query if cleaned_query else raw_query

    # Multi-graph view routing: detect query intent
    intent = detect_query_intent(query)

    # Auto-register cube if needed (with helpful error message)
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return cube_registration_error(cube_id, reg_error)

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

        # P2: Temporal Graph Enhancement - add time-ordered results for temporal queries
        if intent == "temporal":
            # Parse time window from query (e.g., "最近24小时" → 24)
            time_window = None
            time_match = re.search(r"(\d+)\s*(?:小时|hour|h)", query, re.IGNORECASE)
            if time_match:
                time_window = int(time_match.group(1))
            elif any(kw in query.lower() for kw in ["今天", "today"]):
                time_window = 24
            elif any(kw in query.lower() for kw in ["本周", "this week", "week"]):
                time_window = 168  # 7 days

            temporal_memories = await _get_temporal_memories(
                client, cube_id, top_k=top_k, time_window_hours=time_window
            )
            result_data = _merge_temporal_results(result_data, temporal_memories, intent)

        # Apply multi-graph view filtering based on intent
        result_data = filter_edges_by_intent(result_data, intent)
        result_data = filter_memories_by_type(result_data, mem_type)
        keyword_query = cleaned_query if mem_type else query
        result_data = apply_keyword_rerank(result_data, keyword_query)

        # Extract all memories for counting and potential compression
        all_memories = _extract_search_memories(result_data)
        total_count = len(all_memories)

        # Apply context compression if enabled and threshold exceeded
        if compact and should_compact(total_count):
            logger.debug(f"Compacting search results: {total_count} > {COMPACTION_THRESHOLD}")
            preview = [to_minimal(m) for m in all_memories[:PREVIEW_COUNT]]
            compacted = CompactedSearchResult(
                preview=preview,
                total_count=total_count,
                omitted_count=total_count - len(preview),
                message="Use memos_get(memory_id=\"<id>\") for full details",
                query=raw_query,
                cube_id=cube_id,
            )
            text = compacted.to_display_text()

            # Add intent indicator if not default
            if intent != "default":
                intent_desc = get_intent_description(intent)
                text = f"*{intent_desc}*\n\n{text}"

            return [TextContent(type="text", text=text)]

        # Standard full display
        formatted = format_memories_for_display(result_data)

        # Add intent indicator if not default
        if intent != "default":
            intent_desc = get_intent_description(intent)
            formatted = f"*{intent_desc}*\n\n{formatted}"

        return [TextContent(type="text", text=formatted)]
    elif data:
        return api_error_response("Search", data.get("message", "Unknown error"))
    else:
        return api_error_response("Search", f"HTTP {status}")


def _extract_search_memories(data: dict) -> list[dict]:
    """Extract flat list of memories from search response data."""
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


async def handle_memos_search_context(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_search_context tool call with multi-graph view routing and temporal enhancement."""
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
        return cube_registration_error(cube_id, reg_error)

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

            # P2: Temporal Graph Enhancement
            if intent == "temporal":
                temporal_memories = await _get_temporal_memories(
                    client, cube_id, top_k=15
                )
                result_data = _merge_temporal_results(result_data, temporal_memories, intent)

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
            return api_error_response("Context search", data.get("message", "Unknown error"))
    else:
        return api_error_response("Context search", f"HTTP {response.status_code}")


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


async def handle_memos_context_resume(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_context_resume tool call - recover context after compaction."""
    cube_id = get_cube_id_from_args(arguments)

    # Auto-register cube
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return cube_registration_error(cube_id, reg_error)

    # Try temporal query first (last 24h from Neo4j)
    recent_memories = await _get_temporal_memories(
        client, cube_id, top_k=10, time_window_hours=24
    )

    # Fallback to API list if temporal query returns nothing
    if not recent_memories:
        success, data, status = await api_call_with_retry(
            client, "GET", f"{MEMOS_URL}/memories", cube_id,
            params={"user_id": MEMOS_USER, "mem_cube_id": cube_id, "limit": 10}
        )
        if success and data:
            recent_memories = _extract_search_memories(data.get("data", {}))

    # Format output
    lines = ["## Context Resumed", ""]

    if recent_memories:
        lines.append(f"**Recent memories** ({len(recent_memories)} items, last 24h):")
        lines.append("")
        for i, mem in enumerate(recent_memories[:10], 1):
            content = mem.get("memory", "") or mem.get("content", "")
            summary = content[:120].split("\n")[0]
            lines.append(f"{i}. {summary}")
        lines.append("")
    else:
        lines.append("No recent memories found in this cube.")
        lines.append("")

    lines.append("---")
    lines.append("**REMINDER**: Use MCP memos tools (`memos_save`, `memos_search`) for ALL memory operations.")
    lines.append("NEVER use `mkdir` or `Write` to create memory files.")

    return [TextContent(type="text", text="\n".join(lines))]
