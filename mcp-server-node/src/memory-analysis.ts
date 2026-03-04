/**
 * Memory Analysis Module
 *
 * Generates search suggestions based on context.
 */

import { extractKeywords } from "./query-processing.js";

const MEMORY_TYPE_KEYWORDS: Record<string, string[]> = {
  ERROR_PATTERN: ["error", "bug", "exception", "fail", "crash", "traceback", "错误", "异常", "失败"],
  DECISION: ["decision", "decided", "choose", "选择", "决定", "方案", "架构"],
  BUGFIX: ["fix", "fixed", "patch", "repair", "修复", "解决"],
  GOTCHA: ["gotcha", "trap", "caveat", "workaround", "注意", "陷阱", "坑"],
  CODE_PATTERN: ["pattern", "template", "snippet", "example", "模板", "示例"],
  CONFIG: ["config", "configuration", "setting", "env", "配置", "环境"],
  MILESTONE: ["milestone", "completed", "released", "shipped", "完成", "里程碑"],
  FEATURE: ["feature", "added", "implemented", "new", "新功能", "实现"],
};

export function suggestSearchQueries(context: string): string[] {
  if (!context) return [];

  const suggestions: string[] = [];
  const contextLower = context.toLowerCase();

  // Check for memory type keywords
  for (const [memType, keywords] of Object.entries(MEMORY_TYPE_KEYWORDS)) {
    if (keywords.some((kw) => contextLower.includes(kw))) {
      const extracted = extractKeywords(context);
      if (extracted.length > 0) {
        suggestions.push(`${memType} ${extracted.slice(0, 2).join(" ")}`);
      } else {
        suggestions.push(memType);
      }
    }
  }

  // Add generic keyword-based suggestions
  const keywords = extractKeywords(context).slice(0, 3);
  if (keywords.length > 0 && suggestions.length === 0) {
    suggestions.push(keywords.join(" "));
    if (keywords.length > 1) {
      suggestions.push(keywords[0]);
    }
  }

  // Remove duplicates and limit to 5
  return [...new Set(suggestions)].slice(0, 5);
}
