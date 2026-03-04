/**
 * Query Processing Module
 *
 * Intent detection, keyword extraction, reranking, type extraction.
 */

import { MEMORY_TYPES } from "./config.js";
import { ALL_STOPWORDS, extractKeywordsEnhanced, keywordMatchScoreEnhanced } from "./keyword-enhancer.js";
import type { SearchData, MemoryNode, QueryIntent } from "./types.js";

// ============================================================================
// Intent to Graph Type Mapping
// ============================================================================

export const INTENT_TO_GRAPHS: Record<string, string[]> = {
  causal: ["CAUSE", "CONDITION"],
  related: ["RELATE"],
  conflict: ["CONFLICT"],
  temporal: ["FOLLOWS"],
  default: ["CAUSE", "RELATE", "CONDITION"],
};

export function detectQueryIntent(query: string): QueryIntent {
  const q = query.toLowerCase();

  const causalPatterns = [
    /为什么/, /why/, /原因/, /cause/, /导致/, /因为/,
    /根本原因/, /root\s*cause/, /怎么.*出错/, /how.*fail/,
    /什么.*引起/, /what.*caused/, /出了什么问题/,
  ];
  if (causalPatterns.some((p) => p.test(q))) return "causal";

  const conflictPatterns = [
    /冲突/, /conflict/, /矛盾/, /contradict/, /不一致/,
    /inconsisten/, /问题.*之间/, /clash/,
  ];
  if (conflictPatterns.some((p) => p.test(q))) return "conflict";

  const temporalPatterns = [
    /什么时候/, /when/, /之前/, /before/, /之后/, /after/,
    /最近/, /recent/, /先.*后/, /顺序/, /timeline/, /历史/,
    /上次/, /last\s*time/, /earlier/, /previously/,
  ];
  if (temporalPatterns.some((p) => p.test(q))) return "temporal";

  const relatedPatterns = [
    /相关/, /related/, /关联/, /有关/, /涉及/,
    /association/, /connect/, /link/,
  ];
  if (relatedPatterns.some((p) => p.test(q))) return "related";

  return "default";
}

export function getGraphsForIntent(intent: QueryIntent): string[] {
  return INTENT_TO_GRAPHS[intent] ?? INTENT_TO_GRAPHS.default;
}

export function getIntentDescription(intent: QueryIntent): string {
  const descriptions: Record<string, string> = {
    causal: "🔍 因果分析 (Causal Analysis)",
    related: "🔗 关联查询 (Related Search)",
    conflict: "⚠️ 冲突检测 (Conflict Detection)",
    temporal: "📅 时序查询 (Temporal Search)",
    default: "📚 综合查询 (General Search)",
  };
  return descriptions[intent] ?? descriptions.default;
}

// ============================================================================
// Memory Type Prefix Parsing
// ============================================================================

export function parseMemoryTypePrefix(query: string): [string | null, string] {
  if (!query) return [null, ""];
  const m = query.match(/^\s*\[?([A-Z_]+)\]?\s*[:\-]?\s*(.*)$/);
  if (!m) return [null, query.trim()];
  const memType = m[1];
  const rest = (m[2] ?? "").trim();
  if (MEMORY_TYPES.has(memType)) {
    return [memType, rest];
  }
  return [null, query.trim()];
}

// ============================================================================
// Keyword Extraction
// ============================================================================

export function extractKeywords(query: string): string[] {
  return extractKeywordsEnhanced(query, ALL_STOPWORDS);
}

// ============================================================================
// Keyword Match Score
// ============================================================================

export function keywordMatchScore(
  text: string,
  keywords: string[],
  metadata?: Record<string, unknown>,
  enableFuzzy = true
): number {
  return keywordMatchScoreEnhanced(text, keywords, metadata, enableFuzzy);
}

// ============================================================================
// Reranking
// ============================================================================

export function applyKeywordRerank(data: SearchData, query: string, enableFuzzy = true): SearchData {
  const keywords = extractKeywords(query);
  if (keywords.length === 0) return data;

  const textMems = data.text_mem ?? [];
  for (const cubeData of textMems) {
    const memData = cubeData.memories;

    if (memData && !Array.isArray(memData) && memData.nodes) {
      memData.nodes = [...memData.nodes].sort((a, b) => {
        const scoreA = (a.metadata?.relativity ?? 0) + keywordMatchScore(a.memory ?? "", keywords, a.metadata, enableFuzzy);
        const scoreB = (b.metadata?.relativity ?? 0) + keywordMatchScore(b.memory ?? "", keywords, b.metadata, enableFuzzy);
        return scoreB - scoreA;
      });
    } else if (Array.isArray(memData)) {
      memData.sort((a, b) => {
        const scoreA = (a.metadata?.relativity ?? 0) + keywordMatchScore(a.memory ?? "", keywords, a.metadata, enableFuzzy);
        const scoreB = (b.metadata?.relativity ?? 0) + keywordMatchScore(b.memory ?? "", keywords, b.metadata, enableFuzzy);
        return scoreB - scoreA;
      });
    }
  }

  return data;
}

// ============================================================================
// Edge Filtering by Intent
// ============================================================================

export function filterEdgesByIntent(data: SearchData, intent: QueryIntent): SearchData {
  const allowedEdgeTypes = getGraphsForIntent(intent);

  const textMems = data.text_mem ?? [];
  for (const cubeData of textMems) {
    const memData = cubeData.memories;
    if (memData && !Array.isArray(memData) && memData.edges && memData.nodes) {
      const filteredEdges = memData.edges.filter(
        (edge) => edge.type && allowedEdgeTypes.includes(edge.type)
      );
      memData.edges = filteredEdges;

      if (filteredEdges.length > 0) {
        const boostedIds = new Set<string>();
        for (const edge of filteredEdges) {
          if (edge.source) boostedIds.add(edge.source);
          if (edge.target) boostedIds.add(edge.target);
        }
        for (const node of memData.nodes) {
          if (node.id && boostedIds.has(node.id) && node.metadata) {
            node.metadata.relativity = (node.metadata.relativity ?? 0) + 0.5;
            node.metadata.intent_matched = true;
          }
        }
      }
    }
  }

  return data;
}

// ============================================================================
// Memory Type Filter
// ============================================================================

export function filterMemoriesByType(data: SearchData, memType: string | null): SearchData {
  if (!memType) return data;

  const textMems = data.text_mem ?? [];
  for (const cubeData of textMems) {
    const memData = cubeData.memories;
    if (memData && !Array.isArray(memData) && memData.nodes) {
      const filtered = memData.nodes.filter((n) =>
        new RegExp(`^\\[${memType}\\]`).test(n.memory ?? "")
      );
      if (memData.edges) {
        const keptIds = new Set(filtered.map((n) => n.id));
        memData.edges = memData.edges.filter(
          (e) => e.source && keptIds.has(e.source) && e.target && keptIds.has(e.target)
        );
      }
      memData.nodes = filtered;
    } else if (Array.isArray(memData)) {
      (cubeData as Record<string, unknown>).memories = memData.filter((m) =>
        new RegExp(`^\\[${memType}\\]`).test((m as MemoryNode).memory ?? "")
      );
    }
  }

  return data;
}

// ============================================================================
// Memory Extraction
// ============================================================================

export function extractMemoriesFromResponse(data: SearchData): MemoryNode[] {
  const memories: MemoryNode[] = [];
  const textMems = data.text_mem ?? [];

  for (const cubeData of textMems) {
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
// MCP Type Extraction
// ============================================================================

const VALID_MEMORY_TYPES = new Set([
  "BUGFIX", "ERROR_PATTERN", "DECISION", "GOTCHA", "CODE_PATTERN",
  "CONFIG", "FEATURE", "MILESTONE", "PROGRESS",
]);

const TYPE_PATTERN = /^\[([A-Z_]+)\]/;

function extractTypeFromText(text: string): string | null {
  const m = TYPE_PATTERN.exec(text);
  if (m && VALID_MEMORY_TYPES.has(m[1])) return m[1];
  return null;
}

function decodeSourceEntry(entry: unknown): Record<string, unknown> | null {
  if (entry && typeof entry === "object") return entry as Record<string, unknown>;
  if (typeof entry !== "string") return null;
  try {
    let result = JSON.parse(entry);
    if (typeof result === "string") result = JSON.parse(result);
    return typeof result === "object" && result !== null ? result as Record<string, unknown> : null;
  } catch {
    return null;
  }
}

function extractTypeFromSources(sources: unknown[]): string | null {
  if (!sources || sources.length === 0) return null;
  for (const entry of sources) {
    const decoded = decodeSourceEntry(entry);
    if (decoded) {
      const content = String(decoded.content ?? "");
      const found = extractTypeFromText(content);
      if (found) return found;
    }
  }
  return null;
}

export function extractMcpType(memory: MemoryNode | Record<string, unknown>): string {
  // 1. [TYPE] prefix in memory text
  const memText = (memory as MemoryNode).memory ?? "";
  const fromText = extractTypeFromText(memText);
  if (fromText) return fromText;

  // 2. [TYPE] prefix in sources (tree_text mode)
  const sources =
    (memory as Record<string, unknown>).sources ??
    ((memory as MemoryNode).metadata?.sources) ??
    [];
  const fromSources = extractTypeFromSources(sources as unknown[]);
  if (fromSources) return fromSources;

  // 3. LLM-inferred nodes
  const meta = (memory as MemoryNode).metadata ?? (memory as Record<string, unknown>);
  const nodeType = typeof meta === "object" ? (meta as Record<string, unknown>).type : null;
  const key = (memory as MemoryNode).key ?? (typeof meta === "object" ? String((meta as Record<string, unknown>).key ?? "") : "");
  if (nodeType === "reasoning" || String(key).startsWith("InferredFact")) {
    return "INFERRED";
  }

  return "PROGRESS";
}

// ============================================================================
// Stats
// ============================================================================

export function computeMemoryStats(data: SearchData): [Record<string, number>, number] {
  const memories = extractMemoriesFromResponse(data);
  const stats: Record<string, number> = {};
  let total = 0;

  for (const mem of memories) {
    total++;
    const memType = extractMcpType(mem);
    stats[memType] = (stats[memType] ?? 0) + 1;
  }

  return [stats, total];
}
