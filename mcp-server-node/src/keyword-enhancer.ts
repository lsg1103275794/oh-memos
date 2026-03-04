/**
 * Keyword Enhancer Module
 *
 * - Extended stopwords (programming/technical + Chinese)
 * - Fuzzy matching with Levenshtein distance
 * - Smart cube auto-detection from project path
 * - Structured field weighting
 */

// =============================================================================
// Extended Stopwords
// =============================================================================

export const ENGLISH_STOPWORDS: Set<string> = new Set([
  // General English
  "the", "and", "or", "a", "an", "to", "of", "for", "with", "in", "on",
  "at", "is", "are", "was", "were", "be", "been", "being", "this", "that",
  "it", "as", "from", "by", "about", "into", "over", "after", "before",
  "not", "but", "if", "then", "else", "when", "where", "which", "who",
  "whom", "whose", "why", "how", "all", "each", "every", "both", "few",
  "more", "most", "other", "some", "such", "no", "nor", "only", "own",
  "same", "so", "than", "too", "very", "just", "can", "will", "should",
  "would", "could", "may", "might", "must", "shall", "do", "does", "did",
  "doing", "done", "have", "has", "had", "having", "get", "got", "gets",
  "getting", "make", "makes", "made", "making", "go", "goes", "went",
  "going", "come", "comes", "came", "coming", "take", "takes", "took",
  "taking", "see", "sees", "saw", "seeing", "know", "knows", "knew",
  "knowing", "think", "thinks", "thought", "thinking", "want", "wants",
  "wanted", "wanting", "use", "uses", "used", "using", "find", "finds",
  "found", "finding", "give", "gives", "gave", "giving", "tell", "tells",
  "told", "telling", "say", "says", "said", "saying", "try", "tries",
  "tried", "trying", "need", "needs", "needed", "needing", "let", "lets",
  "put", "puts", "keep", "keeps", "kept", "keeping", "begin", "begins",
  "began", "beginning", "show", "shows", "showed", "showing",
  // Programming common words (usually not meaningful for search)
  "todo", "fixme", "hack", "note", "xxx", "temp", "tmp", "foo", "bar",
  "baz", "qux", "test", "example", "sample", "demo", "main", "index",
  "app", "application", "module", "package", "import", "export", "require",
  "define", "declare", "const", "var", "function", "class", "method",
  "return", "void", "null", "undefined", "true", "false", "new", "delete",
  "typeof", "instanceof", "catch", "finally", "throw", "async",
  "await", "yield", "public", "private", "protected", "static", "final",
  "abstract", "interface", "extends", "implements", "super", "self", "cls",
  "args", "kwargs", "param", "params", "arg", "argument", "arguments",
  "value", "values", "result", "results", "data", "info", "item", "items",
  "list", "array", "object", "dict", "map", "tuple", "string",
  "str", "int", "float", "bool", "boolean", "number", "num", "char",
  "byte", "bytes", "type", "types", "name", "names", "key", "keys",
  "val", "vals", "obj", "objs", "elem", "elems", "element", "elements",
  "node", "nodes", "attr", "attrs", "attribute", "attributes", "prop",
  "props", "property", "properties", "opt", "opts", "option", "options",
  "cfg", "conf", "config", "configuration", "setting", "settings",
  "env", "environment", "ctx", "context", "req", "request", "res",
  "response", "err", "error", "errors", "msg", "message", "messages",
  "log", "logs", "debug", "warn", "warning", "warnings", "input", "output",
  "out", "src", "source", "dest", "destination", "target", "path", "paths",
  "file", "files", "dir", "directory", "directories", "folder", "folders",
  "url", "urls", "uri", "uris", "id", "ids", "uid", "uuid", "guid",
  "ref", "refs", "reference", "references", "ptr", "pointer", "pointers",
  "handle", "handles", "callback", "callbacks", "handler", "handlers",
  "listener", "listeners", "event", "events", "action", "actions",
  "state", "states", "status", "flag", "flags", "mode", "modes",
  "level", "levels", "size", "sizes", "length", "len", "count", "counts",
  "total", "sum", "avg", "average", "min", "max", "first", "last",
  "prev", "previous", "next", "current", "cur", "old", "start", "end",
  "init", "initialize", "initialized", "setup", "teardown", "cleanup",
  "reset", "clear", "load", "save", "post", "update", "remove", "insert",
  "append", "push", "pop", "shift", "unshift", "sub", "mul", "div",
  "mod", "xor", "bit", "bits", "word", "words", "line", "lines",
  "row", "rows", "col", "column", "columns", "cell", "cells", "grid",
  "grids", "table", "tables", "record", "records", "field", "fields",
  "schema", "schemas", "model", "models", "view", "views", "controller",
  "controllers", "service", "services", "repository", "repositories",
  "factory", "factories", "builder", "builders", "adapter", "adapters",
  "wrapper", "wrappers", "helper", "helpers", "util", "utils", "utility",
  "utilities", "tool", "tools", "lib", "library", "libraries", "framework",
  "frameworks", "plugin", "plugins", "extension", "extensions",
  "component", "components", "widget", "widgets", "block", "blocks",
  "section", "sections", "part", "parts", "piece", "pieces", "chunk",
  "chunks", "segment", "segments", "unit", "units", "modules", "system",
  "systems", "layer", "layers", "process", "processes", "thread", "threads",
  "task", "tasks", "job", "jobs", "work", "works", "worker", "workers",
  "queue", "queues", "stack", "stacks", "pool", "pools", "cache", "caches",
  "buffer", "buffers", "stream", "streams", "pipe", "pipes", "channel",
  "channels", "socket", "sockets", "port", "ports", "host", "hosts",
  "server", "servers", "client", "clients", "user", "users", "admin",
  "admins", "root", "guest", "account", "accounts", "profile", "profiles",
  "session", "sessions", "token", "tokens", "auth", "authentication",
  "authorization", "permission", "permissions", "role", "roles", "access",
  "grant", "grants", "deny", "denies", "filter", "filters",
  "validate", "validates", "validation", "check", "checks", "verify",
  "verifies", "verification", "confirm", "confirms", "confirmation",
  "approve", "approves", "approval", "reject", "rejects", "rejection",
  "accept", "accepts", "acceptance", "decline", "declines", "cancel",
  "cancels", "cancellation", "abort", "aborts", "retry", "retries",
  "timeout", "timeouts", "expire", "expires", "expiration",
  "refresh", "refreshes", "renew", "renews", "renewal",
]);

export const CHINESE_STOPWORDS: Set<string> = new Set([
  "的", "了", "和", "与", "在", "是", "有", "我", "你", "他", "她", "它",
  "我们", "你们", "他们", "她们", "它们", "这", "那", "这个", "那个",
  "这些", "那些", "这里", "那里", "这儿", "那儿", "什么", "怎么", "怎样",
  "如何", "为什么", "哪", "哪个", "哪些", "哪里", "哪儿", "谁", "多少",
  "几", "多", "少", "大", "小", "好", "坏", "对", "错", "行", "不行",
  "可以", "不可以", "能", "不能", "会", "不会", "要", "不要", "想",
  "不想", "应该", "不应该", "必须", "不必", "可能", "不可能", "一定",
  "也许", "或许", "大概", "肯定", "当然", "确实", "真的", "假的",
  "及", "或", "或者", "还是", "以及", "并", "并且", "而",
  "而且", "但", "但是", "不过", "然而", "可是", "虽然", "尽管", "即使",
  "如果", "假如", "要是", "只要", "除非", "无论", "不管", "不论",
  "因为", "由于", "所以", "因此", "因而", "于是", "那么", "这样",
  "既然", "只有", "才", "就", "便", "却", "倒", "反而", "否则",
  "不然", "要不", "要不然", "要么", "以便", "以免", "以致", "为了",
  "为着", "对于", "关于", "至于", "根据", "按照", "依照", "通过",
  "经过", "随着", "沿着", "顺着", "朝着", "向着", "趁着", "除了",
  "除开", "除去", "除却", "除外",
  "自己", "自身", "本人", "本身", "彼此", "相互", "互相", "大家",
  "各位", "诸位", "各自", "某", "某个", "某些", "其", "其中", "其他",
  "其它", "其余", "另", "另外", "另一", "别", "别的", "任何", "一切",
  "所有", "全部", "整个", "每", "每个", "各", "各个", "同", "同一",
  "同样", "一样", "一般", "一种", "某种", "这种", "那种", "各种",
  "现在", "目前", "当前", "眼前", "此时", "此刻", "刚才", "方才",
  "刚刚", "正在", "正", "将", "将要", "快要", "就要", "已经", "已",
  "曾", "曾经", "过去", "以前", "之前", "以后", "之后", "后来", "然后",
  "接着", "继而", "随后", "最后", "最终", "终于", "始终", "一直",
  "常常", "经常", "往往", "总是", "老是", "有时", "有时候", "偶尔",
  "突然", "忽然", "马上", "立刻", "立即", "赶紧", "赶快", "连忙",
  "从来", "一向", "向来", "素来", "历来", "原来", "本来", "起初",
  "很", "非常", "十分", "极", "极其", "极为", "特别", "尤其", "格外",
  "更", "更加", "越", "越发", "越来越", "最", "顶", "太", "过于",
  "稍", "稍微", "略", "略微", "比较", "相当", "相对", "颇", "挺",
  "不", "没", "没有", "未", "尚未", "并不", "并非", "并没", "并没有",
  "也", "还", "又", "再", "仍", "仍然", "依然", "依旧", "照样",
  "都", "全", "全都", "皆", "均", "统统", "通通", "一概", "一律",
  "只", "只是", "仅", "仅仅", "光", "单", "单独",
  "啊", "呀", "哇", "哦", "噢", "哎", "唉", "嗨", "喂", "嘿",
  "嗯", "哼", "吧", "呢", "吗", "嘛", "啦", "喽", "呗",
  "罢了", "而已", "罢", "地", "得", "着", "过", "们",
  "做", "用", "把", "被", "给", "让", "叫", "使",
  "令", "请", "来", "去", "到", "进", "出", "上", "下", "起", "开",
  "关", "拿", "放", "看", "听", "说", "写", "读",
]);

export const ALL_STOPWORDS: Set<string> = new Set([
  ...ENGLISH_STOPWORDS,
  ...CHINESE_STOPWORDS,
]);

// =============================================================================
// Fuzzy Matching
// =============================================================================

export function levenshteinDistance(s1: string, s2: string): number {
  if (s1.length < s2.length) {
    [s1, s2] = [s2, s1];
  }
  if (s2.length === 0) return s1.length;

  let previousRow: number[] = Array.from({ length: s2.length + 1 }, (_, i) => i);

  for (let i = 0; i < s1.length; i++) {
    const currentRow: number[] = [i + 1];
    for (let j = 0; j < s2.length; j++) {
      const insertions = previousRow[j + 1] + 1;
      const deletions = currentRow[j] + 1;
      const substitutions = previousRow[j] + (s1[i] !== s2[j] ? 1 : 0);
      currentRow.push(Math.min(insertions, deletions, substitutions));
    }
    previousRow = currentRow;
  }

  return previousRow[previousRow.length - 1];
}

export function fuzzyMatchScore(
  query: string,
  text: string,
  threshold = 0.7
): number {
  if (!query || !text) return 0.0;

  const queryLower = query.toLowerCase();
  const textLower = text.toLowerCase();

  if (queryLower === textLower) return 1.0;
  if (textLower.includes(queryLower)) return 0.9;

  const maxLen = Math.max(queryLower.length, textLower.length);
  if (maxLen === 0) return 0.0;

  const distance = levenshteinDistance(queryLower, textLower);
  const similarity = 1 - distance / maxLen;

  return similarity >= threshold ? similarity : 0.0;
}

export function findFuzzyMatches(
  keyword: string,
  text: string,
  threshold = 0.7,
  maxWordLenDiff = 3
): Array<[string, number]> {
  if (!keyword || !text) return [];

  const matches: Array<[string, number]> = [];
  const keywordLower = keyword.toLowerCase();
  const keywordLen = keywordLower.length;

  const words = text.match(/[A-Za-z0-9_]+|[\u4e00-\u9fff]+/g) ?? [];

  for (const word of words) {
    const wordLower = word.toLowerCase();
    const wordLen = wordLower.length;

    if (Math.abs(wordLen - keywordLen) > maxWordLenDiff) continue;

    const score = fuzzyMatchScore(keywordLower, wordLower, threshold);
    if (score > 0) {
      matches.push([word, score]);
    }
  }

  return matches.sort((a, b) => b[1] - a[1]);
}

// =============================================================================
// Smart Cube Detection
// =============================================================================

export function detectCubeFromPath(projectPath?: string): string {
  const targetPath = projectPath ?? process.cwd();

  // Normalize: handle Windows backslashes
  const normalized = targetPath.replace(/\\/g, "/");

  // Extract folder name (last segment)
  const segments = normalized.replace(/\/$/, "").split("/");
  let folderName = segments[segments.length - 1] ?? "";

  // Windows drive handling: "G:" → empty, take next
  if (/^[A-Za-z]:$/.test(folderName)) {
    folderName = segments[segments.length - 2] ?? "default";
  }

  if (!folderName) return "default_cube";

  // Normalize: lowercase, replace -, ., space with _
  let cubeId = folderName.toLowerCase();
  cubeId = cubeId.replace(/[-.\s]+/g, "_");
  cubeId = cubeId.replace(/[^a-z0-9_]/g, "");

  // Ensure doesn't start with digit
  if (cubeId && /^\d/.test(cubeId)) {
    cubeId = "_" + cubeId;
  }

  if (!cubeId.endsWith("_cube")) {
    cubeId = cubeId + "_cube";
  }

  return cubeId || "default_cube";
}

// =============================================================================
// Enhanced Keyword Extraction and Scoring
// =============================================================================

export function extractKeywordsEnhanced(
  query: string,
  stopwords: Set<string> = ALL_STOPWORDS,
  minLength = 2
): string[] {
  if (!query) return [];

  const rawTokens = query.match(/[A-Za-z0-9_]+|[\u4e00-\u9fff]+/g) ?? [];
  const keywords: string[] = [];
  const seen = new Set<string>();

  for (const token of rawTokens) {
    if (!token) continue;

    // Chinese token
    if (/[\u4e00-\u9fff]/.test(token)) {
      if (token.length < minLength) continue;
      if (stopwords.has(token)) continue;
      if (!seen.has(token)) {
        keywords.push(token);
        seen.add(token);
      }
      continue;
    }

    // English token
    const lowered = token.toLowerCase();
    if (lowered.length < minLength) continue;
    if (stopwords.has(lowered)) continue;
    if (!seen.has(lowered)) {
      keywords.push(lowered);
      seen.add(lowered);
    }
  }

  return keywords;
}

export function keywordMatchScoreEnhanced(
  text: string,
  keywords: string[],
  metadata?: Record<string, unknown>,
  enableFuzzy = true,
  fuzzyThreshold = 0.75
): number {
  if (!text || keywords.length === 0) return 0.0;

  const textLower = text.toLowerCase();
  let score = 0.0;
  let matchedCount = 0;

  const keyField = metadata ? String(metadata.key ?? "").toLowerCase() : "";
  const rawTags = metadata?.tags;
  const tags: string[] = Array.isArray(rawTags)
    ? rawTags.map((t) => String(t).toLowerCase())
    : [];

  for (const kw of keywords) {
    const kwLower = kw.toLowerCase();
    const isChinese = /[\u4e00-\u9fff]/.test(kw);
    let kwMatched = false;

    // 1. Key field match (highest weight)
    if (keyField && (keyField.includes(kwLower) || (isChinese && keyField.includes(kw)))) {
      score += 5.0;
      kwMatched = true;
    }

    // 2. Tags match
    for (const tag of tags) {
      if (tag.includes(kwLower) || (isChinese && tag.includes(kw))) {
        score += 3.0;
        kwMatched = true;
        break;
      }
    }

    // 3. Text match
    if (isChinese) {
      if (text.includes(kw)) {
        score += 2.0;
        kwMatched = true;
      }
    } else {
      const wordBoundaryRegex = new RegExp(`\\b${escapeRegex(kwLower)}\\b`);
      if (wordBoundaryRegex.test(textLower)) {
        score += 2.5;
        kwMatched = true;
      } else if (textLower.includes(kwLower)) {
        score += 1.5;
        kwMatched = true;
      }
    }

    // 4. Fuzzy match
    if (enableFuzzy && !kwMatched && !isChinese) {
      const fuzzyMatches = findFuzzyMatches(kwLower, textLower, fuzzyThreshold);
      if (fuzzyMatches.length > 0) {
        score += fuzzyMatches[0][1] * 1.0;
        kwMatched = true;
      }
    }

    if (kwMatched) matchedCount++;
  }

  // Coverage bonus
  if (matchedCount > 0) {
    const coverage = matchedCount / keywords.length;
    score += coverage * 1.5;
  }

  return score;
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
