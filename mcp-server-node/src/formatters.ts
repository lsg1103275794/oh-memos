/**
 * MemOS MCP Server Formatters
 *
 * Formats memory search results and knowledge graphs for display.
 */

import type { SearchData, MemoryNode, GraphEdge } from "./types.js";

// ============================================================================
// Memory Display Formatter
// ============================================================================

export function formatMemoriesForDisplay(data: SearchData): string {
  const results: string[] = [];

  const textMems = data.text_mem ?? [];
  for (const cubeData of textMems) {
    const cubeId = cubeData.cube_id ?? "unknown";
    const memoriesData = cubeData.memories;

    let memories: MemoryNode[] = [];
    if (memoriesData && !Array.isArray(memoriesData) && memoriesData.nodes) {
      memories = memoriesData.nodes;
    } else if (Array.isArray(memoriesData)) {
      memories = memoriesData as MemoryNode[];
    }

    if (memories.length === 0) continue;

    results.push(`## 📦 Cube: ${cubeId}`);
    results.push("");

    // Group by type
    const grouped: Record<string, MemoryNode[]> = {};
    for (const mem of memories) {
      const memText = mem.memory ?? "";
      const typeMatch = memText.match(/^\[([A-Z_]+)\]/);
      const memType = typeMatch ? typeMatch[1] : "PROGRESS";
      if (!grouped[memType]) grouped[memType] = [];
      grouped[memType].push(mem);
    }

    // Display by type
    for (const [memType, items] of Object.entries(grouped)) {
      results.push(`### 🏷️ Type: ${memType}`);
      results.push("");

      for (let i = 0; i < items.length; i++) {
        const mem = items[i];
        const memText = mem.memory ?? "";
        const memId = mem.id ?? "";

        // Remove [TYPE] prefix
        const displayText = memText.replace(/^\[[A-Z_]+\]\s*/, "");
        const firstLine = displayText.split("\n")[0].slice(0, 100);

        if (displayText.split("\n").length > 1 || displayText.length > 100) {
          results.push(`#### ${i + 1}. ${firstLine}`);
        } else {
          results.push(`#### ${i + 1}. ${displayText}`);
        }

        results.push(`ID: \`${memId}\``);
        results.push("");

        // Detect code blocks
        const hasCodeIndicator = displayText.split("\n").some((line) =>
          /^(import |def |class |export |const |let |var )/.test(line.trim())
        );
        if (!displayText.includes("```") && hasCodeIndicator) {
          results.push("```python");
          results.push(displayText);
          results.push("```");
        } else {
          results.push(displayText);
        }

        results.push("");
        results.push("---");
        results.push("");
      }
    }
  }

  if (results.length === 0) {
    return "No memories found matching your query.";
  }

  return results.join("\n");
}

// ============================================================================
// Graph Display Formatter
// ============================================================================

export interface GraphCubeData {
  cube_id?: string;
  memories?: Array<{
    nodes?: MemoryNode[];
    edges?: GraphEdge[];
  }>;
}

export function formatGraphForDisplay(data: GraphCubeData[]): string {
  const results: string[] = [];

  for (const cubeData of data) {
    const cubeId = cubeData.cube_id ?? "unknown";
    const memoriesList = cubeData.memories ?? [];

    if (memoriesList.length === 0) continue;

    results.push(`## 🧠 Knowledge Graph: ${cubeId}`);
    results.push("");

    for (const memData of memoriesList) {
      const nodes = memData.nodes ?? [];
      const edges = memData.edges ?? [];

      // Build node lookup
      const nodeLookup: Record<string, string> = {};
      for (const node of nodes) {
        const nodeId = node.id ?? "";
        const nodeMemory = node.memory ?? "";
        const cleanText = nodeMemory.replace(/\n/g, " ").replace(/"/g, "'").replace(/\[/g, "(").replace(/\]/g, ")");
        nodeLookup[nodeId] = cleanText.length > 50 ? cleanText.slice(0, 50) + "..." : cleanText;
      }

      // Display nodes
      if (nodes.length > 0) {
        results.push("### 📝 Memory Nodes");
        results.push("");
        for (let i = 0; i < Math.min(nodes.length, 10); i++) {
          const node = nodes[i];
          const memory = node.memory ?? "";
          const firstLine = memory.split("\n")[0].slice(0, 100);
          const nodeId = node.id ?? "";
          results.push(`${i + 1}. **${firstLine}**`);
          results.push(`   ID: \`${nodeId}\``);
          results.push("");
        }
      }

      // Display relationships with Mermaid
      if (edges.length > 0) {
        results.push("### 📊 Relationship Diagram (Mermaid)");
        results.push("");
        results.push("```mermaid");
        results.push("graph TD");
        results.push("    classDef cause fill:#f96,stroke:#333,stroke-width:2px;");
        results.push("    classDef relate fill:#bbf,stroke:#333,stroke-width:1px;");
        results.push("    classDef conflict fill:#f66,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;");

        const addedEdges = new Set<string>();
        for (const edge of edges) {
          const sourceId = edge.source ?? "";
          const targetId = edge.target ?? "";
          const relType = edge.type ?? "UNKNOWN";

          if (relType === "PARENT") continue;

          const edgeKey = `${sourceId}-${targetId}-${relType}`;
          if (addedEdges.has(edgeKey)) continue;
          addedEdges.add(edgeKey);

          const sourceText = nodeLookup[sourceId] ?? sourceId.slice(0, 8);
          const targetText = nodeLookup[targetId] ?? targetId.slice(0, 8);
          const sId = `node_${sourceId.slice(0, 8)}`;
          const tId = `node_${targetId.slice(0, 8)}`;

          if (relType === "CAUSE") {
            results.push(`    ${sId}["${sourceText}"] -- CAUSE --> ${tId}["${targetText}"]:::cause`);
          } else if (relType === "RELATE") {
            results.push(`    ${sId}["${sourceText}"] -. RELATE .- ${tId}["${targetText}"]:::relate`);
          } else if (relType === "CONFLICT") {
            results.push(`    ${sId}["${sourceText}"] == CONFLICT == ${tId}["${targetText}"]:::conflict`);
          } else if (relType === "CONDITION") {
            results.push(`    ${sId}["${sourceText}"] -- CONDITION --> ${tId}["${targetText}"]`);
          } else {
            results.push(`    ${sId}["${sourceText}"] -- ${relType} --> ${tId}["${targetText}"]`);
          }
        }

        results.push("```");
        results.push("");

        // Textual fallback
        results.push("### 🔗 Textual Relationships");
        results.push("");
        results.push("```");
        for (const edge of edges) {
          if (edge.type === "PARENT") continue;
          const sText = (nodeLookup[edge.source ?? ""] ?? "???").slice(0, 40);
          const tText = (nodeLookup[edge.target ?? ""] ?? "???").slice(0, 40);
          results.push(`[${sText}] --${edge.type}--> [${tText}]`);
        }
        results.push("```");
        results.push("");
      }
    }

    results.push("---");
  }

  if (results.length === 0) {
    return "No memories or relationships found.";
  }

  return results.join("\n");
}
