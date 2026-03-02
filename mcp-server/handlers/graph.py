#!/usr/bin/env python3
"""
MemOS MCP Server Graph Handlers

Handles memos_trace_path, memos_get_graph, memos_export_schema, memos_impact tools.
"""

from typing import Any

import httpx

from config import (
    MEMOS_URL,
    MEMOS_USER,
    NEO4J_HTTP_URL,
    NEO4J_PASSWORD,
    NEO4J_USER,
    _registered_cubes,
    logger,
)
from cube_manager import ensure_cube_registered
from mcp.types import TextContent
from query_processing import (
    detect_query_intent,
    extract_memories_from_response,
    get_graphs_for_intent,
    get_intent_description,
)

from handlers.utils import (
    ERR_NEO4J_CONFIG,
    ERR_PARAM_MISSING,
    api_error_response,
    cube_registration_error,
    error_response,
    get_cube_id_from_args,
)


async def handle_memos_trace_path(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_trace_path tool call."""
    cube_id = get_cube_id_from_args(arguments)
    source_id = arguments.get("source_id", "")
    target_id = arguments.get("target_id", "")
    max_depth = min(arguments.get("max_depth", 3), 10)

    if not source_id or not target_id:
        return error_response(
            "Both source_id and target_id are required",
            error_code=ERR_PARAM_MISSING,
            suggestions=[
                "Get node IDs from memos_search or memos_get_graph",
                "Example: `memos_trace_path(source_id=\"uuid-1\", target_id=\"uuid-2\")`",
            ],
        )

    # Auto-register cube if needed
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return cube_registration_error(cube_id, reg_error)

    # Call the trace_path API endpoint
    try:
        response = await client.post(
            f"{MEMOS_URL}/product/graph/trace_path",
            json={
                "user_id": MEMOS_USER,
                "source_id": source_id,
                "target_id": target_id,
                "max_depth": max_depth,
                "include_all_paths": False,
                "mem_cube_id": cube_id,
            }
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                trace_data = data.get("data", {})
                found = trace_data.get("path_found") or trace_data.get("found", False)
                paths = trace_data.get("paths", [])
                source_node = trace_data.get("source", {})
                target_node = trace_data.get("target", {})

                results = []
                results.append("## 🔗 Path Trace Results")
                results.append("")

                if source_node:
                    source_mem = source_node.get("memory", "")[:80]
                    results.append(f"**Source**: {source_mem}...")
                if target_node:
                    target_mem = target_node.get("memory", "")[:80]
                    results.append(f"**Target**: {target_mem}...")
                results.append("")

                if not found:
                    results.append(f"*No path found within {max_depth} hops.*")
                    results.append("")
                    results.append("Suggestions:")
                    results.append("- Try increasing max_depth (up to 10)")
                    results.append("- Verify the node IDs are correct")
                    results.append("- The nodes may not be connected in the graph")
                else:
                    for i, path in enumerate(paths, 1):
                        length = path.get("length", 0)
                        nodes = path.get("nodes", [])
                        edges = path.get("edges", [])

                        # API may return path_found=true but empty nodes/edges
                        # Fall back to direct Neo4j query in that case
                        if not nodes and NEO4J_HTTP_URL and NEO4J_USER and NEO4J_PASSWORD:
                            raise ValueError("API returned empty path nodes, falling back to Neo4j")

                        results.append(f"### Path {i} (Length: {length})")
                        results.append("")
                        results.append("```")

                        for j, node in enumerate(nodes):
                            node_mem = node.get("memory", "")[:60]
                            results.append(f"[{j+1}] {node_mem}...")

                            if j < len(edges):
                                edge = edges[j]
                                edge_type = edge.get("type", "UNKNOWN")
                                results.append("    │")
                                results.append(f"    └── {edge_type} ──>")

                        results.append("```")
                        results.append("")

                return [TextContent(type="text", text="\n".join(results))]
            else:
                return api_error_response("Trace path", data.get("message", "Unknown error"))
        else:
            return api_error_response("Trace path", f"HTTP {response.status_code}")

    except Exception as e:
        logger.warning(f"Falling back to direct Neo4j query: {e}")

        if not NEO4J_HTTP_URL or not NEO4J_USER or not NEO4J_PASSWORD:
            return error_response(
                "Neo4j configuration missing",
                error_code=ERR_NEO4J_CONFIG,
                suggestions=[
                    "Set NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD in .env",
                    "Example: NEO4J_HTTP_URL=http://localhost:7474/db/neo4j/tx/commit",
                ],
            )

        neo4j_auth = (NEO4J_USER, NEO4J_PASSWORD)

        cypher_query = f"""
        MATCH (source:Memory), (target:Memory)
        WHERE source.id = $source_id AND target.id = $target_id
        MATCH path = shortestPath((source)-[*1..{max_depth}]-(target))
        RETURN [n IN nodes(path) | {{id: n.id, memory: n.memory}}] AS nodes,
               [r IN relationships(path) | {{type: type(r)}}] AS rels
        LIMIT 1
        """

        neo4j_response = await client.post(
            NEO4J_HTTP_URL,
            json={
                "statements": [{
                    "statement": cypher_query,
                    "parameters": {"source_id": source_id, "target_id": target_id}
                }]
            },
            auth=neo4j_auth
        )

        results = ["## 🔗 Path Trace (Direct Query)"]
        results.append("")

        if neo4j_response.status_code == 200:
            neo4j_data = neo4j_response.json()
            rows = neo4j_data.get("results", [{}])[0].get("data", [])

            if rows:
                row = rows[0].get("row", [[], []])
                nodes = row[0] if len(row) > 0 else []
                rels = row[1] if len(row) > 1 else []

                results.append("```")
                for j, node in enumerate(nodes):
                    node_mem = (node.get("memory") or "")[:60]
                    results.append(f"[{j+1}] {node_mem}...")
                    if j < len(rels):
                        rel_type = rels[j].get("type", "?")
                        results.append(f"    └── {rel_type} ──>")
                results.append("```")
            else:
                results.append(f"*No path found within {max_depth} hops.*")
        else:
            results.append(f"*Neo4j query error: {neo4j_response.status_code}*")

        return [TextContent(type="text", text="\n".join(results))]


async def handle_memos_get_graph(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_get_graph tool call with multi-graph view routing."""
    cube_id = get_cube_id_from_args(arguments)
    query = arguments.get("query", "")

    # Multi-graph view routing: detect query intent
    intent = detect_query_intent(query)
    target_edge_types = get_graphs_for_intent(intent)

    # Auto-register cube if needed
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return cube_registration_error(cube_id, reg_error)

    if not NEO4J_HTTP_URL or not NEO4J_USER or not NEO4J_PASSWORD:
        return error_response(
            "Neo4j configuration missing",
            error_code=ERR_NEO4J_CONFIG,
            suggestions=[
                "Set NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD in .env",
                "Example: NEO4J_HTTP_URL=http://localhost:7474/db/neo4j/tx/commit",
            ],
        )

    neo4j_auth = (NEO4J_USER, NEO4J_PASSWORD)

    # First search for relevant memories using MemOS API
    search_response = await client.post(
        f"{MEMOS_URL}/search",
        json={
            "user_id": MEMOS_USER,
            "query": query,
            "install_cube_ids": [cube_id]
        }
    )

    # Use helper to extract memories (handles tree_text mode)
    memories = []
    if search_response.status_code == 200:
        data = search_response.json()
        if data.get("code") == 200:
            memories = extract_memories_from_response(data.get("data", {}))
        else:
            # Try to re-register and search again
            _registered_cubes.discard(cube_id)
            retry_success, _ = await ensure_cube_registered(client, cube_id, force=True)
            if retry_success:
                retry_search = await client.post(
                    f"{MEMOS_URL}/search",
                    json={
                        "user_id": MEMOS_USER,
                        "query": query,
                        "install_cube_ids": [cube_id]
                    }
                )
                if retry_search.status_code == 200:
                    retry_data = retry_search.json()
                    if retry_data.get("code") == 200:
                        memories = extract_memories_from_response(retry_data.get("data", {}))

    # Build dynamic Cypher query based on intent (multi-graph view routing)
    # Use IDs from MemOS vector search instead of string matching (language-agnostic)
    edge_types_cypher = "|".join(target_edge_types)

    if memories:
        # Strategy 1: find relationships BETWEEN the searched nodes (most accurate)
        mem_ids = [m.get("id") or m.get("metadata", {}).get("id") for m in memories[:10] if m.get("id") or m.get("metadata", {}).get("id")]
        if mem_ids:
            id_list = ", ".join(f'"{mid}"' for mid in mem_ids)
            cypher_query = f"""
            MATCH (a)-[r:{edge_types_cypher}]->(b)
            WHERE a.id IN [{id_list}] OR b.id IN [{id_list}]
            RETURN a.id as source_id, a.memory as source_memory,
                   type(r) as relation_type,
                   b.id as target_id, b.memory as target_memory
            LIMIT 20
            """
        else:
            # Fallback: keyword on individual terms
            first_word = query.split()[0] if query.split() else query
            cypher_query = f"""
            MATCH (a)-[r:{edge_types_cypher}]->(b)
            WHERE a.memory CONTAINS $keyword OR b.memory CONTAINS $keyword
            RETURN a.id as source_id, a.memory as source_memory,
                   type(r) as relation_type,
                   b.id as target_id, b.memory as target_memory
            LIMIT 20
            """
    else:
        # No search results: try first token as keyword
        first_word = query.split()[0] if query.split() else query
        cypher_query = f"""
        MATCH (a)-[r:{edge_types_cypher}]->(b)
        WHERE a.memory CONTAINS $keyword OR b.memory CONTAINS $keyword
        RETURN a.id as source_id, a.memory as source_memory,
               type(r) as relation_type,
               b.id as target_id, b.memory as target_memory
        LIMIT 20
        """

    # Determine parameters for the Cypher statement
    use_id_strategy = memories and any(
        m.get("id") or m.get("metadata", {}).get("id") for m in memories[:10]
    )
    keyword_param = query.split()[0] if query.split() else query

    neo4j_response = await client.post(
        NEO4J_HTTP_URL,
        json={
            "statements": [{
                "statement": cypher_query,
                "parameters": {} if use_id_strategy else {"keyword": keyword_param}
            }]
        },
        auth=neo4j_auth
    )

    results = []
    intent_desc = get_intent_description(intent)
    results.append(f"## 🧠 Knowledge Graph: {cube_id}")
    results.append(f"Query: `{query}` | {intent_desc}")
    results.append(f"*Filtering edges: {', '.join(target_edge_types)}*")
    results.append("")

    # Display memories from search
    if memories:
        results.append("### 📝 Related Memories")
        results.append("")
        for i, mem in enumerate(memories[:5], 1):
            memory = mem.get("memory", "")
            first_line = memory.split("\n")[0][:100]
            results.append(f"{i}. {first_line}")
        results.append("")

    # Display relationships from Neo4j
    if neo4j_response.status_code == 200:
        neo4j_data = neo4j_response.json()
        rows = neo4j_data.get("results", [{}])[0].get("data", [])

        if rows:
            results.append("### 🔗 Relationships")
            results.append("```")
            for row in rows:
                r = row.get("row", [])
                if len(r) >= 5:
                    source_mem = (r[1] or "")[:50]
                    rel_type = r[2]
                    target_mem = (r[4] or "")[:50]

                    if rel_type == "CAUSE":
                        arrow = "──CAUSE──>"
                    elif rel_type == "RELATE":
                        arrow = "──RELATE──"
                    elif rel_type == "CONFLICT":
                        arrow = "══CONFLICT══"
                    else:
                        arrow = f"──{rel_type}──>"

                    results.append(f"[{source_mem}...]")
                    results.append(f"    {arrow}")
                    results.append(f"[{target_mem}...]")
                    results.append("")
            results.append("```")
        else:
            results.append("*No relationships found for this query.*")
    else:
        results.append(f"*Neo4j query error: {neo4j_response.status_code}*")

    return [TextContent(type="text", text="\n".join(results))]


async def handle_memos_export_schema(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_export_schema tool call."""
    cube_id = get_cube_id_from_args(arguments)
    sample_size = min(max(arguments.get("sample_size", 100), 10), 1000)

    # Auto-register cube if needed
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return cube_registration_error(cube_id, reg_error)

    try:
        response = await client.post(
            f"{MEMOS_URL}/graph/schema",
            json={
                "user_id": MEMOS_USER,
                "mem_cube_id": cube_id,
                "sample_size": sample_size,
            }
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                schema = data.get("data", {})

                results = []
                results.append("## 📊 Knowledge Graph Schema")
                results.append("")

                # Overview
                results.append("### Overview")
                results.append(f"- **Total Nodes**: {schema.get('total_nodes', 0)}")
                results.append(f"- **Total Edges**: {schema.get('total_edges', 0)}")
                results.append(f"- **Avg Connections/Node**: {schema.get('avg_connections_per_node', 0):.2f}")
                results.append(f"- **Max Connections**: {schema.get('max_connections', 0)}")
                results.append(f"- **Orphan Nodes**: {schema.get('orphan_node_count', 0)}")
                results.append("")

                # Time range
                time_range = schema.get("time_range", {})
                if time_range.get("earliest") or time_range.get("latest"):
                    results.append("### Time Range")
                    if time_range.get("earliest"):
                        results.append(f"- Earliest: {time_range['earliest']}")
                    if time_range.get("latest"):
                        results.append(f"- Latest: {time_range['latest']}")
                    results.append("")

                # Edge types
                edge_dist = schema.get("edge_type_distribution", {})
                if edge_dist:
                    results.append("### Relationship Types")
                    for edge_type, count in sorted(edge_dist.items(), key=lambda x: x[1], reverse=True):
                        results.append(f"- **{edge_type}**: {count}")
                    results.append("")

                # Memory types
                mem_dist = schema.get("memory_type_distribution", {})
                if mem_dist:
                    results.append("### Memory Types")
                    for mem_type, count in sorted(mem_dist.items(), key=lambda x: x[1], reverse=True):
                        results.append(f"- {mem_type}: {count}")
                    results.append("")

                # Top tags
                tag_freq = schema.get("tag_frequency", {})
                if tag_freq:
                    results.append("### Top Tags")
                    tag_items = list(tag_freq.items())[:10]
                    for tag, count in tag_items:
                        results.append(f"- `{tag}`: {count}")
                    results.append("")

                # Health assessment
                results.append("### Health Assessment")
                total_nodes = schema.get("total_nodes", 0)
                orphan_count = schema.get("orphan_node_count", 0)
                if total_nodes > 0:
                    orphan_ratio = orphan_count / total_nodes
                    if orphan_ratio > 0.5:
                        results.append("⚠️ High orphan ratio - many memories are not connected")
                    elif orphan_ratio > 0.2:
                        results.append("📋 Moderate orphan ratio - some memories could benefit from more connections")
                    else:
                        results.append("✅ Good connectivity - memories are well connected")

                avg_conn = schema.get("avg_connections_per_node", 0)
                if avg_conn < 1:
                    results.append("⚠️ Low average connections - consider enriching relationships")
                elif avg_conn > 5:
                    results.append("✅ Rich relationships - good knowledge graph density")

                return [TextContent(type="text", text="\n".join(results))]
            else:
                return api_error_response("Schema export", data.get("message", "Unknown error"))
        else:
            return api_error_response("Schema export", f"HTTP {response.status_code}")

    except Exception as e:
        logger.error(f"Schema export error: {e}")
        return api_error_response("Schema export", str(e))


async def handle_memos_impact(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Handle memos_impact tool call — forward blast radius analysis."""
    cube_id = get_cube_id_from_args(arguments)
    memory_id = arguments.get("memory_id", "")
    max_depth = min(max(arguments.get("max_depth", 3), 1), 6)

    if not memory_id:
        return error_response(
            "memory_id is required",
            error_code=ERR_PARAM_MISSING,
            suggestions=[
                "Get a memory_id from memos_search or memos_get_graph first",
                "Example: `memos_impact(memory_id=\"uuid-here\")`",
            ],
        )

    if not NEO4J_HTTP_URL or not NEO4J_USER or not NEO4J_PASSWORD:
        return error_response(
            "Neo4j configuration missing",
            error_code=ERR_NEO4J_CONFIG,
            suggestions=[
                "Set NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD in .env",
                "Example: NEO4J_HTTP_URL=http://localhost:7474/db/neo4j/tx/commit",
            ],
        )

    neo4j_auth = (NEO4J_USER, NEO4J_PASSWORD)

    # Cypher: follow CAUSE and FOLLOWS edges forward, compute hop depth
    cypher_query = f"""
    MATCH (source:Memory {{id: $source_id}})-[:CAUSE|FOLLOWS*1..{max_depth}]->(node:Memory)
    WITH DISTINCT source, node
    MATCH path = shortestPath((source)-[:CAUSE|FOLLOWS*1..{max_depth}]->(node))
    RETURN node.id AS id, node.key AS key, node.memory AS memory,
           length(path) AS depth
    ORDER BY depth ASC
    LIMIT 30
    """

    try:
        neo4j_response = await client.post(
            NEO4J_HTTP_URL,
            json={
                "statements": [{
                    "statement": cypher_query,
                    "parameters": {"source_id": memory_id}
                }]
            },
            auth=neo4j_auth
        )

        if neo4j_response.status_code != 200:
            return api_error_response("Impact analysis", f"Neo4j HTTP {neo4j_response.status_code}")

        neo4j_data = neo4j_response.json()

        # Check for Neo4j-level errors
        errors = neo4j_data.get("errors", [])
        if errors:
            error_msg = errors[0].get("message", "Unknown Neo4j error")
            logger.error(f"Neo4j query error in memos_impact: {error_msg}")
            return api_error_response("Impact analysis", error_msg)

        rows = neo4j_data.get("results", [{}])[0].get("data", [])

        if not rows:
            return [TextContent(
                type="text",
                text="No forward impact found — this memory has no CAUSE or FOLLOWS successors."
            )]

        # Group results by depth
        depth_groups: dict[int, list[dict]] = {}
        for row in rows:
            r = row.get("row", [])
            if len(r) >= 4:
                depth = r[3]
                depth_groups.setdefault(depth, []).append({
                    "id": r[0],
                    "key": r[1] or "",
                    "memory": r[2] or "",
                })

        total_count = sum(len(items) for items in depth_groups.values())
        max_hop = max(depth_groups.keys())

        # Build markdown output
        results = []
        results.append("## Impact Analysis")
        results.append("")
        results.append(f"**Blast Radius: {total_count} downstream memories across {max_hop} hop(s)**")
        results.append("")

        depth_labels = {
            1: "Direct Impact",
            2: "Indirect Impact",
        }

        for depth in sorted(depth_groups.keys()):
            items = depth_groups[depth]
            label = depth_labels.get(depth, f"Downstream (hop {depth})")
            results.append(f"### {label} ({len(items)} node{'s' if len(items) != 1 else ''})")
            results.append("")

            for item in items[:8]:
                key = item["key"]
                memory_preview = item["memory"].split("\n")[0][:100]
                if key:
                    results.append(f"- **{key}**: {memory_preview}")
                else:
                    results.append(f"- {memory_preview}")

            if len(items) > 8:
                results.append(f"- ... and {len(items) - 8} more")
            results.append("")

        return [TextContent(type="text", text="\n".join(results))]

    except Exception as e:
        logger.error(f"Impact analysis error: {e}")
        return api_error_response("Impact analysis", str(e))
