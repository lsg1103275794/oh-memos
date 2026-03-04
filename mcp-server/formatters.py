#!/usr/bin/env python3
"""
MemOS MCP Server Formatters Module

Contains data formatting functions for displaying memory search results and graphs.
"""

import re

from typing import Any

from pydantic import BaseModel


class MemorySearchResult(BaseModel):
    """Structured memory search result."""
    id: str
    content: str
    relevance: float = 1.0
    metadata: dict[str, Any] = {}


def format_memories_for_display(data: dict) -> str:
    """Format memory search results for readable display."""
    results = []

    # Process text memories
    text_mems = data.get("text_mem", [])
    for cube_data in text_mems:
        cube_id = cube_data.get("cube_id", "unknown")
        memories_data = cube_data.get("memories", [])

        # If memories is a dict with nodes (tree_text mode), extract nodes
        memories = []
        if isinstance(memories_data, dict) and "nodes" in memories_data:
            memories = memories_data["nodes"]
        elif isinstance(memories_data, list):
            memories = memories_data

        if memories:
            results.append(f"## 📦 Cube: {cube_id}")
            results.append("")

            # Group by type
            grouped = {}
            for mem in memories:
                memory_text = mem.get("memory", "")
                # Try to extract type from [TYPE] prefix
                type_match = re.match(r"^\[([A-Z_]+)\]", memory_text)
                mem_type = type_match.group(1) if type_match else "PROGRESS"
                if mem_type not in grouped:
                    grouped[mem_type] = []
                grouped[mem_type].append(mem)

            # Display by type
            for mem_type, items in grouped.items():
                results.append(f"### 🏷️ Type: {mem_type}")
                results.append("")

                for i, mem in enumerate(items, 1):
                    memory_text = mem.get("memory", "")
                    mem_id = mem.get("id", "")  # Full UUID for delete operations

                    # Remove the [TYPE] prefix from display text if present
                    display_text = re.sub(r"^\[[A-Z_]+\]\s*", "", memory_text)

                    # Extract first line as title
                    first_line = display_text.split("\n")[0][:100]
                    if len(display_text.split("\n")) > 1 or len(display_text) > 100:
                        results.append(f"#### {i}. {first_line}")
                    else:
                        results.append(f"#### {i}. {display_text}")

                    results.append(f"ID: `{mem_id}`")
                    results.append("")

                    # Detect if it's a code block (simple heuristic)
                    if "```" not in display_text and any(
                        line.strip().startswith(("import ", "def ", "class ", "export ", "const ", "let ", "var "))
                        for line in display_text.split("\n")
                    ):
                        results.append("```python")
                        results.append(display_text)
                        results.append("```")
                    else:
                        results.append(display_text)

                    results.append("")
                    results.append("---")
                    results.append("")

    if not results:
        return "No memories found matching your query."

    return "\n".join(results)


def format_graph_for_display(data: list) -> str:
    """Format knowledge graph results with relationships for readable display."""
    results = []

    for cube_data in data:
        cube_id = cube_data.get("cube_id", "unknown")
        memories_list = cube_data.get("memories", [])

        if not memories_list:
            continue

        results.append(f"## 🧠 Knowledge Graph: {cube_id}")
        results.append("")

        for mem_data in memories_list:
            # Extract nodes and edges
            nodes = mem_data.get("nodes", [])
            edges = mem_data.get("edges", [])

            # Build node lookup for relationship display
            node_lookup = {}
            for node in nodes:
                node_id = node.get("id", "")
                node_memory = node.get("memory", "")
                # Clean up memory text for mermaid (remove newlines and special chars)
                clean_text = node_memory.replace("\n", " ").replace('"', "'").replace("[", "(").replace("]", ")")
                node_lookup[node_id] = clean_text[:50] + "..." if len(clean_text) > 50 else clean_text

            # Display nodes
            if nodes:
                results.append("### [NOTE] Memory Nodes")
                results.append("")
                for i, node in enumerate(nodes[:10], 1):  # Limit to 10 nodes
                    memory = node.get("memory", "")
                    first_line = memory.split("\n")[0][:100]
                    node_id = node.get("id", "")  # Full UUID for delete operations
                    results.append(f"{i}. **{first_line}**")
                    results.append(f"   ID: `{node_id}`")
                    results.append("")

            # Display relationships with Mermaid diagram
            if edges:
                results.append("### 📊 Relationship Diagram (Mermaid)")
                results.append("")
                results.append("```mermaid")
                results.append("graph TD")

                # Style definitions
                results.append("    classDef cause fill:#f96,stroke:#333,stroke-width:2px;")
                results.append("    classDef relate fill:#bbf,stroke:#333,stroke-width:1px;")
                results.append("    classDef conflict fill:#f66,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;")

                added_edges = set()
                for edge in edges:
                    source_id = edge.get("source", "")
                    target_id = edge.get("target", "")
                    rel_type = edge.get("type", "UNKNOWN")

                    # Skip PARENT relationships, only show semantic ones
                    if rel_type == "PARENT":
                        continue

                    # Avoid duplicate edges in diagram
                    edge_key = f"{source_id}-{target_id}-{rel_type}"
                    if edge_key in added_edges:
                        continue
                    added_edges.add(edge_key)

                    source_text = node_lookup.get(source_id, source_id[:8])
                    target_text = node_lookup.get(target_id, target_id[:8])

                    # Sanitize IDs for mermaid (must be alphanumeric)
                    s_id = f"node_{source_id[:8]}"
                    t_id = f"node_{target_id[:8]}"

                    # Format relationship in mermaid
                    if rel_type == "CAUSE":
                        results.append(f'    {s_id}["{source_text}"] -- CAUSE --> {t_id}["{target_text}"]:::cause')
                    elif rel_type == "RELATE":
                        results.append(f'    {s_id}["{source_text}"] -. RELATE .- {t_id}["{target_text}"]:::relate')
                    elif rel_type == "CONFLICT":
                        results.append(f'    {s_id}["{source_text}"] == CONFLICT == {t_id}["{target_text}"]:::conflict')
                    elif rel_type == "CONDITION":
                        results.append(f'    {s_id}["{source_text}"] -- CONDITION --> {t_id}["{target_text}"]')
                    else:
                        results.append(f'    {s_id}["{source_text}"] -- {rel_type} --> {t_id}["{target_text}"]')

                results.append("```")
                results.append("")

                # Textual fallback for terminals that don't render mermaid
                results.append("### [LINK] Textual Relationships")
                results.append("")
                results.append("```")
                for edge in edges:
                    if edge.get("type") == "PARENT":
                        continue
                    s_text = node_lookup.get(edge.get("source"), "???")[:40]
                    t_text = node_lookup.get(edge.get("target"), "???")[:40]
                    results.append(f"[{s_text}] --{edge.get('type')}--> [{t_text}]")
                results.append("```")
                results.append("")

        results.append("---")

    if not results:
        return "No memories or relationships found."

    return "\n".join(results)
