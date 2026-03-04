/**
 * Calendar Handler
 *
 * memos_calendar - project mode and student mode
 */

import { MEMOS_URL, MEMOS_USER } from "../config.js";
import { apiCallWithRetry } from "../api-client.js";
import { ensureCubeRegistered } from "../cube-manager.js";
import type { TextContent, MemoryNode, SearchData } from "../types.js";
import { apiErrorResponse, cubeRegistrationError, getCubeIdFromArgs } from "./utils.js";

// ============================================================================
// Date Utilities
// ============================================================================

function getSemesterDates(semester: string): [Date, Date] {
  const now = new Date();

  if (semester === "current") {
    const year = now.getFullYear();
    const month = now.getMonth() + 1; // 1-based
    if (month >= 9) {
      return [new Date(year, 8, 1), new Date(year, 11, 31)];
    } else if (month >= 2) {
      return [new Date(year, 1, 1), new Date(year, 5, 30)];
    } else {
      return [new Date(year - 1, 8, 1), new Date(year - 1, 11, 31)];
    }
  }

  const parts = semester.split("-");
  if (parts.length === 2) {
    const year = parseInt(parts[0]);
    const season = parts[1].toLowerCase();
    if (!isNaN(year)) {
      if (season === "spring") return [new Date(year, 1, 1), new Date(year, 5, 30)];
      if (season === "fall") return [new Date(year, 8, 1), new Date(year, 11, 31)];
      if (season === "summer") return [new Date(year, 6, 1), new Date(year, 7, 31)];
    }
  }

  return [new Date(now.getFullYear(), now.getMonth(), 1), now];
}

function getWeekDates(semesterStart: Date, week: number): [Date, Date] {
  const weekStart = new Date(semesterStart.getTime() + (week - 1) * 7 * 24 * 60 * 60 * 1000);
  const dayOfWeek = weekStart.getDay();
  const monday = new Date(weekStart.getTime() - ((dayOfWeek + 6) % 7) * 24 * 60 * 60 * 1000);
  const sunday = new Date(monday.getTime() + 6 * 24 * 60 * 60 * 1000);
  return [monday, sunday];
}

// ============================================================================
// Project Timeline Formatter
// ============================================================================

function formatProjectTimeline(memories: MemoryNode[], cubeId: string): string {
  const lines: string[] = [];
  lines.push(`## 🗓️ Project Timeline — ${cubeId}`, "");

  const projectTypes = new Set(["MILESTONE", "DECISION", "FEATURE", "BUGFIX", "ERROR_PATTERN", "GOTCHA"]);

  const projectMems = memories.filter((m) => {
    const t = String((m as Record<string, unknown>).memory_type ?? (m as Record<string, unknown>).type ?? "").toUpperCase();
    return projectTypes.has(t);
  });

  if (projectMems.length === 0) {
    lines.push("_No project milestones or decisions found._", "");
    lines.push('Save memories with: memos_save(..., memory_type="MILESTONE")');
    return lines.join("\n");
  }

  // Group by year-month
  const byMonth: Record<string, typeof projectMems> = {};
  for (const mem of projectMems) {
    const created = String((mem as Record<string, unknown>).created_at ?? (mem as Record<string, unknown>).timestamp ?? "");
    const monthStr = created.length >= 7 ? created.slice(0, 7) : "unknown";
    if (!byMonth[monthStr]) byMonth[monthStr] = [];
    byMonth[monthStr].push(mem);
  }

  const sortedMonths = Object.keys(byMonth).sort().reverse();

  for (const monthStr of sortedMonths) {
    const mems = byMonth[monthStr];
    lines.push(`**${monthStr}**`);
    for (let i = 0; i < mems.length; i++) {
      const mem = mems[i];
      const memType = String((mem as Record<string, unknown>).memory_type ?? (mem as Record<string, unknown>).type ?? "NOTE").toUpperCase();
      const content = String((mem as Record<string, unknown>).content ?? mem.key ?? "");
      const summary = content.split("\n")[0].slice(0, 80);
      const connector = i === mems.length - 1 ? "└──" : "├──";
      lines.push(`  ${connector} [${memType}] ${summary}`);
    }
    lines.push("");
  }

  const typeCounts: Record<string, number> = {};
  for (const mem of projectMems) {
    const t = String((mem as Record<string, unknown>).memory_type ?? "OTHER").toUpperCase();
    typeCounts[t] = (typeCounts[t] ?? 0) + 1;
  }

  lines.push(`📊 Total: ${projectMems.length} entries across ${sortedMonths.length} month(s)`);
  const typeStr = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}:${v}`).join(", ");
  lines.push(`   Types: ${typeStr}`);

  return lines.join("\n");
}

// ============================================================================
// Calendar View Formatter
// ============================================================================

function formatCalendarOutput(
  memories: MemoryNode[],
  semester: string,
  course: string | undefined,
  week: number | undefined,
  view: string
): string {
  const lines: string[] = [];

  if (course) {
    lines.push(`## 📅 ${semester} - ${course}`);
  } else {
    lines.push(`## 📅 ${semester} 学期笔记`);
  }
  lines.push("");

  if (memories.length === 0) {
    lines.push("_暂无笔记_");
    return lines.join("\n");
  }

  // Group by date
  const byDate: Record<string, MemoryNode[]> = {};
  for (const mem of memories) {
    const created = String((mem as Record<string, unknown>).created_at ?? (mem as Record<string, unknown>).timestamp ?? "");
    const dateStr = created ? created.slice(0, 10) : new Date().toISOString().slice(0, 10);
    if (!byDate[dateStr]) byDate[dateStr] = [];
    byDate[dateStr].push(mem);
  }

  const sortedDates = Object.keys(byDate).sort().reverse();

  if (view === "list") {
    lines.push("| 日期 | 类型 | 内容摘要 |");
    lines.push("|------|------|---------|");

    for (const dateStr of sortedDates.slice(0, 20)) {
      for (const mem of byDate[dateStr]) {
        const memType = String((mem as Record<string, unknown>).memory_type ?? (mem as Record<string, unknown>).type ?? "NOTE");
        let content = String((mem as Record<string, unknown>).content ?? mem.key ?? "").slice(0, 50);
        if (content.length === 50) content += "...";
        content = content.replace(/\|/g, "\\|").replace(/\n/g, " ");
        lines.push(`| ${dateStr} | ${memType} | ${content} |`);
      }
    }
  } else if (view === "week") {
    if (week) lines.push(`### 第 ${week} 周`);
    lines.push("");

    const weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
    for (const dateStr of sortedDates.slice(0, 7)) {
      try {
        const dt = new Date(dateStr);
        const weekday = weekdays[(dt.getDay() + 6) % 7];
        lines.push(`**${dateStr} ${weekday}**`);
      } catch {
        lines.push(`**${dateStr}**`);
      }

      for (const mem of byDate[dateStr]) {
        const memType = String((mem as Record<string, unknown>).memory_type ?? (mem as Record<string, unknown>).type ?? "NOTE");
        const content = String((mem as Record<string, unknown>).content ?? mem.key ?? "").slice(0, 60).replace(/\n/g, " ");
        lines.push(`- [${memType}] ${content}`);
      }
      lines.push("");
    }
  } else {
    // month view
    lines.push("| 日期 | 笔记数 | 类型分布 |");
    lines.push("|------|--------|---------|");

    for (const dateStr of sortedDates.slice(0, 30)) {
      const mems = byDate[dateStr];
      const types: Record<string, number> = {};
      for (const m of mems) {
        const t = String((m as Record<string, unknown>).memory_type ?? "OTHER");
        types[t] = (types[t] ?? 0) + 1;
      }
      const typeStr = Object.entries(types).map(([k, v]) => `${k}:${v}`).join(", ");
      lines.push(`| ${dateStr} | ${mems.length} | ${typeStr} |`);
    }
  }

  const total = memories.length;
  const typeCounts: Record<string, number> = {};
  for (const mem of memories) {
    const t = String((mem as Record<string, unknown>).memory_type ?? "OTHER");
    typeCounts[t] = (typeCounts[t] ?? 0) + 1;
  }

  lines.push("");
  lines.push(`📊 总计: ${total} 条笔记`);
  if (Object.keys(typeCounts).length > 0) {
    const typeStr = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}:${v}`).join(", ");
    lines.push(`   类型: ${typeStr}`);
  }

  return lines.join("\n");
}

// ============================================================================
// memos_calendar
// ============================================================================

export async function handleMemosCalendar(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = getCubeIdFromArgs(arguments_);
  const mode = String(arguments_.mode ?? "student");
  const semester = String(arguments_.semester ?? "current");
  const course = arguments_.course ? String(arguments_.course) : undefined;
  const week = arguments_.week !== undefined ? Number(arguments_.week) : undefined;
  const view = String(arguments_.view ?? "list");

  const [regSuccess, regError] = await ensureCubeRegistered(cubeId);
  if (!regSuccess) return cubeRegistrationError(cubeId, regError);

  if (mode === "project") {
    const result = await apiCallWithRetry(
      "GET",
      `${MEMOS_URL}/memories`,
      cubeId,
      { params: { user_id: MEMOS_USER, mem_cube_id: cubeId, limit: 200 } },
      ensureCubeRegistered
    );

    if (result.success && result.data) {
      const resultData = (result.data as Record<string, unknown>).data as SearchData ?? {};
      const memories: MemoryNode[] = [];
      for (const cubeData of resultData.text_mem ?? []) {
        const memData = cubeData.memories;
        if (memData && !Array.isArray(memData) && memData.nodes) {
          memories.push(...memData.nodes);
        } else if (Array.isArray(memData)) {
          memories.push(...(memData as MemoryNode[]));
        }
      }
      const output = formatProjectTimeline(memories, cubeId);
      return [{ type: "text", text: output }];
    } else if (result.data) {
      return apiErrorResponse("Calendar", String((result.data as Record<string, unknown>).message ?? "Unknown error"));
    } else {
      return apiErrorResponse("Calendar", `HTTP ${result.status}`);
    }
  }

  // Student mode
  let [startDate, endDate] = getSemesterDates(semester);
  if (week !== undefined) {
    [startDate, endDate] = getWeekDates(startDate, week);
  }

  const result = await apiCallWithRetry(
    "GET",
    `${MEMOS_URL}/memories`,
    cubeId,
    { params: { user_id: MEMOS_USER, mem_cube_id: cubeId, limit: 100 } },
    ensureCubeRegistered
  );

  if (result.success && result.data) {
    const resultData = (result.data as Record<string, unknown>).data as SearchData ?? {};
    let memories: MemoryNode[] = [];
    for (const cubeData of resultData.text_mem ?? []) {
      const memData = cubeData.memories;
      if (memData && !Array.isArray(memData) && memData.nodes) {
        memories.push(...memData.nodes);
      } else if (Array.isArray(memData)) {
        memories.push(...(memData as MemoryNode[]));
      }
    }

    // Filter by course
    if (course) {
      const courseLower = course.toLowerCase();
      memories = memories.filter(
        (m) =>
          String((m as Record<string, unknown>).content ?? "").toLowerCase().includes(courseLower) ||
          String((m as Record<string, unknown>).tags ?? "").toLowerCase().includes(courseLower)
      );
    }

    // Filter by date range
    const filtered: MemoryNode[] = [];
    for (const mem of memories) {
      const created = String((mem as Record<string, unknown>).created_at ?? "");
      if (created) {
        try {
          const dt = new Date(created.replace("Z", "+00:00"));
          const dtNoTz = new Date(dt.getFullYear(), dt.getMonth(), dt.getDate());
          if (dtNoTz >= startDate && dtNoTz <= endDate) {
            filtered.push(mem);
          }
        } catch {
          filtered.push(mem);
        }
      } else {
        filtered.push(mem);
      }
    }

    const output = formatCalendarOutput(filtered, semester, course, week, view);
    return [{ type: "text", text: output }];
  } else if (result.data) {
    return apiErrorResponse("Calendar", String((result.data as Record<string, unknown>).message ?? "Unknown error"));
  } else {
    return apiErrorResponse("Calendar", `HTTP ${result.status}`);
  }
}
