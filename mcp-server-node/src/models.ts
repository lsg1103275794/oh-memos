/**
 * Layered Memory Models + Compaction Logic
 */

import { extractMcpType } from "./query-processing.js";
import type { MemoryNode, MemoryMinimal, MemoryBrief, MemoryFull } from "./types.js";

// ============================================================================
// Compaction Configuration
// ============================================================================

export const COMPACTION_THRESHOLD = 15;
export const PREVIEW_COUNT = 5;

export function shouldCompact(count: number): boolean {
  return count > COMPACTION_THRESHOLD;
}

// ============================================================================
// Type Icon
// ============================================================================

export function getTypeIcon(memoryType: string): string {
  const icons: Record<string, string> = {
    ERROR_PATTERN: "🔴",
    BUGFIX: "🐛",
    DECISION: "📋",
    GOTCHA: "⚠️",
    CODE_PATTERN: "📝",
    CONFIG: "⚙️",
    FEATURE: "✨",
    MILESTONE: "🎯",
    PROGRESS: "📊",
    INFERRED: "🔗",
  };
  return icons[memoryType] ?? "📌";
}

// ============================================================================
// Conversion Utilities
// ============================================================================

export function toMinimal(memory: MemoryNode | Record<string, unknown>): MemoryMinimal {
  const memoryType = extractMcpType(memory as MemoryNode);
  const content = (memory as MemoryNode).memory ?? (memory as Record<string, unknown>).content as string ?? "";
  const cleanContent = content.replace(/^\[[A-Z_]+\]\s*/, "");

  const lines = cleanContent.split("\n").filter((l) => l.trim());
  const firstLine = lines[0] ?? cleanContent;
  const summary = firstLine.length > 100 ? firstLine.slice(0, 100) + "..." : firstLine;

  const meta = (memory as MemoryNode).metadata ?? {};
  const created =
    (memory as MemoryNode).updated_at ??
    (memory as MemoryNode).created_at ??
    meta.updated_at as string ??
    meta.created_at as string;

  return {
    id: (memory as MemoryNode).id ?? "",
    memoryType,
    summary,
    createdAt: created,
  };
}

export function toBrief(memory: MemoryNode | Record<string, unknown>): MemoryBrief {
  const minimal = toMinimal(memory);
  const meta = (memory as MemoryNode).metadata ?? {};
  const rawTags = (memory as MemoryNode).tags ?? meta.tags as string[] ?? [];

  return {
    ...minimal,
    key: (memory as MemoryNode).key ?? meta.key as string,
    tags: Array.isArray(rawTags) ? rawTags.map(String) : [],
    relevance: (meta.relativity as number) ?? 1.0,
  };
}

export function toFull(
  memory: MemoryNode | Record<string, unknown>,
  cubeId = "",
  userId = ""
): MemoryFull {
  const brief = toBrief(memory);
  const meta = (memory as MemoryNode).metadata ?? {};
  const content = (memory as MemoryNode).memory ?? (memory as Record<string, unknown>).content as string ?? "";
  const cleanContent = content.replace(/^\[[A-Z_]+\]\s*/, "");

  return {
    ...brief,
    content: cleanContent,
    background: (memory as MemoryNode).background ?? meta.background as string,
    cubeId,
    userId,
    relations: (memory as Record<string, unknown>).relations as unknown[] ?? [],
  };
}

// ============================================================================
// Compacted Search Result
// ============================================================================

export interface CompactedSearchResultData {
  preview: MemoryMinimal[];
  totalCount: number;
  omittedCount: number;
  message: string;
  query: string;
  cubeId: string;
}

export function compactedResultToText(result: CompactedSearchResultData): string {
  const lines = [
    "## 🔍 Search Results (Compacted)",
    "",
    `**Query**: \`${result.query}\``,
    `**Total**: ${result.totalCount} memories found`,
    `**Showing**: Top ${result.preview.length} (omitted ${result.omittedCount})`,
    "",
    "### Preview",
    "",
  ];

  for (let i = 0; i < result.preview.length; i++) {
    const mem = result.preview[i];
    const icon = getTypeIcon(mem.memoryType);
    lines.push(`${i + 1}. ${icon} **[${mem.memoryType}]** ${mem.summary}`);
    lines.push(`   ID: \`${mem.id}\``);
    lines.push("");
  }

  lines.push("---");
  lines.push("");
  lines.push('💡 **Tip**: Use `memos_get(memory_id="<id>")` to get full details of a specific memory.');

  return lines.join("\n");
}
