#!/usr/bin/env python3
"""
Keyword Enhancer Module for MemOS MCP Server

Features:
1. Extended stopwords (programming/technical + Chinese)
2. Fuzzy matching with Levenshtein distance
3. Smart cube auto-detection from project path
4. Structured field weighting (key, tags)
"""

import os
import re

from pathlib import Path


# =============================================================================
# Extended Stopwords - Programming & Technical Terms
# =============================================================================

# English programming stopwords (common but meaningless in code search)
ENGLISH_STOPWORDS = {
    # General English
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
    "tried", "trying", "need", "needs", "needed", "needing", "seem", "seems",
    "seemed", "seeming", "let", "lets", "leave", "leaves", "left", "leaving",
    "put", "puts", "keep", "keeps", "kept", "keeping", "begin", "begins",
    "began", "beginning", "show", "shows", "showed", "showing", "hear",
    "hears", "heard", "hearing", "play", "plays", "played", "playing",
    "run", "runs", "ran", "running", "move", "moves", "moved", "moving",
    "like", "likes", "liked", "liking", "live", "lives", "lived", "living",
    "believe", "believes", "believed", "believing", "hold", "holds", "held",
    "holding", "bring", "brings", "brought", "bringing", "happen", "happens",
    "happened", "happening", "write", "writes", "wrote", "writing", "sit",
    "sits", "sat", "sitting", "stand", "stands", "stood", "standing", "lose",
    "loses", "lost", "losing", "pay", "pays", "paid", "paying", "meet",
    "meets", "met", "meeting", "include", "includes", "included", "including",
    "continue", "continues", "continued", "continuing", "set", "sets",
    "learn", "learns", "learned", "learning", "change", "changes", "changed",
    "changing", "lead", "leads", "led", "leading", "understand", "understands",
    "understood", "understanding", "watch", "watches", "watched", "watching",
    "follow", "follows", "followed", "following", "stop", "stops", "stopped",
    "stopping", "create", "creates", "created", "creating", "speak", "speaks",
    "spoke", "speaking", "read", "reads", "allow", "allows", "allowed",
    "allowing", "add", "adds", "added", "adding", "spend", "spends", "spent",
    "spending", "grow", "grows", "grew", "growing", "open", "opens", "opened",
    "opening", "walk", "walks", "walked", "walking", "win", "wins", "won",
    "winning", "offer", "offers", "offered", "offering", "remember", "remembers",
    "remembered", "remembering", "consider", "considers", "considered",
    "considering", "appear", "appears", "appeared", "appearing", "buy", "buys",
    "bought", "buying", "wait", "waits", "waited", "waiting", "serve", "serves",
    "served", "serving", "die", "dies", "died", "dying", "send", "sends",
    "sent", "sending", "expect", "expects", "expected", "expecting", "build",
    "builds", "built", "building", "stay", "stays", "stayed", "staying",
    "fall", "falls", "fell", "falling", "cut", "cuts", "reach", "reaches",
    "reached", "reaching", "kill", "kills", "killed", "killing", "remain",
    "remains", "remained", "remaining",
    # Programming common words (usually not meaningful for search)
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
    "log", "logs", "debug", "warn", "warning", "warnings", "input", "output", "out", "src", "source", "dest", "destination",
    "target", "path", "paths", "file", "files", "dir", "directory",
    "directories", "folder", "folders", "url", "urls", "uri", "uris",
    "id", "ids", "uid", "uuid", "guid", "ref", "refs", "reference",
    "references", "ptr", "pointer", "pointers", "handle", "handles",
    "callback", "callbacks", "handler", "handlers", "listener", "listeners",
    "event", "events", "action", "actions", "state", "states", "status",
    "flag", "flags", "mode", "modes", "level", "levels", "size", "sizes",
    "length", "len", "count", "counts", "total", "sum", "avg", "average",
    "min", "max", "first", "last", "prev", "previous", "next", "current",
    "cur", "old", "start", "end", "init",
    "initialize", "initialized", "setup", "teardown", "cleanup", "reset",
    "clear", "load", "save", "post", "update", "remove", "insert", "append",
    "push", "pop", "shift", "unshift", "sub", "mul", "div",
    "mod", "xor", "bit", "bits", "word", "words", "line", "lines", "row", "rows", "col", "column",
    "columns", "cell", "cells", "grid", "grids", "table", "tables",
    "record", "records", "field", "fields", "schema", "schemas", "model",
    "models", "view", "views", "controller", "controllers", "service",
    "services", "repository", "repositories", "factory", "factories",
    "builder", "builders", "adapter", "adapters", "wrapper", "wrappers",
    "helper", "helpers", "util", "utils", "utility", "utilities", "tool",
    "tools", "lib", "library", "libraries", "framework", "frameworks",
    "plugin", "plugins", "extension", "extensions", "addon", "addons",
    "component", "components", "widget", "widgets", "block", "blocks", "section", "sections", "part", "parts", "piece",
    "pieces", "chunk", "chunks", "segment", "segments", "fragment",
    "fragments", "unit", "units", "modules", "system", "systems",
    "subsystem", "subsystems", "layer", "layers", "tier", "tiers",
    "process", "processes", "thread", "threads", "task", "tasks", "job",
    "jobs", "work", "works", "worker", "workers", "queue", "queues",
    "stack", "stacks", "heap", "heaps", "pool", "pools", "cache", "caches",
    "buffer", "buffers", "stream", "streams", "pipe", "pipes", "channel",
    "channels", "socket", "sockets", "port", "ports", "host", "hosts",
    "server", "servers", "client", "clients", "user", "users", "admin",
    "admins", "root", "guest", "account", "accounts", "profile", "profiles",
    "session", "sessions", "token", "tokens", "auth", "authentication",
    "authorization", "permission", "permissions", "role", "roles", "access",
    "grant", "grants", "deny", "denies", "filter", "filters", "validate", "validates", "validation",
    "check", "checks", "verify", "verifies", "verification", "confirm",
    "confirms", "confirmation", "approve", "approves", "approval", "reject",
    "rejects", "rejection", "accept", "accepts", "acceptance", "decline",
    "declines", "cancel", "cancels", "cancellation", "abort", "aborts",
    "retry", "retries", "timeout", "timeouts", "expire", "expires",
    "expiration", "refresh", "refreshes", "renew", "renews", "renewal",
}

# Chinese stopwords (comprehensive list from multiple sources)
CHINESE_STOPWORDS = {
    # Common functional words
    "的", "了", "和", "与", "在", "是", "有", "我", "你", "他", "她", "它",
    "我们", "你们", "他们", "她们", "它们", "这", "那", "这个", "那个",
    "这些", "那些", "这里", "那里", "这儿", "那儿", "什么", "怎么", "怎样",
    "如何", "为什么", "哪", "哪个", "哪些", "哪里", "哪儿", "谁", "多少",
    "几", "多", "少", "大", "小", "好", "坏", "对", "错", "行", "不行",
    "可以", "不可以", "能", "不能", "会", "不会", "要", "不要", "想",
    "不想", "应该", "不应该", "必须", "不必", "可能", "不可能", "一定",
    "也许", "或许", "大概", "肯定", "当然", "确实", "真的", "假的",
    # Conjunctions and prepositions
    "及", "或", "或者", "还是", "以及", "并", "并且", "而",
    "而且", "但", "但是", "不过", "然而", "可是", "虽然", "尽管", "即使",
    "如果", "假如", "要是", "只要", "除非", "无论", "不管", "不论",
    "因为", "由于", "所以", "因此", "因而", "于是", "那么", "这样",
    "既然", "只有", "才", "就", "便", "却", "倒", "反而", "否则",
    "不然", "要不", "要不然", "要么", "以便", "以免", "以致", "为了", "为着", "对于", "关于", "至于",
    "根据", "按照", "依照", "通过", "经过", "随着", "沿着", "顺着",
    "朝着", "向着", "趁着", "除了", "除开", "除去", "除却", "除外",
    # Pronouns and determiners
    "自己", "自身", "本人", "本身", "彼此", "相互", "互相", "大家",
    "各位", "诸位", "各自", "某", "某个", "某些", "其", "其中", "其他",
    "其它", "其余", "另", "另外", "另一", "别", "别的", "任何", "一切",
    "所有", "全部", "整个", "每", "每个", "各", "各个", "同", "同一",
    "同样", "一样", "一般", "一种", "某种", "这种", "那种", "各种",
    # Time words
    "现在", "目前", "当前", "眼前", "此时", "此刻", "刚才", "方才",
    "刚刚", "正在", "正", "将", "将要", "快要", "就要", "已经", "已",
    "曾", "曾经", "过去", "以前", "之前", "以后", "之后", "后来", "然后",
    "接着", "继而", "随后", "最后", "最终", "终于", "始终", "一直",
    "常常", "经常", "往往", "总是", "老是", "有时", "有时候", "偶尔",
    "突然", "忽然", "马上", "立刻", "立即", "赶紧", "赶快", "连忙",
    "从来", "一向", "向来", "素来", "历来", "原来", "本来", "起初",
    "起先", "首先", "开始", "当初", "当时", "那时", "彼时", "此时",
    # Adverbs
    "很", "非常", "十分", "极", "极其", "极为", "特别", "尤其", "格外",
    "更", "更加", "越", "越发", "越来越", "最", "顶", "太", "过于",
    "稍", "稍微", "略", "略微", "比较", "相当", "相对", "颇", "挺",
    "蛮", "怪", "真", "实在", "的确", "果然", "果真", "居然",
    "竟然", "竟", "简直", "几乎", "差不多", "大约", "左右",
    "上下", "前后", "之间", "不", "没", "没有", "未", "尚未", "并不", "并非", "并没", "并没有", "也", "还", "又", "再", "仍",
    "仍然", "依然", "依旧", "照样", "照旧", "照常", "本", "原", "原本",
    "根本", "压根", "完全", "全", "全都", "都", "皆", "均",
    "俱", "统统", "通通", "一概", "一律", "一并", "一同", "一起",
    "一齐", "同时", "一块", "一块儿", "一道", "只", "只是", "仅", "仅仅", "光", "光是", "单", "单单", "单独",
    "独", "独自", "唯", "唯独", "唯有", "方", "刚", "恰", "恰好", "恰巧", "正好", "正巧",
    # Particles and interjections
    "啊", "呀", "哇", "哦", "噢", "哎", "哎呀", "哎哟", "唉", "嗨",
    "喂", "嘿", "呃", "嗯", "哼", "呵", "嘻", "呸", "咦", "哈", "嘿嘿",
    "哈哈", "呵呵", "嘻嘻", "吧", "呢", "吗", "嘛", "啦", "喽", "呗",
    "罢了", "而已", "罢", "地", "得", "着", "过", "们",
    # Common verbs (often meaningless in search)
    "做", "用", "把", "被", "给", "让", "叫", "使",
    "令", "请", "来", "去", "到", "进", "出", "上", "下", "起", "开",
    "关", "拿", "放", "看", "听", "说", "写", "读", "觉得", "认为",
    "知道", "了解", "明白", "清楚", "理解", "相信", "希望", "期望",
    "盼望", "愿意", "喜欢", "讨厌", "害怕", "担心", "感觉", "感到",
    "发现", "注意", "注意到", "看到", "听到", "收到",
    "得到", "拿到", "找到", "遇到", "碰到", "见到", "看见", "听见",
    "遇见", "碰见", "学会", "学到", "懂得", "记得", "忘记", "忘了",
    "想起", "记起", "提到", "说到", "谈到", "讲到", "涉及", "有关", "属于", "成为", "变成", "作为", "当作", "看作", "视为",
}

# Combined stopwords
ALL_STOPWORDS = ENGLISH_STOPWORDS | CHINESE_STOPWORDS


# =============================================================================
# Fuzzy Matching
# =============================================================================

def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings.
    This is the minimum number of single-character edits needed
    to change one string into the other.
    """
    if len(s1) < len(s2):
        s1, s2 = s2, s1

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost is 0 if characters are same, 1 otherwise
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def fuzzy_match_score(query: str, text: str, threshold: float = 0.7) -> float:
    """
    Calculate fuzzy match score between query and text.
    Returns a score between 0 and 1, where 1 is exact match.

    Args:
        query: The search query
        text: The text to match against
        threshold: Minimum similarity threshold (0-1)

    Returns:
        Similarity score (0-1), or 0 if below threshold
    """
    if not query or not text:
        return 0.0

    query_lower = query.lower()
    text_lower = text.lower()

    # Exact match
    if query_lower == text_lower:
        return 1.0

    # Substring match
    if query_lower in text_lower:
        return 0.9

    # Calculate Levenshtein-based similarity
    max_len = max(len(query_lower), len(text_lower))
    if max_len == 0:
        return 0.0

    distance = levenshtein_distance(query_lower, text_lower)
    similarity = 1 - (distance / max_len)

    return similarity if similarity >= threshold else 0.0


def find_fuzzy_matches(
    keyword: str,
    text: str,
    threshold: float = 0.7,
    max_word_len_diff: int = 3
) -> list[tuple[str, float]]:
    """
    Find fuzzy matches for a keyword in text.

    Args:
        keyword: The keyword to search for
        text: The text to search in
        threshold: Minimum similarity threshold
        max_word_len_diff: Maximum length difference to consider

    Returns:
        List of (matched_word, score) tuples
    """
    if not keyword or not text:
        return []

    matches = []
    keyword_lower = keyword.lower()
    keyword_len = len(keyword_lower)

    # Split text into words
    words = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text)

    for word in words:
        word_lower = word.lower()
        word_len = len(word_lower)

        # Skip if length difference is too large
        if abs(word_len - keyword_len) > max_word_len_diff:
            continue

        score = fuzzy_match_score(keyword_lower, word_lower, threshold)
        if score > 0:
            matches.append((word, score))

    # Sort by score descending
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


# =============================================================================
# Smart Cube Detection
# =============================================================================

def detect_cube_from_path(project_path: str | None = None) -> str:
    """
    Detect the appropriate cube ID from the project path.

    The cube ID is derived from the project folder name:
    - Extract the folder name
    - Convert to lowercase
    - Replace -, ., space with _
    - Append '_cube'

    Examples:
        /mnt/g/test/MemOS -> memos_cube
        ~/my-app -> my_app_cube
        C:\\Projects\\MyProject -> myproject_cube

    Args:
        project_path: The project directory path. If None, uses CWD.

    Returns:
        The derived cube ID
    """
    if not project_path:
        project_path = os.getcwd()

    # Normalize path - handle both Windows and Unix paths
    # Replace backslashes with forward slashes for consistency
    normalized_path = project_path.replace("\\", "/")
    path = Path(normalized_path).resolve()

    # Get the folder name
    folder_name = path.name

    # Normalize: lowercase, replace special chars with underscore
    cube_id = folder_name.lower()
    cube_id = re.sub(r"[-.\s]+", "_", cube_id)
    cube_id = re.sub(r"[^a-z0-9_]", "", cube_id)

    # Ensure it doesn't start with a number
    if cube_id and cube_id[0].isdigit():
        cube_id = "_" + cube_id

    # Append _cube suffix if not already present
    if not cube_id.endswith("_cube"):
        cube_id = cube_id + "_cube"

    return cube_id or "default_cube"


def get_project_keywords(project_path: str | None = None) -> list[str]:
    """
    Extract potential keywords from project structure.

    Scans common configuration files and extracts project-related keywords
    that might help with cube identification.

    Args:
        project_path: The project directory path

    Returns:
        List of extracted keywords
    """
    if not project_path:
        project_path = os.getcwd()

    path = Path(project_path)
    keywords = []

    # Check package.json
    pkg_json = path / "package.json"
    if pkg_json.exists():
        try:
            import json
            with open(pkg_json, encoding="utf-8") as f:
                data = json.load(f)
                if "name" in data:
                    keywords.append(data["name"])
                if "keywords" in data:
                    keywords.extend(data["keywords"])
        except (OSError, json.JSONDecodeError):
            pass

    # Check pyproject.toml
    pyproject = path / "pyproject.toml"
    if pyproject.exists():
        try:
            with open(pyproject, encoding="utf-8") as f:
                content = f.read()
                # Simple extraction of project name
                match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    keywords.append(match.group(1))
        except OSError:
            pass

    # Check setup.py
    setup_py = path / "setup.py"
    if setup_py.exists():
        try:
            with open(setup_py, encoding="utf-8") as f:
                content = f.read()
                match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    keywords.append(match.group(1))
        except OSError:
            pass

    # Add folder name
    keywords.append(path.name)

    # Deduplicate and clean
    seen = set()
    result = []
    for kw in keywords:
        kw_clean = kw.strip().lower()
        if kw_clean and kw_clean not in seen:
            result.append(kw_clean)
            seen.add(kw_clean)

    return result


# =============================================================================
# Enhanced Keyword Extraction and Scoring
# =============================================================================

def extract_keywords_enhanced(
    query: str,
    stopwords: set[str] | None = None,
    min_length: int = 2
) -> list[str]:
    """
    Extract keywords from query with enhanced stopword filtering.

    Args:
        query: The search query
        stopwords: Custom stopword set (uses ALL_STOPWORDS if None)
        min_length: Minimum keyword length

    Returns:
        List of extracted keywords
    """
    if not query:
        return []

    if stopwords is None:
        stopwords = ALL_STOPWORDS

    # Tokenize: English words, numbers with underscores, Chinese characters
    raw_tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", query)

    keywords = []
    seen = set()

    for token in raw_tokens:
        if not token:
            continue

        # Chinese token
        if re.search(r"[\u4e00-\u9fff]", token):
            if len(token) < min_length:
                continue
            if token in stopwords:
                continue
            if token not in seen:
                keywords.append(token)
                seen.add(token)
            continue

        # English token
        lowered = token.lower()
        if len(lowered) < min_length:
            continue
        if lowered in stopwords:
            continue
        if lowered not in seen:
            keywords.append(lowered)
            seen.add(lowered)

    return keywords


def keyword_match_score_enhanced(
    text: str,
    keywords: list[str],
    metadata: dict | None = None,
    enable_fuzzy: bool = True,
    fuzzy_threshold: float = 0.75
) -> float:
    """
    Calculate enhanced keyword match score with structured field weighting
    and optional fuzzy matching.

    Args:
        text: The text to match against
        keywords: List of keywords to match
        metadata: Optional metadata dict with 'key' and 'tags' fields
        enable_fuzzy: Enable fuzzy matching
        fuzzy_threshold: Minimum similarity for fuzzy matches

    Returns:
        Total match score
    """
    if not text or not keywords:
        return 0.0

    text_lower = text.lower()
    score = 0.0
    matched_count = 0

    # Extract metadata fields
    key_field = ""
    tags = []
    if metadata:
        key_field = str(metadata.get("key", "")).lower()
        raw_tags = metadata.get("tags", [])
        if isinstance(raw_tags, list):
            tags = [str(t).lower() for t in raw_tags]

    for kw in keywords:
        kw_lower = kw.lower()
        is_chinese = bool(re.search(r"[\u4e00-\u9fff]", kw))
        kw_matched = False

        # 1. Key field match (highest weight)
        if key_field:
            if kw_lower in key_field or (is_chinese and kw in key_field):
                score += 5.0
                kw_matched = True

        # 2. Tags match (high weight)
        for tag in tags:
            if kw_lower in tag or (is_chinese and kw in tag):
                score += 3.0
                kw_matched = True
                break

        # 3. Text exact match
        if is_chinese:
            if kw in text:
                score += 2.0
                kw_matched = True
        else:
            # Word boundary match
            if re.search(rf"\b{re.escape(kw_lower)}\b", text_lower):
                score += 2.5
                kw_matched = True
            elif kw_lower in text_lower:
                # Substring match
                score += 1.5
                kw_matched = True

        # 4. Fuzzy match (if enabled and no exact match)
        if enable_fuzzy and not kw_matched and not is_chinese:
            fuzzy_matches = find_fuzzy_matches(
                kw_lower, text_lower, fuzzy_threshold
            )
            if fuzzy_matches:
                best_match_score = fuzzy_matches[0][1]
                score += best_match_score * 1.0  # Weighted fuzzy score
                kw_matched = True

        if kw_matched:
            matched_count += 1

    # Bonus for matching multiple keywords
    if matched_count > 0 and len(keywords) > 0:
        coverage = matched_count / len(keywords)
        score += coverage * 1.5

    return score


# =============================================================================
# Utility Functions
# =============================================================================

def get_stopwords() -> set[str]:
    """Get the complete set of stopwords."""
    return ALL_STOPWORDS.copy()


def is_stopword(word: str, include_programming: bool = True) -> bool:
    """
    Check if a word is a stopword.

    Args:
        word: The word to check
        include_programming: Whether to include programming stopwords

    Returns:
        True if the word is a stopword
    """
    if include_programming:
        return word.lower() in ALL_STOPWORDS
    else:
        return word.lower() in CHINESE_STOPWORDS or word.lower() in {
            "the", "and", "or", "a", "an", "to", "of", "for", "with", "in",
            "on", "at", "is", "are", "was", "were", "be", "this", "that",
            "it", "as", "from", "by", "about", "into", "over", "after",
            "before", "not", "but", "if", "then", "else", "when", "where",
        }
