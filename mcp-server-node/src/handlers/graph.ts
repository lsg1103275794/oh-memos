/**
 * Graph Handlers
 *
 * memos_trace_path, memos_get_graph, memos_export_schema, memos_impact
 */

import { MEMOS_URL, MEMOS_USER, NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD, logger, registeredCubes } from "../config.js";
import { fetchWithTimeout } from "../api-client.js";
import { ensureCubeRegistered } from "../cube-manager.js";
import {
  detectQueryIntent,
  extractMemoriesFromResponse,
  getGraphsForIntent,
  getIntentDescription,
} from "../query-processing.js";
import type { TextContent, SearchData } from "../types.js";
import {
  ERR_NEO4J_CONFIG,
  ERR_PARAM_MISSING,
  apiErrorResponse,
  cubeRegistrationError,
  errorResponse,
  getCubeIdFromArgs,
} from "./utils.js";

// ============================================================================
// Neo4j Helper
// ============================================================================

function neo4jAuthHeader(): string {
  return `Basic ${Buffer.from(`${NEO4J_USER}:${NEO4J_PASSWORD}`).toString("base64")}`;
}

async function neo4jQuery(
  cypher: string,
  parameters: Record<string, unknown>
): Promise<{ ok: boolean; data: Record<string, unknown> | null; status: number }> {
  try {
    const response = await fetchWithTimeout(NEO4J_HTTP_URL!, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: neo4jAuthHeader(),
      },
      body: JSON.stringify({
        statements: [{ statement: cypher, parameters }],
      }),
      timeoutMs: 15,
    });

    const data = await response.json() as Record<string, unknown>;
    return { ok: response.ok, data, status: response.status };
  } catch (err) {
    logger.error(`Neo4j query error: ${err}`);
    return { ok: false, data: null, status: 0 };
  }
}

// ============================================================================
// memos_trace_path
// ============================================================================

export async function handleMemosTracePath(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = getCubeIdFromArgs(arguments_);
  const sourceId = String(arguments_.source_id ?? "");
  const targetId = String(arguments_.target_id ?? "");
  const maxDepth = Math.min(Number(arguments_.max_depth ?? 3), 10);

  if (!sourceId || !targetId) {
    return errorResponse(
      "Both source_id and target_id are required",
      ERR_PARAM_MISSING,
      [
        "Get node IDs from memos_search or memos_get_graph",
        '`memos_trace_path(source_id="uuid-1", target_id="uuid-2")`',
      ]
    );
  }

  const [regSuccess, regError] = await ensureCubeRegistered(cubeId);
  if (!regSuccess) return cubeRegistrationError(cubeId, regError);

  try {
    const response = await fetchWithTimeout(`${MEMOS_URL}/product/graph/trace_path`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: MEMOS_USER,
        source_id: sourceId,
        target_id: targetId,
        max_depth: maxDepth,
        include_all_paths: false,
        mem_cube_id: cubeId,
      }),
    });

    if (response.ok) {
      const data = await response.json() as Record<string, unknown>;
      if (data.code === 200) {
        const traceData = data.data as Record<string, unknown> ?? {};
        const found = traceData.path_found ?? traceData.found ?? false;
        const paths = (traceData.paths as unknown[]) ?? [];
        const sourceNode = traceData.source as Record<string, unknown> ?? {};
        const targetNode = traceData.target as Record<string, unknown> ?? {};

        const results: string[] = ["## 🔗 Path Trace Results", ""];

        if (sourceNode.memory) results.push(`**Source**: ${String(sourceNode.memory).slice(0, 80)}...`);
        if (targetNode.memory) results.push(`**Target**: ${String(targetNode.memory).slice(0, 80)}...`);
        results.push("");

        if (!found) {
          results.push(`*No path found within ${maxDepth} hops.*`, "");
          results.push("Suggestions:");
          results.push("- Try increasing max_depth (up to 10)");
          results.push("- Verify the node IDs are correct");
          results.push("- The nodes may not be connected in the graph");
        } else {
          for (let i = 0; i < paths.length; i++) {
            const path = paths[i] as Record<string, unknown>;
            const length = path.length ?? 0;
            const nodes = (path.nodes as unknown[]) ?? [];
            const edges = (path.edges as unknown[]) ?? [];

            // If API returns empty nodes, fall back to Neo4j
            if (nodes.length === 0 && NEO4J_HTTP_URL && NEO4J_USER && NEO4J_PASSWORD) {
              throw new Error("API returned empty path nodes, falling back to Neo4j");
            }

            results.push(`### Path ${i + 1} (Length: ${length})`, "", "```");
            for (let j = 0; j < nodes.length; j++) {
              const node = nodes[j] as Record<string, unknown>;
              const nodeMem = String(node.memory ?? "").slice(0, 60);
              results.push(`[${j + 1}] ${nodeMem}...`);
              if (j < edges.length) {
                const edge = edges[j] as Record<string, unknown>;
                results.push("    │");
                results.push(`    └── ${edge.type ?? "UNKNOWN"} ──>`);
              }
            }
            results.push("```", "");
          }
        }

        return [{ type: "text", text: results.join("\n") }];
      } else {
        return apiErrorResponse("Trace path", String((data as Record<string, unknown>).message ?? "Unknown error"));
      }
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (err) {
    logger.warning(`Falling back to direct Neo4j query: ${err}`);

    if (!NEO4J_HTTP_URL || !NEO4J_USER || !NEO4J_PASSWORD) {
      return errorResponse(
        "Neo4j configuration missing",
        ERR_NEO4J_CONFIG,
        [
          "Set NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD in .env",
          "Example: NEO4J_HTTP_URL=http://localhost:7474/db/neo4j/tx/commit",
        ]
      );
    }

    const cypher = `
      MATCH (source:Memory), (target:Memory)
      WHERE source.id = $source_id AND target.id = $target_id
      MATCH path = shortestPath((source)-[*1..${maxDepth}]-(target))
      RETURN [n IN nodes(path) | {id: n.id, memory: n.memory}] AS nodes,
             [r IN relationships(path) | {type: type(r)}] AS rels
      LIMIT 1
    `;

    const { ok, data, status } = await neo4jQuery(cypher, { source_id: sourceId, target_id: targetId });

    const results = ["## 🔗 Path Trace (Direct Query)", ""];

    if (ok && data) {
      const rows = ((data.results as Record<string, unknown>[])?.[0]?.data as Record<string, unknown>[]) ?? [];
      if (rows.length > 0) {
        const row = rows[0].row as unknown[][] ?? [[], []];
        const nodes = (row[0] as Record<string, unknown>[]) ?? [];
        const rels = (row[1] as Record<string, unknown>[]) ?? [];

        results.push("```");
        for (let j = 0; j < nodes.length; j++) {
          const nodeMem = String(nodes[j].memory ?? "").slice(0, 60);
          results.push(`[${j + 1}] ${nodeMem}...`);
          if (j < rels.length) {
            results.push(`    └── ${rels[j].type ?? "?"} ──>`);
          }
        }
        results.push("```");
      } else {
        results.push(`*No path found within ${maxDepth} hops.*`);
      }
    } else {
      results.push(`*Neo4j query error: ${status}*`);
    }

    return [{ type: "text", text: results.join("\n") }];
  }
}

// ============================================================================
// memos_get_graph
// ============================================================================

export async function handleMemosGetGraph(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = getCubeIdFromArgs(arguments_);
  const query = String(arguments_.query ?? "");

  const intent = detectQueryIntent(query);
  const targetEdgeTypes = getGraphsForIntent(intent);

  const [regSuccess, regError] = await ensureCubeRegistered(cubeId);
  if (!regSuccess) return cubeRegistrationError(cubeId, regError);

  if (!NEO4J_HTTP_URL || !NEO4J_USER || !NEO4J_PASSWORD) {
    return errorResponse(
      "Neo4j configuration missing",
      ERR_NEO4J_CONFIG,
      [
        "Set NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD in .env",
        "Example: NEO4J_HTTP_URL=http://localhost:7474/db/neo4j/tx/commit",
      ]
    );
  }

  // Search for relevant memories first
  let memories: ReturnType<typeof extractMemoriesFromResponse> = [];
  try {
    const searchResponse = await fetchWithTimeout(`${MEMOS_URL}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: MEMOS_USER,
        query,
        install_cube_ids: [cubeId],
      }),
    });

    if (searchResponse.ok) {
      const data = await searchResponse.json() as Record<string, unknown>;
      if (data.code === 200) {
        memories = extractMemoriesFromResponse((data.data as SearchData) ?? {});
      } else {
        // Re-register and retry
        registeredCubes.delete(cubeId);
        const [retrySuccess] = await ensureCubeRegistered(cubeId, true);
        if (retrySuccess) {
          const retrySearch = await fetchWithTimeout(`${MEMOS_URL}/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: MEMOS_USER, query, install_cube_ids: [cubeId] }),
          });
          if (retrySearch.ok) {
            const retryData = await retrySearch.json() as Record<string, unknown>;
            if (retryData.code === 200) {
              memories = extractMemoriesFromResponse((retryData.data as SearchData) ?? {});
            }
          }
        }
      }
    }
  } catch (err) {
    logger.warning(`Graph search failed: ${err}`);
  }

  // Build Cypher query
  const edgeTypesCypher = targetEdgeTypes.join("|");
  const memIds = memories
    .slice(0, 10)
    .map((m) => m.id ?? (m.metadata?.id as string))
    .filter(Boolean);

  let cypher: string;
  let params: Record<string, unknown>;

  if (memIds.length > 0) {
    const idList = memIds.map((id) => `"${id}"`).join(", ");
    cypher = `
      MATCH (a)-[r:${edgeTypesCypher}]->(b)
      WHERE a.id IN [${idList}] OR b.id IN [${idList}]
      RETURN a.id as source_id, a.memory as source_memory,
             type(r) as relation_type,
             b.id as target_id, b.memory as target_memory
      LIMIT 20
    `;
    params = {};
  } else {
    const firstWord = query.split(/\s+/)[0] ?? query;
    cypher = `
      MATCH (a)-[r:${edgeTypesCypher}]->(b)
      WHERE a.memory CONTAINS $keyword OR b.memory CONTAINS $keyword
      RETURN a.id as source_id, a.memory as source_memory,
             type(r) as relation_type,
             b.id as target_id, b.memory as target_memory
      LIMIT 20
    `;
    params = { keyword: firstWord };
  }

  const { ok, data, status } = await neo4jQuery(cypher, params);

  const results: string[] = [];
  const intentDesc = getIntentDescription(intent);
  results.push(`## 🧠 Knowledge Graph: ${cubeId}`);
  results.push(`Query: \`${query}\` | ${intentDesc}`);
  results.push(`*Filtering edges: ${targetEdgeTypes.join(", ")}*`);
  results.push("");

  if (memories.length > 0) {
    results.push("### 📝 Related Memories", "");
    for (let i = 0; i < Math.min(memories.length, 5); i++) {
      const memory = memories[i].memory ?? "";
      const firstLine = memory.split("\n")[0].slice(0, 100);
      results.push(`${i + 1}. ${firstLine}`);
    }
    results.push("");
  }

  if (ok && data) {
    const rows = ((data.results as Record<string, unknown>[])?.[0]?.data as Record<string, unknown>[]) ?? [];

    if (rows.length > 0) {
      results.push("### 🔗 Relationships", "```");
      for (const row of rows) {
        const r = row.row as unknown[] ?? [];
        if (r.length >= 5) {
          const sourceMem = String(r[1] ?? "").slice(0, 50);
          const relType = String(r[2] ?? "UNKNOWN");
          const targetMem = String(r[4] ?? "").slice(0, 50);

          let arrow: string;
          if (relType === "CAUSE") arrow = "──CAUSE──>";
          else if (relType === "RELATE") arrow = "──RELATE──";
          else if (relType === "CONFLICT") arrow = "══CONFLICT══";
          else arrow = `──${relType}──>`;

          results.push(`[${sourceMem}...]`);
          results.push(`    ${arrow}`);
          results.push(`[${targetMem}...]`);
          results.push("");
        }
      }
      results.push("```");
    } else {
      results.push("*No relationships found for this query.*");
    }
  } else {
    results.push(`*Neo4j query error: ${status}*`);
  }

  return [{ type: "text", text: results.join("\n") }];
}

// ============================================================================
// memos_export_schema
// ============================================================================

export async function handleMemosExportSchema(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = getCubeIdFromArgs(arguments_);
  const sampleSize = Math.min(Math.max(Number(arguments_.sample_size ?? 100), 10), 1000);

  const [regSuccess, regError] = await ensureCubeRegistered(cubeId);
  if (!regSuccess) return cubeRegistrationError(cubeId, regError);

  try {
    const response = await fetchWithTimeout(`${MEMOS_URL}/graph/schema`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: MEMOS_USER,
        mem_cube_id: cubeId,
        sample_size: sampleSize,
      }),
    });

    if (response.ok) {
      const data = await response.json() as Record<string, unknown>;
      if (data.code === 200) {
        const schema = (data.data as Record<string, unknown>) ?? {};
        const results: string[] = [];

        results.push("## 📊 Knowledge Graph Schema", "");
        results.push("### Overview");
        results.push(`- **Total Nodes**: ${schema.total_nodes ?? 0}`);
        results.push(`- **Total Edges**: ${schema.total_edges ?? 0}`);
        results.push(`- **Avg Connections/Node**: ${Number(schema.avg_connections_per_node ?? 0).toFixed(2)}`);
        results.push(`- **Max Connections**: ${schema.max_connections ?? 0}`);
        results.push(`- **Orphan Nodes**: ${schema.orphan_node_count ?? 0}`);
        results.push("");

        const timeRange = (schema.time_range as Record<string, unknown>) ?? {};
        if (timeRange.earliest || timeRange.latest) {
          results.push("### Time Range");
          if (timeRange.earliest) results.push(`- Earliest: ${timeRange.earliest}`);
          if (timeRange.latest) results.push(`- Latest: ${timeRange.latest}`);
          results.push("");
        }

        const edgeDist = (schema.edge_type_distribution as Record<string, number>) ?? {};
        if (Object.keys(edgeDist).length > 0) {
          results.push("### Relationship Types");
          for (const [t, c] of Object.entries(edgeDist).sort((a, b) => b[1] - a[1])) {
            results.push(`- **${t}**: ${c}`);
          }
          results.push("");
        }

        const memDist = (schema.memory_type_distribution as Record<string, number>) ?? {};
        if (Object.keys(memDist).length > 0) {
          results.push("### Memory Types");
          for (const [t, c] of Object.entries(memDist).sort((a, b) => b[1] - a[1])) {
            results.push(`- ${t}: ${c}`);
          }
          results.push("");
        }

        const tagFreq = (schema.tag_frequency as Record<string, number>) ?? {};
        const tagItems = Object.entries(tagFreq).slice(0, 10);
        if (tagItems.length > 0) {
          results.push("### Top Tags");
          for (const [tag, count] of tagItems) {
            results.push(`- \`${tag}\`: ${count}`);
          }
          results.push("");
        }

        results.push("### Health Assessment");
        const totalNodes = Number(schema.total_nodes ?? 0);
        const orphanCount = Number(schema.orphan_node_count ?? 0);
        if (totalNodes > 0) {
          const orphanRatio = orphanCount / totalNodes;
          if (orphanRatio > 0.5) results.push("⚠️ High orphan ratio - many memories are not connected");
          else if (orphanRatio > 0.2) results.push("📋 Moderate orphan ratio");
          else results.push("✅ Good connectivity - memories are well connected");
        }

        const avgConn = Number(schema.avg_connections_per_node ?? 0);
        if (avgConn < 1) results.push("⚠️ Low average connections - consider enriching relationships");
        else if (avgConn > 5) results.push("✅ Rich relationships - good knowledge graph density");

        return [{ type: "text", text: results.join("\n") }];
      } else {
        return apiErrorResponse("Schema export", String((data as Record<string, unknown>).message ?? "Unknown error"));
      }
    } else {
      return apiErrorResponse("Schema export", `HTTP ${response.status}`);
    }
  } catch (err) {
    return apiErrorResponse("Schema export", String(err));
  }
}

// ============================================================================
// memos_impact
// ============================================================================

export async function handleMemosImpact(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = getCubeIdFromArgs(arguments_);
  const memoryId = String(arguments_.memory_id ?? "");
  const maxDepth = Math.min(Math.max(Number(arguments_.max_depth ?? 3), 1), 6);

  if (!memoryId) {
    return errorResponse(
      "memory_id is required",
      ERR_PARAM_MISSING,
      [
        "Get a memory_id from memos_search or memos_get_graph first",
        '`memos_impact(memory_id="uuid-here")`',
      ]
    );
  }

  if (!NEO4J_HTTP_URL || !NEO4J_USER || !NEO4J_PASSWORD) {
    return errorResponse(
      "Neo4j configuration missing",
      ERR_NEO4J_CONFIG,
      [
        "Set NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD in .env",
        "Example: NEO4J_HTTP_URL=http://localhost:7474/db/neo4j/tx/commit",
      ]
    );
  }

  const cypher = `
    MATCH (source:Memory {id: $source_id})-[:CAUSE|FOLLOWS*1..${maxDepth}]->(node:Memory)
    WITH DISTINCT source, node
    MATCH path = shortestPath((source)-[:CAUSE|FOLLOWS*1..${maxDepth}]->(node))
    RETURN node.id AS id, node.key AS key, node.memory AS memory,
           length(path) AS depth
    ORDER BY depth ASC
    LIMIT 30
  `;

  try {
    const { ok, data, status } = await neo4jQuery(cypher, { source_id: memoryId });

    if (!ok) {
      return apiErrorResponse("Impact analysis", `Neo4j HTTP ${status}`);
    }

    if (!data) {
      return apiErrorResponse("Impact analysis", "No data returned");
    }

    const errors = (data.errors as unknown[]) ?? [];
    if (errors.length > 0) {
      const errMsg = String((errors[0] as Record<string, unknown>).message ?? "Unknown Neo4j error");
      return apiErrorResponse("Impact analysis", errMsg);
    }

    const rows = ((data.results as Record<string, unknown>[])?.[0]?.data as Record<string, unknown>[]) ?? [];

    if (rows.length === 0) {
      return [{ type: "text", text: "No forward impact found — this memory has no CAUSE or FOLLOWS successors." }];
    }

    // Group by depth
    const depthGroups: Record<number, Array<{ id: string; key: string; memory: string }>> = {};
    for (const row of rows) {
      const r = row.row as unknown[] ?? [];
      if (r.length >= 4) {
        const depth = Number(r[3]);
        if (!depthGroups[depth]) depthGroups[depth] = [];
        depthGroups[depth].push({
          id: String(r[0] ?? ""),
          key: String(r[1] ?? ""),
          memory: String(r[2] ?? ""),
        });
      }
    }

    const totalCount = Object.values(depthGroups).reduce((sum, items) => sum + items.length, 0);
    const maxHop = Math.max(...Object.keys(depthGroups).map(Number));

    const results: string[] = [
      "## Impact Analysis",
      "",
      `**Blast Radius: ${totalCount} downstream memories across ${maxHop} hop(s)**`,
      "",
    ];

    const depthLabels: Record<number, string> = {
      1: "Direct Impact",
      2: "Indirect Impact",
    };

    for (const depth of Object.keys(depthGroups).map(Number).sort((a, b) => a - b)) {
      const items = depthGroups[depth];
      const label = depthLabels[depth] ?? `Downstream (hop ${depth})`;
      results.push(`### ${label} (${items.length} node${items.length !== 1 ? "s" : ""})`, "");

      for (let i = 0; i < Math.min(items.length, 8); i++) {
        const item = items[i];
        const memPreview = item.memory.split("\n")[0].slice(0, 100);
        if (item.key) {
          results.push(`- **${item.key}**: ${memPreview}`);
        } else {
          results.push(`- ${memPreview}`);
        }
      }

      if (items.length > 8) {
        results.push(`- ... and ${items.length - 8} more`);
      }
      results.push("");
    }

    return [{ type: "text", text: results.join("\n") }];
  } catch (err) {
    return apiErrorResponse("Impact analysis", String(err));
  }
}
