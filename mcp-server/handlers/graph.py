#!/usr/bin/env python3
"""
MemOS MCP Server Graph Handlers

Handles memos_trace_path, memos_get_graph, memos_export_schema tools.
"""

from typing import Any

import httpx
from mcp.types import TextContent

from config import (
    MEMOS_URL,
    MEMOS_USER,
    NEO4J_HTTP_URL,
    NEO4J_USER,
    NEO4J_PASSWORD,
    logger,
    _registered_cubes,
)
from cube_manager import ensure_cube_registered
from query_processing import extract_memories_from_response
from handlers.utils import get_cube_id_from_args, error_response


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
        return error_response("❌ Both source_id and target_id are required.")

    # Auto-register cube if needed
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return error_response(f"## Cube Registration Failed\n\n{reg_error}")

    # Call the trace_path API endpoint
    try:
        response = await client.post(
            f"{MEMOS_URL}/graph/trace_path",
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
                found = trace_data.get("found", False)
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
                return error_response(f"Trace path failed: {data.get('message', 'Unknown error')}")
        else:
            return error_response(f"API error: {response.status_code}")

    except Exception as e:
        logger.warning(f"Falling back to direct Neo4j query: {e}")

        if not NEO4J_HTTP_URL or not NEO4J_USER or not NEO4J_PASSWORD:
            return error_response("Neo4j fallback requires NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD in .env")

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
    """Handle memos_get_graph tool call."""
    cube_id = get_cube_id_from_args(arguments)
    query = arguments.get("query", "")

    # Auto-register cube if needed
    reg_success, reg_error = await ensure_cube_registered(client, cube_id)
    if not reg_success:
        return error_response(f"## Cube Registration Failed\n\n{reg_error}")

    if not NEO4J_HTTP_URL or not NEO4J_USER or not NEO4J_PASSWORD:
        return error_response("Neo4j query requires NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD in .env")

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

    # Query Neo4j for all CAUSE/RELATE/CONFLICT relationships
    cypher_query = """
    MATCH (a)-[r:CAUSE|RELATE|CONFLICT|CONDITION]->(b)
    WHERE a.memory CONTAINS $keyword OR b.memory CONTAINS $keyword
    RETURN a.id as source_id, a.memory as source_memory,
           type(r) as relation_type,
           b.id as target_id, b.memory as target_memory
    LIMIT 20
    """

    neo4j_response = await client.post(
        NEO4J_HTTP_URL,
        json={
            "statements": [{
                "statement": cypher_query,
                "parameters": {"keyword": query}
            }]
        },
        auth=neo4j_auth
    )

    results = []
    results.append(f"## 🧠 Knowledge Graph: {cube_id}")
    results.append(f"Query: `{query}`")
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
        return error_response(f"## Cube Registration Failed\n\n{reg_error}")

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
                return error_response(f"Schema export failed: {data.get('message', 'Unknown error')}")
        else:
            return error_response(f"API error: {response.status_code}")

    except Exception as e:
        logger.error(f"Schema export error: {e}")
        return error_response(f"Schema export error: {e!s}")
