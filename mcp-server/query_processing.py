#!/usr/bin/env python3
"""
MemOS MCP Server Query Processing Module

Contains query processing functions for keyword extraction, matching, and reranking.
"""

import re
from typing import Optional

from config import (
    MEMORY_TYPES,
    KEYWORD_ENHANCER_AVAILABLE,
    _KEYWORD_STOPWORDS,
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
    metadata: Optional[dict] = None,
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


def compute_memory_stats(data: dict) -> tuple[dict[str, int], int]:
    """
    Compute memory type statistics from API response.

    Args:
        data: API response data

    Returns:
        tuple: (stats_dict: {type: count}, total_count)
    """
    memories = extract_memories_from_response(data)
    stats: dict[str, int] = {}
    total = 0

    for mem in memories:
        memory_text = mem.get("memory", "")
        total += 1
        type_match = re.match(r"^\[([A-Z_]+)\]", memory_text)
        mem_type = type_match.group(1) if type_match else "PROGRESS"
        stats[mem_type] = stats.get(mem_type, 0) + 1

    return stats, total
