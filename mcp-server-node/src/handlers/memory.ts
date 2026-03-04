/**
 * Memory Handlers
 *
 * memos_save, memos_list_v2, memos_get, memos_get_stats
 */

import * as crypto from "crypto";
import { MEMOS_URL, MEMOS_USER, logger } from "../config.js";
import { apiCallWithRetry } from "../api-client.js";
import { ensureCubeRegistered } from "../cube-manager.js";
import { formatMemoriesForDisplay } from "../formatters.js";
import {
  COMPACTION_THRESHOLD,
  PREVIEW_COUNT,
  shouldCompact,
  compactedResultToText,
  toMinimal,
  toFull,
} from "../models.js";
import { computeMemoryStats, extractMcpType } from "../query-processing.js";
import type { TextContent, MemoryNode, SearchData } from "../types.js";
import {
  ERR_PARAM_MISSING,
  apiErrorResponse,
  cubeRegistrationError,
  errorResponse,
  getCubeIdFromArgs,
} from "./utils.js";

// ============================================================================
// Deduplication Cache
// ============================================================================

const saveDedupCache: Map<string, [string, number]> = new Map();
const DEDUP_TTL_SECONDS = 60;

function contentHash(content: string, cubeId: string): string {
  return crypto.createHash("md5").update(`${cubeId}:${content}`).digest("hex");
}

function isDuplicateSave(content: string, cubeId: string): boolean {
  const key = contentHash(content, cubeId);
  const now = Date.now() / 1000;

  // Clean expired
  for (const [k, [, ts]] of saveDedupCache) {
    if (now - ts > DEDUP_TTL_SECONDS) saveDedupCache.delete(k);
  }

  const entry = saveDedupCache.get(key);
  if (entry && now - entry[1] < DEDUP_TTL_SECONDS) {
    logger.debug(`Duplicate save detected (within ${DEDUP_TTL_SECONDS}s), skipping`);
    return true;
  }
  return false;
}

function markSaved(content: string, cubeId: string): void {
  const key = contentHash(content, cubeId);
  saveDedupCache.set(key, [cubeId, Date.now() / 1000]);
}

// ============================================================================
// memos_save
// ============================================================================

export async function handleMemosSave(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = getCubeIdFromArgs(arguments_);
  let content = String(arguments_.content ?? "");
  const memoryType = arguments_.memory_type as string | undefined;

  if (!memoryType) {
    return errorResponse(
      "memory_type parameter is required",
      ERR_PARAM_MISSING,
      [
        "Bug fix -> `BUGFIX` or `ERROR_PATTERN`",
        "Technical decision -> `DECISION`",
        "Gotcha/trap -> `GOTCHA`",
        "Code template -> `CODE_PATTERN`",
        "Config change -> `CONFIG`",
        "New feature -> `FEATURE`",
        "Major achievement -> `MILESTONE`",
        "Pure progress update -> `PROGRESS`",
        'Example: `memos_save(content="...", memory_type="BUGFIX")`',
      ]
    );
  }

  if (!content.startsWith(`[${memoryType}]`)) {
    content = `[${memoryType}] ${content}`;
  }

  if (isDuplicateSave(content, cubeId)) {
    return [{ type: "text", text: `⏭️ Skipped: Same content was saved within ${DEDUP_TTL_SECONDS}s (dedup protection)` }];
  }

  const [regSuccess, regError] = await ensureCubeRegistered(cubeId);
  if (!regSuccess) return cubeRegistrationError(cubeId, regError);

  const result = await apiCallWithRetry(
    "POST",
    `${MEMOS_URL}/memories`,
    cubeId,
    {
      body: {
        user_id: MEMOS_USER,
        mem_cube_id: cubeId,
        memory_content: content,
      },
    },
    ensureCubeRegistered
  );

  if (result.success) {
    markSaved(content, cubeId);
    return [{ type: "text", text: `Memory saved as [${memoryType}] in cube '${cubeId}'` }];
  } else if (result.data) {
    return apiErrorResponse("Save", String((result.data as Record<string, unknown>).message ?? "Unknown error"));
  } else {
    return apiErrorResponse("Save", `HTTP ${result.status}`);
  }
}

// ============================================================================
// memos_list_v2
// ============================================================================

export async function handleMemosList(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = getCubeIdFromArgs(arguments_);
  const limit = Number(arguments_.limit ?? 20);
  const memoryType = arguments_.memory_type as string | undefined;
  const compact = arguments_.compact !== false; // Default true

  const [regSuccess, regError] = await ensureCubeRegistered(cubeId);
  if (!regSuccess) return cubeRegistrationError(cubeId, regError);

  const params: Record<string, string | number | boolean> = {
    user_id: MEMOS_USER,
    mem_cube_id: cubeId,
  };
  if (!memoryType) {
    params.limit = limit;
  }

  const result = await apiCallWithRetry("GET", `${MEMOS_URL}/memories`, cubeId, { params }, ensureCubeRegistered);

  if (result.success && result.data) {
    const resultData = (result.data as Record<string, unknown>).data as SearchData ?? {};
    let allMemories = extractMemoriesFromData(resultData);

    if (memoryType) {
      allMemories = allMemories.filter((m) => extractMcpType(m) === memoryType).slice(0, limit);
    }

    const totalCount = allMemories.length;

    if (compact && shouldCompact(totalCount)) {
      const preview = allMemories.slice(0, PREVIEW_COUNT).map(toMinimal);
      const text = compactedResultToText({
        preview,
        totalCount,
        omittedCount: totalCount - preview.length,
        message: 'Use memos_get(memory_id="<id>") for full details',
        query: memoryType ? `list (type=${memoryType})` : "list all",
        cubeId,
      });
      return [{ type: "text", text }];
    }

    const formatted = formatMemoriesForDisplay(resultData);
    return [{ type: "text", text: formatted }];
  } else if (result.data) {
    return apiErrorResponse("List", String((result.data as Record<string, unknown>).message ?? "Unknown error"));
  } else {
    return apiErrorResponse("List", `HTTP ${result.status}`);
  }
}

// ============================================================================
// memos_get
// ============================================================================

export async function handleMemosGet(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = getCubeIdFromArgs(arguments_);
  const memoryId = String(arguments_.memory_id ?? "");

  if (!memoryId) {
    return errorResponse(
      "memory_id parameter is required",
      ERR_PARAM_MISSING,
      [
        "Get memory_id from memos_search or memos_list_v2 results",
        'Example: `memos_get(memory_id="abc123-...")`',
      ]
    );
  }

  const [regSuccess, regError] = await ensureCubeRegistered(cubeId);
  if (!regSuccess) return cubeRegistrationError(cubeId, regError);

  const result = await apiCallWithRetry(
    "GET",
    `${MEMOS_URL}/memories/${cubeId}/${memoryId}`,
    cubeId,
    {},
    ensureCubeRegistered
  );

  if (result.success && result.data) {
    const resultData = (result.data as Record<string, unknown>).data as MemoryNode | null;

    if (resultData) {
      const fullMem = toFull(resultData, cubeId, MEMOS_USER);
      const lines = [
        "## 📝 Memory Details",
        "",
        `**ID**: \`${fullMem.id}\``,
        `**Type**: ${fullMem.memoryType}`,
        `**Cube**: ${fullMem.cubeId}`,
      ];

      if (fullMem.key) lines.push(`**Key**: ${fullMem.key}`);
      if (fullMem.tags.length > 0) lines.push(`**Tags**: ${fullMem.tags.join(", ")}`);
      if (fullMem.createdAt) lines.push(`**Created**: ${fullMem.createdAt}`);

      lines.push("", "### Content", "", fullMem.content);

      if (fullMem.background) {
        lines.push("", "### Background", "", fullMem.background);
      }

      if (fullMem.relations && fullMem.relations.length > 0) {
        lines.push("", "### Relations", "");
        for (const rel of fullMem.relations.slice(0, 5)) {
          lines.push(`- ${JSON.stringify(rel)}`);
        }
      }

      return [{ type: "text", text: lines.join("\n") }];
    } else {
      return [{ type: "text", text: notFoundText(memoryId) }];
    }
  } else if (result.data) {
    const errMsg = String((result.data as Record<string, unknown>).message ?? "Unknown error");
    if (errMsg.toLowerCase().includes("not found") || result.status === 404) {
      return [{ type: "text", text: notFoundText(memoryId) }];
    }
    return apiErrorResponse("Get", errMsg);
  } else {
    return apiErrorResponse("Get", `HTTP ${result.status}`);
  }
}

function notFoundText(memoryId: string): string {
  return [
    `❌ Memory not found: \`${memoryId}\``,
    "",
    "💡 **Tips**:",
    "- Verify the ID is correct (copy from memos_search results)",
    "- The memory may have been deleted",
    "- Try `memos_search` to find the memory again",
  ].join("\n");
}

// ============================================================================
// memos_get_stats
// ============================================================================

export async function handleMemosGetStats(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = getCubeIdFromArgs(arguments_);

  const [regSuccess, regError] = await ensureCubeRegistered(cubeId);
  if (!regSuccess) return cubeRegistrationError(cubeId, regError);

  const result = await apiCallWithRetry(
    "GET",
    `${MEMOS_URL}/memories`,
    cubeId,
    { params: { user_id: MEMOS_USER, mem_cube_id: cubeId } },
    ensureCubeRegistered
  );

  if (result.success && result.data) {
    const [stats, total] = computeMemoryStats((result.data as Record<string, unknown>).data as SearchData ?? {});

    if (total === 0) {
      return [{ type: "text", text: `No memories found in cube '${cubeId}'.` }];
    }

    const typeIcons: Record<string, string> = {
      BUGFIX: "🐛", ERROR_PATTERN: "🔴", DECISION: "📋",
      GOTCHA: "⚠️", CODE_PATTERN: "📝", CONFIG: "⚙️",
      FEATURE: "✨", MILESTONE: "🎯", PROGRESS: "📊", INFERRED: "🔗",
    };

    const result_lines = [`## 📊 Memory Stats: ${cubeId}`, `Total Memories: **${total}**`, ""];

    for (const [mtype, count] of Object.entries(stats).sort((a, b) => b[1] - a[1])) {
      const percentage = (count / total * 100).toFixed(1);
      const icon = typeIcons[mtype] ?? "📌";
      result_lines.push(`- ${icon} **${mtype}**: ${count} (${percentage}%)`);
    }

    const inferredCount = stats.INFERRED ?? 0;
    const progressCount = stats.PROGRESS ?? 0;
    const userTyped = total - inferredCount - progressCount;

    if (inferredCount > 0) {
      result_lines.push("", "---", "", `ℹ️ **INFERRED** (${inferredCount} 条): 图数据库自动生成的因果推断节点，非用户保存，属正常现象。`);
    }

    if (total > 0 && progressCount / total > 0.5) {
      result_lines.push("", "---", "", `⚠️ **PROGRESS 占比偏高** (${progressCount}/${total}): 保存时建议显式指定类型:`);
      result_lines.push("   `BUGFIX` · `DECISION` · `MILESTONE` · `FEATURE` · `GOTCHA` · `CONFIG`");
    }

    if (userTyped > 0) {
      result_lines.push("", `✅ **用户标注记忆**: ${userTyped} 条 (${(userTyped / total * 100).toFixed(0)}%)`);
    }

    return [{ type: "text", text: result_lines.join("\n") }];
  } else if (result.data) {
    return apiErrorResponse("Stats", String((result.data as Record<string, unknown>).message ?? "Unknown error"));
  } else {
    return apiErrorResponse("Stats", `HTTP ${result.status}`);
  }
}

// ============================================================================
// Helpers
// ============================================================================

export function extractMemoriesFromData(data: SearchData): MemoryNode[] {
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
