#!/usr/bin/env python3
"""
MemOS MCP Server Query Processing Module

Contains query processing functions for keyword extraction, matching, and reranking.
"""

import json
import re
from typing import Any

from config import (
    _KEYWORD_STOPWORDS,
    KEYWORD_ENHANCER_AVAILABLE,
    MEMORY_TYPES,
)


# Import enhanced functions if available
if KEYWORD_ENHANCER_AVAILABLE:
    from keyword_enhancer import (
        extract_keywords_enhanced,
        keyword_match_score_enhanced,
    )
else:
    extract_keywords_enhanced = None
    keyword_match_score_enhanced = None


def parse_memory_type_prefix(query: str) -> tuple[str | None, str]:
    """
    Parse memory type prefix from query string.

    Returns:
        (memory_type, remaining_query)
    """
    if not query:
        return None, ""
    match = re.match(r"^\s*\[?([A-Z_]+)\]?\s*[:\-]?\s*(.*)$", query)
    if not match:
        return None, query.strip()
    mem_type = match.group(1)
    rest = match.group(2).strip()
    if mem_type in MEMORY_TYPES:
        return mem_type, rest
    return None, query.strip()


# ============================================================================
# Multi-Graph View Routing (MAGMA-inspired)
# ============================================================================

# Intent to graph type mapping
INTENT_TO_GRAPHS: dict[str, list[str]] = {
    "causal": ["CAUSE", "CONDITION"],       # Why did X happen? What caused Y?
    "related": ["RELATE"],                   # What's related to X?
    "conflict": ["CONFLICT"],                # What conflicts with X?
    "temporal": ["FOLLOWS"],                 # What happened before/after X?
    "default": ["CAUSE", "RELATE", "CONDITION"],  # General queries
}


def detect_query_intent(query: str) -> str:
    """
    Detect query intent for multi-graph routing.

    Returns one of: "causal", "related", "conflict", "temporal", "default"
    """
    query_lower = query.lower()

    # Causal intent patterns (Chinese + English)
    causal_patterns = [
        r"为什么", r"why", r"原因", r"cause", r"导致", r"因为",
        r"根本原因", r"root\s*cause", r"怎么.*出错", r"how.*fail",
        r"什么.*引起", r"what.*caused", r"出了什么问题",
    ]
    for pattern in causal_patterns:
        if re.search(pattern, query_lower):
            return "causal"

    # Conflict intent patterns
    conflict_patterns = [
        r"冲突", r"conflict", r"矛盾", r"contradict", r"不一致",
        r"inconsisten", r"问题.*之间", r"clash",
    ]
    for pattern in conflict_patterns:
        if re.search(pattern, query_lower):
            return "conflict"

    # Temporal intent patterns
    temporal_patterns = [
        r"什么时候", r"when", r"之前", r"before", r"之后", r"after",
        r"最近", r"recent", r"先.*后", r"顺序", r"timeline", r"历史",
        r"上次", r"last\s*time", r"earlier", r"previously",
    ]
    for pattern in temporal_patterns:
        if re.search(pattern, query_lower):
            return "temporal"

    # Related intent patterns (general association)
    related_patterns = [
        r"相关", r"related", r"关联", r"有关", r"涉及",
        r"association", r"connect", r"link",
    ]
    for pattern in related_patterns:
        if re.search(pattern, query_lower):
            return "related"

    return "default"


def get_graphs_for_intent(intent: str) -> list[str]:
    """Get the list of graph/edge types to query for a given intent."""
    return INTENT_TO_GRAPHS.get(intent, INTENT_TO_GRAPHS["default"])


def filter_edges_by_intent(data: dict, intent: str) -> dict:
    """
    Filter edges in search results based on query intent.

    This implements MAGMA-style multi-graph view routing:
    - Only keep edges of types relevant to the intent
    - Boost nodes that have matching edges

    Args:
        data: Search results data with text_mem containing nodes and edges
        intent: Query intent from detect_query_intent()

    Returns:
        Filtered data with only relevant edge types
    """
    allowed_edge_types = get_graphs_for_intent(intent)

    text_mems = data.get("text_mem", [])
    for cube_data in text_mems:
        mem_data = cube_data.get("memories", {})

        # Handle tree_text mode with nodes and edges
        if isinstance(mem_data, dict) and "edges" in mem_data:
            edges = mem_data.get("edges", [])
            nodes = mem_data.get("nodes", [])

            # Filter edges by allowed types
            filtered_edges = [
                edge for edge in edges
                if edge.get("type") in allowed_edge_types
            ]
            mem_data["edges"] = filtered_edges

            # Boost nodes that have matching edges
            if filtered_edges:
                # Collect node IDs that have filtered edges
                boosted_ids = set()
                for edge in filtered_edges:
                    boosted_ids.add(edge.get("source", ""))
                    boosted_ids.add(edge.get("target", ""))

                # Add a boost score to metadata for reranking
                for node in nodes:
                    node_id = node.get("id", "")
                    metadata = node.get("metadata", {})
                    if node_id in boosted_ids:
                        # Add intent_match boost
                        current_relativity = metadata.get("relativity", 0.0)
                        metadata["relativity"] = current_relativity + 0.5
                        metadata["intent_matched"] = True

    return data


def get_intent_description(intent: str) -> str:
    """Get human-readable description of query intent."""
    descriptions = {
        "causal": "🔍 因果分析 (Causal Analysis)",
        "related": "🔗 关联查询 (Related Search)",
        "conflict": "⚠️ 冲突检测 (Conflict Detection)",
        "temporal": "📅 时序查询 (Temporal Search)",
        "default": "📚 综合查询 (General Search)",
    }
    return descriptions.get(intent, descriptions["default"])


def extract_keywords(query: str) -> list[str]:
    """Extract keywords from query with stopword filtering."""
    if KEYWORD_ENHANCER_AVAILABLE and extract_keywords_enhanced is not None:
        return extract_keywords_enhanced(query, _KEYWORD_STOPWORDS)
    # Fallback to basic implementation
    if not query:
        return []
    raw_tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", query)
    keywords: list[str] = []
    seen = set()
    for token in raw_tokens:
        if not token:
            continue
        if re.search(r"[\u4e00-\u9fff]", token):
            if len(token) < 2:
                continue
            if token in _KEYWORD_STOPWORDS:
                continue
            if token not in seen:
                keywords.append(token)
                seen.add(token)
            continue
        lowered = token.lower()
        if len(lowered) < 2:
            continue
        if lowered in _KEYWORD_STOPWORDS:
            continue
        if lowered not in seen:
            keywords.append(lowered)
            seen.add(lowered)
    return keywords


def keyword_match_score(
    text: str,
    keywords: list[str],
    metadata: dict | None = None,
    enable_fuzzy: bool = True
) -> float:
    """
    Calculate keyword match score with optional fuzzy matching.

    Args:
        text: The text to match against
        keywords: List of keywords
        metadata: Optional metadata with 'key' and 'tags' fields
        enable_fuzzy: Enable fuzzy matching (default True)

    Returns:
        Match score
    """
    if KEYWORD_ENHANCER_AVAILABLE and keyword_match_score_enhanced is not None:
        return keyword_match_score_enhanced(
            text, keywords, metadata, enable_fuzzy=enable_fuzzy
        )
    # Fallback to basic implementation
    if not text or not keywords:
        return 0.0
    text_lower = text.lower()
    matched = 0
    score = 0.0
    for kw in keywords:
        if re.search(r"[\u4e00-\u9fff]", kw):
            if kw in text:
                matched += 1
                score += 2.0
            continue
        if re.search(rf"\b{re.escape(kw)}\b", text_lower):
            matched += 1
            score += 2.0
        elif kw in text_lower:
            matched += 1
            score += 1.2
    if matched:
        score += matched / max(len(keywords), 1)
    return score


def apply_keyword_rerank(data: dict, query: str, enable_fuzzy: bool = True) -> dict:
    """
    Apply keyword-based reranking to search results.

    Args:
        data: Search results data
        query: Original query string
        enable_fuzzy: Enable fuzzy matching

    Returns:
        Reranked data
    """
    keywords = extract_keywords(query)
    if not keywords:
        return data
    text_mems = data.get("text_mem", [])
    for cube_data in text_mems:
        mem_data = cube_data.get("memories", [])
        if isinstance(mem_data, dict) and "nodes" in mem_data:
            nodes = mem_data.get("nodes", [])
            nodes.sort(
                key=lambda mem: (
                    mem.get("metadata", {}).get("relativity", 0.0)
                    + keyword_match_score(
                        mem.get("memory", ""),
                        keywords,
                        mem.get("metadata"),
                        enable_fuzzy
                    )
                ),
                reverse=True,
            )
        elif isinstance(mem_data, list):
            mem_data.sort(
                key=lambda mem: (
                    mem.get("metadata", {}).get("relativity", 0.0)
                    + keyword_match_score(
                        mem.get("memory", ""),
                        keywords,
                        mem.get("metadata"),
                        enable_fuzzy
                    )
                ),
                reverse=True,
            )
    return data


def filter_memories_by_type(data: dict, mem_type: str | None) -> dict:
    """Filter memories to only include those of the specified type."""
    if not mem_type:
        return data
    text_mems = data.get("text_mem", [])
    for cube_data in text_mems:
        mem_data = cube_data.get("memories", [])
        if isinstance(mem_data, dict) and "nodes" in mem_data:
            nodes = mem_data.get("nodes", [])
            filtered_nodes = [
                node for node in nodes
                if re.match(rf"^\[{mem_type}\]", node.get("memory", ""))
            ]
            if "edges" in mem_data:
                kept_ids = {node.get("id", "") for node in filtered_nodes}
                edges = mem_data.get("edges", [])
                mem_data["edges"] = [
                    edge for edge in edges
                    if edge.get("source") in kept_ids and edge.get("target") in kept_ids
                ]
            mem_data["nodes"] = filtered_nodes
        elif isinstance(mem_data, list):
            mem_data[:] = [
                mem for mem in mem_data
                if re.match(rf"^\[{mem_type}\]", mem.get("memory", ""))
            ]
    return data


def extract_memories_from_response(data: dict) -> list[dict]:
    """
    Extract memory nodes from API response, handling both flat and tree_text modes.

    Args:
        data: API response data containing text_mem

    Returns:
        List of memory node dictionaries
    """
    memories = []
    text_mems = data.get("text_mem", [])

    for cube_data in text_mems:
        mem_data = cube_data.get("memories", [])

        # Handle tree_text mode (dict with "nodes" key)
        if isinstance(mem_data, dict) and "nodes" in mem_data:
            memories.extend(mem_data["nodes"])
        # Handle flat mode (list of memories)
        elif isinstance(mem_data, list):
            memories.extend(mem_data)

    return memories


_VALID_MEMORY_TYPES = {
    "BUGFIX", "ERROR_PATTERN", "DECISION", "GOTCHA", "CODE_PATTERN",
    "CONFIG", "FEATURE", "MILESTONE", "PROGRESS",
}

_TYPE_PATTERN = re.compile(r"^\[([A-Z_]+)\]")


def _extract_type_from_text(text: str) -> str | None:
    """Extract [TYPE] prefix from text if it is a known memory type."""
    m = _TYPE_PATTERN.match(text)
    if m and m.group(1) in _VALID_MEMORY_TYPES:
        return m.group(1)
    return None


def _decode_source_entry(entry: Any) -> dict | None:
    """
    Decode a single source entry which may be single or double JSON-encoded.

    Neo4j stores sources as JSON strings; the API may return them already
    parsed or still as strings.  Some entries are double-encoded:
      '"{\\"type\\": \\"chat\\", ...}"'  →  parse twice to get the dict.
    """
    if isinstance(entry, dict):
        return entry
    if not isinstance(entry, str):
        return None
    try:
        result = json.loads(entry)
        # Double-encoded: first parse returned another string
        if isinstance(result, str):
            result = json.loads(result)
        return result if isinstance(result, dict) else None
    except Exception:
        return None


def _extract_type_from_sources(sources: list) -> str | None:
    """
    Fallback: extract type from any source entry's content field.

    tree_text backend strips [TYPE] from `memory` during LLM extraction,
    but the original content with [TYPE] prefix is preserved in sources.
    Scans all source entries (not just sources[0]) because some nodes may
    share a source that has the type prefix at a later index.
    """
    if not sources:
        return None
    for entry in sources:
        decoded = _decode_source_entry(entry)
        if decoded:
            content = decoded.get("content", "")
            found = _extract_type_from_text(content)
            if found:
                return found
    return None


def extract_mcp_type(memory: dict) -> str:
    """
    Extract the user-specified MCP type from a raw memory dict.

    This is the single source of truth for type classification across
    all MCP tools (stats, list, get, search).

    Detection order:
    1. [TYPE] prefix in `memory` field (flat-mode saves where prefix is kept)
    2. [TYPE] prefix in sources content (tree_text mode — LLM extractor strips
       the prefix from `memory`, but sources retain the original message)
    3. LLM-inferred reasoning nodes (Neo4j graph-generated) → "INFERRED"
    4. Default → "PROGRESS"

    Args:
        memory: Raw memory dict from API response.
                Can have sources at top-level or inside metadata.

    Returns:
        One of: BUGFIX, ERROR_PATTERN, DECISION, GOTCHA, CODE_PATTERN,
                CONFIG, FEATURE, MILESTONE, PROGRESS, INFERRED
    """
    # 1. [TYPE] prefix in memory text (flat-mode)
    mem_type = _extract_type_from_text(memory.get("memory", ""))
    if mem_type:
        return mem_type

    # 2. [TYPE] prefix in sources (tree_text mode)
    sources = (
        memory.get("sources")
        or memory.get("metadata", {}).get("sources")
        or []
    )
    mem_type = _extract_type_from_sources(sources)
    if mem_type:
        return mem_type

    # 3. LLM-inferred reasoning nodes auto-generated by the graph DB
    #    They have metadata.type == "reasoning" or key starts with "InferredFact"
    meta = memory.get("metadata", memory)  # flat or nested
    node_type = meta.get("type") if isinstance(meta, dict) else None
    key = memory.get("key") or (meta.get("key") if isinstance(meta, dict) else None) or ""
    if node_type == "reasoning" or str(key).startswith("InferredFact"):
        return "INFERRED"

    return "PROGRESS"


def compute_memory_stats(data: dict) -> tuple[dict[str, int], int]:
    """
    Compute memory type statistics from API response.

    Uses extract_mcp_type() for consistent classification across all tools.

    Args:
        data: API response data

    Returns:
        tuple: (stats_dict: {type: count}, total_count)
    """
    memories = extract_memories_from_response(data)
    stats: dict[str, int] = {}
    total = 0

    for mem in memories:
        total += 1
        mem_type = extract_mcp_type(mem)
        stats[mem_type] = stats.get(mem_type, 0) + 1

    return stats, total
