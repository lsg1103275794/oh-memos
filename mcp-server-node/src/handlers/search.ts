/**
 * Search Handlers
 *
 * memos_search, memos_search_context, memos_suggest, memos_context_resume
 */

import { MEMOS_URL, MEMOS_USER, NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD, logger } from "../config.js";
import { apiCallWithRetry, fetchWithTimeout } from "../api-client.js";
import { ensureCubeRegistered } from "../cube-manager.js";
import { formatMemoriesForDisplay } from "../formatters.js";
import {
  COMPACTION_THRESHOLD,
  PREVIEW_COUNT,
  shouldCompact,
  compactedResultToText,
  toMinimal,
} from "../models.js";
import {
  applyKeywordRerank,
  detectQueryIntent,
  filterEdgesByIntent,
  filterMemoriesByType,
  getIntentDescription,
  parseMemoryTypePrefix,
} from "../query-processing.js";
import { suggestSearchQueries } from "../memory-analysis.js";
import type { TextContent, MemoryNode, SearchData } from "../types.js";
import {
  apiErrorResponse,
  cubeRegistrationError,
  getCubeIdFromArgs,
} from "./utils.js";

// ============================================================================
// Temporal Graph Query (Neo4j)
// ============================================================================

async function getTemporalMemories(
  cubeId: string,
  topK = 10,
  timeWindowHours?: number
): Promise<MemoryNode[]> {
  if (!NEO4J_HTTP_URL || !NEO4J_USER || !NEO4J_PASSWORD) {
    logger.debug("Neo4j config missing, skipping temporal query");
    return [];
  }

  const auth = Buffer.from(`${NEO4J_USER}:${NEO4J_PASSWORD}`).toString("base64");

  const timeFilter = timeWindowHours
    ? `AND n.updated_at >= datetime() - duration({hours: ${timeWindowHours}})`
    : "";

  const cypher = `
    MATCH (n:Memory)
    WHERE n.user_name = $user_name
    AND n.status = 'activated'
    ${timeFilter}
    RETURN n.id AS id, n.memory AS memory, n.key AS key,
           n.updated_at AS updated_at, n.background AS background,
           n.tags AS tags
    ORDER BY n.updated_at DESC
    LIMIT $top_k
  `;

  try {
    const response = await fetchWithTimeout(NEO4J_HTTP_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Basic ${auth}`,
      },
      body: JSON.stringify({
        statements: [
          {
            statement: cypher,
            parameters: { user_name: MEMOS_USER, top_k: topK },
          },
        ],
      }),
      timeoutMs: 10,
    });

    if (response.ok) {
      const data = await response.json() as Record<string, unknown>;
      const errors = data.errors as unknown[] ?? [];
      if (errors.length > 0) {
        logger.warning(`Neo4j temporal query errors: ${JSON.stringify(errors)}`);
        return [];
      }

      const rows = ((data.results as Record<string, unknown>[])?.[0]?.data as Record<string, unknown>[] ?? []);
      const memories: MemoryNode[] = [];

      for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const r = row.row as unknown[] ?? [];
        if (r.length >= 4) {
          memories.push({
            id: String(r[0] ?? ""),
            memory: String(r[1] ?? ""),
            key: String(r[2] ?? ""),
            updated_at: String(r[3] ?? ""),
            background: r.length > 4 ? String(r[4] ?? "") : "",
            tags: Array.isArray(r[5]) ? (r[5] as string[]) : [],
            metadata: {
              relativity: 0.8 - i * 0.05,
              temporal_rank: i + 1,
              source: "temporal_query",
            },
          });
        }
      }

      logger.info(`Temporal query returned ${memories.length} memories`);
      return memories;
    }
  } catch (err) {
    logger.error(`Temporal query error: ${err}`);
  }
  return [];
}

function mergeTemporalResults(
  searchData: SearchData,
  temporalMemories: MemoryNode[],
  intent: string
): SearchData {
  if (temporalMemories.length === 0) return searchData;

  const existingIds = new Set<string>();
  const textMem = searchData.text_mem ?? [];

  for (const bucket of textMem) {
    const memData = bucket.memories;
    const memories = Array.isArray(memData)
      ? (memData as MemoryNode[])
      : (memData?.nodes ?? []);
    for (const mem of memories) {
      const id = mem.id ?? (mem.metadata?.id as string);
      if (id) existingIds.add(id);
    }
  }

  const newTemporal = temporalMemories.filter((m) => !existingIds.has(m.id));
  if (newTemporal.length === 0) return searchData;

  if (intent === "temporal") {
    const temporalBucket = {
      cube_id: "temporal",
      memories: { nodes: newTemporal, edges: [] },
      _source: "temporal_graph_query",
    };
    searchData.text_mem = [temporalBucket, ...textMem];
  }

  return searchData;
}

function extractSearchMemories(data: SearchData): MemoryNode[] {
  const memories: MemoryNode[] = [];
  for (const cubeData of data.text_mem ?? []) {
    const memData = cubeData.memories;
    if (memData && !Array.isArray(memData) && memData.nodes) {
      memories.push(...memData.nodes);
    } else if (Array.isArray(memData)) {
      memories.push(...(memData as MemoryNode[]));
    }
  }
  return memories;
}

// ============================================================================
// memos_search
// ============================================================================

export async function handleMemosSearch(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = getCubeIdFromArgs(arguments_);
  const rawQuery = String(arguments_.query ?? "");
  const topK = Number(arguments_.top_k ?? 10);
  const compact = arguments_.compact !== false;

  const [memType, cleanedQuery] = parseMemoryTypePrefix(rawQuery);
  const query = cleanedQuery || rawQuery;
  const intent = detectQueryIntent(query);

  const [regSuccess, regError] = await ensureCubeRegistered(cubeId);
  if (!regSuccess) return cubeRegistrationError(cubeId, regError);

  const apiResult = await apiCallWithRetry(
    "POST",
    `${MEMOS_URL}/search`,
    cubeId,
    {
      body: {
        user_id: MEMOS_USER,
        query,
        install_cube_ids: [cubeId],
        top_k: topK,
      },
    },
    ensureCubeRegistered
  );

  if (apiResult.success && apiResult.data) {
    let resultData = (apiResult.data as Record<string, unknown>).data as SearchData ?? {};

    // Temporal enhancement
    if (intent === "temporal") {
      let timeWindow: number | undefined;
      const timeMatch = query.match(/(\d+)\s*(?:小时|hour|h)/i);
      if (timeMatch) timeWindow = parseInt(timeMatch[1]);
      else if (/今天|today/i.test(query)) timeWindow = 24;
      else if (/本周|this\s*week|week/i.test(query)) timeWindow = 168;

      const temporalMemories = await getTemporalMemories(cubeId, topK, timeWindow);
      resultData = mergeTemporalResults(resultData, temporalMemories, intent);
    }

    resultData = filterEdgesByIntent(resultData, intent);
    resultData = filterMemoriesByType(resultData, memType);
    const keywordQuery = memType ? cleanedQuery : query;
    resultData = applyKeywordRerank(resultData, keywordQuery);

    const allMemories = extractSearchMemories(resultData);
    const totalCount = allMemories.length;

    if (compact && shouldCompact(totalCount)) {
      const preview = allMemories.slice(0, PREVIEW_COUNT).map(toMinimal);
      let text = compactedResultToText({
        preview,
        totalCount,
        omittedCount: totalCount - preview.length,
        message: 'Use memos_get(memory_id="<id>") for full details',
        query: rawQuery,
        cubeId,
      });

      if (intent !== "default") {
        const intentDesc = getIntentDescription(intent);
        text = `*${intentDesc}*\n\n${text}`;
      }

      return [{ type: "text", text }];
    }

    let formatted = formatMemoriesForDisplay(resultData);
    if (intent !== "default") {
      const intentDesc = getIntentDescription(intent);
      formatted = `*${intentDesc}*\n\n${formatted}`;
    }

    return [{ type: "text", text: formatted }];
  } else if (apiResult.data) {
    return apiErrorResponse("Search", String((apiResult.data as Record<string, unknown>).message ?? "Unknown error"));
  } else {
    return apiErrorResponse("Search", `HTTP ${apiResult.status}`);
  }
}

// ============================================================================
// memos_search_context
// ============================================================================

export async function handleMemosSearchContext(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = getCubeIdFromArgs(arguments_);
  const rawQuery = String(arguments_.query ?? "");
  const context = (arguments_.context as Array<Record<string, string>>) ?? [];

  const [memType, cleanedQuery] = parseMemoryTypePrefix(rawQuery);
  const query = cleanedQuery || rawQuery;

  const contextText = context.slice(-5).map((m) => m.content ?? "").join(" ");
  const intent = detectQueryIntent(`${query} ${contextText}`);

  const [regSuccess, regError] = await ensureCubeRegistered(cubeId);
  if (!regSuccess) return cubeRegistrationError(cubeId, regError);

  const chatHistory = context.slice(-10)
    .filter((m) => m.content)
    .map((m) => ({ role: m.role, content: m.content }));

  try {
    const response = await fetchWithTimeout(`${MEMOS_URL}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: MEMOS_USER,
        query,
        readable_cube_ids: [cubeId],
        enable_context_analysis: true,
        chat_history: chatHistory,
        top_k: 15,
      }),
    });

    if (response.ok) {
      const data = await response.json() as Record<string, unknown>;
      if (data.code === 200) {
        const results: string[] = [];
        const intentDesc = getIntentDescription(intent);
        results.push(`## ${intentDesc}`, "");

        let resultData = (data.data as SearchData) ?? {};

        if (intent === "temporal") {
          const temporalMemories = await getTemporalMemories(cubeId, 15);
          resultData = mergeTemporalResults(resultData, temporalMemories, intent);
        }

        resultData = filterEdgesByIntent(resultData, intent);
        resultData = filterMemoriesByType(resultData, memType);
        const keywordQuery = memType ? cleanedQuery : query;
        resultData = applyKeywordRerank(resultData, keywordQuery);
        const formatted = formatMemoriesForDisplay(resultData);

        if (context.length > 0) {
          results.push(`*Analyzed with ${context.length} context messages*`, "");
        }
        results.push(formatted);
        return [{ type: "text", text: results.join("\n") }];
      } else {
        // Fallback to standard search
        const fallbackResult = await apiCallWithRetry(
          "POST",
          `${MEMOS_URL}/search`,
          cubeId,
          { body: { user_id: MEMOS_USER, query, install_cube_ids: [cubeId] } },
          ensureCubeRegistered
        );
        if (fallbackResult.success && fallbackResult.data) {
          let resultData = (fallbackResult.data as Record<string, unknown>).data as SearchData ?? {};
          resultData = filterEdgesByIntent(resultData, intent);
          resultData = filterMemoriesByType(resultData, memType);
          const keywordQuery = memType ? cleanedQuery : query;
          resultData = applyKeywordRerank(resultData, keywordQuery);
          const formatted = formatMemoriesForDisplay(resultData);
          return [{ type: "text", text: `## Search Results (fallback)\n\n${formatted}` }];
        }
        return apiErrorResponse("Context search", String(data.message ?? "Unknown error"));
      }
    } else {
      return apiErrorResponse("Context search", `HTTP ${response.status}`);
    }
  } catch (err) {
    return apiErrorResponse("Context search", String(err));
  }
}

// ============================================================================
// memos_suggest
// ============================================================================

export async function handleMemosSuggest(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const context = String(arguments_.context ?? "");
  const suggestions = suggestSearchQueries(context);

  if (suggestions.length > 0) {
    const result = ["## 🔍 Suggested Searches\n", "Based on your context, try these searches:\n"];
    for (let i = 0; i < suggestions.length; i++) {
      result.push(`${i + 1}. \`${suggestions[i]}\``);
    }
    return [{ type: "text", text: result.join("\n") }];
  } else {
    return [{ type: "text", text: "No specific suggestions. Try searching with keywords from your context." }];
  }
}

// ============================================================================
// memos_context_resume
// ============================================================================

export async function handleMemosContextResume(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = getCubeIdFromArgs(arguments_);

  const [regSuccess, regError] = await ensureCubeRegistered(cubeId);
  if (!regSuccess) return cubeRegistrationError(cubeId, regError);

  // Try temporal query first
  let recentMemories = await getTemporalMemories(cubeId, 10, 24);

  // Fallback to API list
  if (recentMemories.length === 0) {
    const result = await apiCallWithRetry(
      "GET",
      `${MEMOS_URL}/memories`,
      cubeId,
      { params: { user_id: MEMOS_USER, mem_cube_id: cubeId, limit: 10 } },
      ensureCubeRegistered
    );
    if (result.success && result.data) {
      recentMemories = extractSearchMemories((result.data as Record<string, unknown>).data as SearchData ?? {});
    }
  }

  const lines = ["## Context Resumed", ""];

  if (recentMemories.length > 0) {
    lines.push(`**Recent memories** (${recentMemories.length} items, last 24h):`, "");
    for (let i = 0; i < Math.min(recentMemories.length, 10); i++) {
      const mem = recentMemories[i];
      const content = mem.memory ?? "";
      const summary = content.slice(0, 120).split("\n")[0];
      lines.push(`${i + 1}. ${summary}`);
    }
    lines.push("");
  } else {
    lines.push("No recent memories found in this cube.", "");
  }

  lines.push("---");
  lines.push("**REMINDER**: Use MCP memos tools (`memos_save`, `memos_search`) for ALL memory operations.");
  lines.push("NEVER use `mkdir` or `Write` to create memory files.");

  return [{ type: "text", text: lines.join("\n") }];
}
