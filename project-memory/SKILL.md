---
name: project-memory
description: "Proactive project memory management via MemOS MCP. **智能项目感知 (Smart Project Awareness)**: 当你进入一个新项目或目录时，MemOS 会自动为你创建隔离的记忆空间。你必须根据当前项目路径自动推导 `cube_id`。
**推导规则**: 提取项目文件夹名称 -> 转小写 -> 将 `-`, `.`, 空格替换为 `_` -> 后缀加上 `_cube`。
示例: `/mnt/g/test/AudioCraft` -> `audiocraft_cube`, `~/projects/my-app` -> `my_app_cube`。
**核心意识**: 你拥有持久化记忆能力。你应该像一个长期合作伙伴一样，通过 MemOS 记录和检索：
1. **项目进度 (Milestones)**: 任务完成后的阶段性总结。
2. **技术架构 (Architecture/Decisions)**: 为什么选择某个库，架构设计思路。
3. **实现细节 (Details/Code Patterns)**: 核心算法逻辑，复杂的正则，复用代码段。
4. **异常排查 (Bugfixes/Patterns)**: 遇到的坑 (Gotchas) 及其解决方案。
**强制触发场景**:
- 查找/找寻/搜索/find/search/记得吗/之前/上次 -> **必须先**调用 `memos_search`。
- 知识图谱/关系/KG/dependency/因果 -> **必须**调用 `memos_get_graph` 梳理逻辑。
- 开始工作 -> 调用 `memos_search` 获取上下文。
- 修复 Bug/完成任务/做出决策/发现陷阱 -> **必须实时**调用 `memos_save` 记录记忆。"
---

# Project Memory (MCP Powered)

Intelligent project memory system powered by **MemOS MCP Server**. Use MCP tools directly - no scripts needed!

---

## 🔒 Auto Project Isolation (IMPORTANT!)

**Every project gets its own isolated memory cube automatically.**

### Cube ID Derivation Rule

```
Project Path → cube_id
─────────────────────────────────────────────────────
/mnt/g/test/MemOS        → memos_cube
/home/user/my-awesome-app → my_awesome_app_cube
~/projects/WebApp.v2      → webapp_v2_cube
C:\Users\dev\todo-list    → todo_list_cube
```

**Algorithm:**
1. Extract project folder name from working directory
2. Convert to lowercase
3. Replace `-`, `.`, spaces with `_`
4. Append `_cube`

### Usage

**ALWAYS pass the derived `cube_id` to ALL memos_* tools:**

```python
# Working in /mnt/g/test/MemOS
memos_search(query="error", cube_id="memos_cube")
memos_save(content="...", cube_id="memos_cube")

# Working in ~/projects/my-app
memos_search(query="config", cube_id="my_app_cube")
```

---

## Quick Reference: MCP Tools

| Tool | When to Use | Example |
|------|-------------|---------|
| `memos_search` | Find related memories, solutions, patterns | `query: "ERROR_PATTERN xxx", cube_id: "{project}_cube"` |
| `memos_save` | Record important information | `content: "Fixed X by Y", memory_type: "BUGFIX", cube_id: "{project}_cube"` |
| `memos_list` | See all memories in project | `cube_id: "{project}_cube", limit: 10` |
| `memos_list_v2` | List with improved formatting | `cube_id: "{project}_cube"` |
| `memos_suggest` | Get search suggestions | `context: "Connection refused error"` |
| `memos_get_graph` | **知识图谱 - View CAUSE/RELATE/CONFLICT** | `query: "Neo4j", cube_id: "{project}_cube"` |
| `memos_get_stats` | Memory statistics by type | `cube_id: "{project}_cube"` |
| `memos_delete` | ⚠️ Delete memories (use with caution) | `memory_id: "uuid", cube_id: "{project}_cube"` |

---

## Proactive Triggers (Use MCP Automatically!)

### When to Search (`memos_search`)

**IMPORTANT: When the user uses ANY of these keywords, you MUST proactively call `memos_search` to check the memory database BEFORE responding.**

| User Says / Context | Search Query |
|---------------------|--------------|
| "找", "找一下", "找找", "找寻", "查找", "搜索", "搜一下" | `{topic}` - search for the mentioned topic |
| "find", "search", "look up", "look for", "check if" | `{topic}` - search for the mentioned topic |
| "有没有", "是否有", "有记录吗", "记得吗" | `{topic}` - check if memory exists |
| "之前", "上次", "以前", "previously", "last time" | `{topic} history` |
| "为什么", "why did we", "当时为什么" | `DECISION {topic}` |
| "怎么解决", "how to fix", "怎么修", error message | `ERROR_PATTERN {error_type}` |
| "类似", "similar", "像...一样" | `CODE_PATTERN {pattern}` |
| "什么时候", "when did", "哪次" | `{topic}` - search timeline |
| "谁", "who", "哪个项目" | `{topic}` - search context |
| Working with config file | `CONFIG {filename}` |
| Opening file for editing | `{filename} gotcha` |
| "RAG", "rag", "检索增强", "retrieval" | `{topic}` - search with RAG context |
| "向量", "vector", "embedding", "嵌入" | `{topic}` - semantic vector search |
| "语义搜索", "semantic search", "智能搜索" | `{topic}` - meaning-based search |

### When to Get Graph (`memos_get_graph`) - Knowledge Graph & Dependencies

**IMPORTANT: When the user mentions knowledge graph, dependencies, or causal relationships, you MUST call `memos_get_graph` to retrieve relationship data.**

| User Says / Context | Query | Returns |
|---------------------|-------|---------|
| "知识图谱", "knowledge graph", "KG" | `{topic}` | Full knowledge graph for topic |
| "依赖关系", "dependency", "dependencies", "依赖" | `{component}` | CAUSE/RELATE relationships |
| "关系图", "relationship graph", "关联图" | `{topic}` | Visual relationship mapping |
| "为什么失败", "why failed", "root cause", "根因" | `{error/feature}` | Causal chain (A→B→C) |
| "相关的", "related to", "关联", "有关系" | `{topic}` | RELATE relationships |
| "冲突", "conflict", "矛盾", "冲突检测" | `{topic}` | CONFLICT relationships |
| "影响", "impact", "会影响什么", "影响范围" | `{change}` | What depends on this |
| "因果", "cause", "causation", "因果链" | `{topic}` | CAUSE chain analysis |
| "上下游", "upstream", "downstream" | `{component}` | Dependency flow |
| Debugging complex issues | `{error_keyword}` | Full context graph |

**Example Output:**
```
[Neo4j需要Java 17+]
    ──CAUSE──>
[Neo4j启动失败, JAVA_HOME not set]
```

### When to Save (`memos_save`)

| Scenario | Memory Type | Content Should Include |
|----------|-------------|------------------------|
| Bug fixed | `ERROR_PATTERN` | Error signature, cause, solution, prevention |
| Feature done | `FEATURE` | What was added, how to use |
| Task completed | `MILESTONE` | Summary of achievement |
| Made a choice | `DECISION` | Options considered, rationale, impact |
| Found a trap | `GOTCHA` | Issue, context, workaround |
| Changed config | `CONFIG` | What changed, why, how to revert |
| Code template | `CODE_PATTERN` | Template, usage, parameters |

---

## Memory Type Formats

### [ERROR_PATTERN] - For Solved Errors

```markdown
[ERROR_PATTERN] Error: {ErrorType}

## Signature
- Type: {ErrorType}
- Message: {Full error message}
- Context: {When this occurs}

## Root Cause
{Why this error happens}

## Solution
1. {Step 1}
2. {Step 2}

## Prevention
{How to avoid in future}

Tags: error, {error_type}, {category}
```

### [DECISION] - For Choices Made

```markdown
[DECISION] Topic: {topic}

## Decision
{What was decided}

## Options Considered
1. **{Option A}**: {pros/cons}
2. **{Option B}** (chosen): {pros/cons}

## Rationale
{Why this option was chosen}

## Impact
- Files affected: {list}
- Dependencies: {list}

Tags: decision, {topic}
```

### [CODE_PATTERN] - For Reusable Code

```markdown
[CODE_PATTERN] Pattern: {name}

## Purpose
{What this pattern does}

## Template
```{language}
{code template}
```

## Usage
{When and how to use}

Tags: pattern, {language}, {category}
```

### [MILESTONE] - For Achievements

```markdown
[MILESTONE] {short description}

## Summary
{What was accomplished}

## Details
- {detail 1}
- {detail 2}

Tags: milestone, {category}
```

### [GOTCHA] - For Traps and Workarounds

```markdown
[GOTCHA] {short description}

## Issue
{The non-obvious problem}

## Context
{When/where this occurs}

## Workaround
{How to avoid or fix}

Tags: gotcha, {category}
```

---

## Workflow with MCP

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROJECT MEMORY WORKFLOW (MCP)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ⚡ FIRST: Derive cube_id from project path!                    │
│     /mnt/g/test/MemOS → cube_id = "memos_cube"                 │
│                                                                 │
│  TRIGGER              MCP TOOL              ACTION              │
│  ───────              ────────              ──────              │
│                                                                 │
│  Start working   ───> memos_search    ───> Get project context  │
│                       cube_id: "{project}_cube"                 │
│                                                                 │
│  Hit error       ───> memos_search    ───> Find ERROR_PATTERN   │
│                       query: "ERROR_PATTERN {type}"             │
│                       cube_id: "{project}_cube"                 │
│                                                                 │
│  Need root cause ───> memos_get_graph ───> View CAUSE chain     │
│                       query: "{error_keyword}"                  │
│                       cube_id: "{project}_cube"                 │
│                                                                 │
│  Check deps      ───> memos_get_graph ───> View relationships   │
│  "依赖关系"            query: "{component}"                      │
│  "dependency"          cube_id: "{project}_cube"                │
│                                                                 │
│  知识图谱/KG     ───> memos_get_graph ───> Full knowledge graph  │
│  knowledge graph       query: "{topic}"                         │
│                       cube_id: "{project}_cube"                 │
│                                                                 │
│  Solved error    ───> memos_save      ───> Save ERROR_PATTERN   │
│                       memory_type: "ERROR_PATTERN"              │
│                       cube_id: "{project}_cube"                 │
│                                                                 │
│  Make decision   ───> memos_save      ───> Save DECISION        │
│                       memory_type: "DECISION"                   │
│                       cube_id: "{project}_cube"                 │
│                                                                 │
│  Complete task   ───> memos_save      ───> Save MILESTONE       │
│                       memory_type: "MILESTONE"                  │
│                       cube_id: "{project}_cube"                 │
│                                                                 │
│  "之前/上次"     ───> memos_search    ───> Find history         │
│                       cube_id: "{project}_cube"                 │
│                                                                 │
│  "找/查找/搜索"  ───> memos_search    ───> Search memory DB     │
│  "find/search"                                                  │
│                                                                 │
│  RAG/rag/检索    ───> memos_search    ───> RAG-enhanced search  │
│  向量/语义搜索         query: "{topic}"                         │
│                                                                 │
│  Unsure search   ───> memos_suggest   ───> Get suggestions      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Best Practices

1. **Search Before Save** - Check if similar memory exists
2. **Be Specific** - Include file paths, function names, error messages
3. **Include Why** - Don't just record what, explain the reasoning
4. **Tag Consistently** - Use standard tags for searchability
5. **Save Immediately** - Record while context is fresh
6. **Robust Prompting** - ALWAYS use `.replace("{var}", val)` instead of `.format()` for prompt templates to avoid `KeyError` with content containing `{}`.
7. **Robust JSON Parsing** - ALWAYS use `parse_json_result(text)` for LLM outputs. It handles markdown, lists, and auto-fixes truncated JSON via stack-based logic.
8. **F-String Limit** - Avoid backslashes `\` in f-string expressions (e.g., `f"{'\n'.join(list)}"` is invalid). Use intermediate variables.

---

## Core Coding Patterns (CODE_PATTERN)

### 1. Robust Prompt Substitution
```python
# GOOD: Use replace to avoid KeyError
user_prompt = PROMPT_TEMPLATE.replace("{query}", query).replace("{context}", context)

# BAD: May cause KeyError if query/context contains { or }
# user_prompt = PROMPT_TEMPLATE.format(query=query, context=context)
```

### 2. Standardized JSON Parsing
```python
from memos.mem_reader.read_multi_modal.utils import parse_json_result

# Parse LLM response safely
result_dict = parse_json_result(llm_response)
```

---

## Common Traps (GOTCHA)

### 1. F-String Backslash SyntaxError
**Issue:** Python f-strings cannot contain backslashes `\` inside the expression part (the `{}` part).
**Context:** Common when using `'\n'.join()` or regex inside an f-string.
**Workaround:** Assign the expression to an intermediate variable first.
```python
# BAD
# dialogue = f"————{'\n————'.join(history)}"  # SyntaxError

# GOOD
dialogue_content = '\n————'.join(history)
dialogue = f"————{dialogue_content}"
```

### 2. Prompt Template KeyError
**Issue:** Using `.format()` on templates containing JSON or code blocks.
**Context:** Prompt templates often contain `{}` for JSON schemas.
**Workaround:** Use `.replace("{placeholder}", value)`.

---

## Legacy Scripts (Optional)

> **Note**: With MCP, you rarely need these scripts. They're kept for backward compatibility.

The following scripts in `scripts/` folder still work but MCP is preferred:

| Script | MCP Equivalent |
|--------|----------------|
| `memos_init_project.py` | Auto-registered by MCP |
| `memos_save.py` | `memos_save` tool |
| `memos_search.py` | `memos_search` tool |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API URL |
| `MEMOS_USER` | `dev_user` | User ID |
| `MEMOS_DEFAULT_CUBE` | `dev_cube` | Fallback cube (used only if auto-derivation fails) |
| `MEMOS_CUBES_DIR` | `G:/test/MemOS/data/memos_cubes` | Cube storage (for auto-registration) |

> **Note**: With Auto Project Isolation, `MEMOS_DEFAULT_CUBE` is rarely used. The AI automatically derives `cube_id` from the project path.

---

## Troubleshooting

### MCP Tool Returns Error

1. **Check MemOS API is running**: `curl http://localhost:18000/users`
2. **Check MCP connection**: In Claude Code, run `/mcp` to see server status
3. **Restart Claude Code** if MCP shows as disconnected

### Memory Not Found

1. Use `memos_list` to see what's in the cube
2. Try broader search terms
3. Check if searching correct `cube_id`

### Save Failed

1. Check API is running
2. MCP auto-registers cubes, but verify with `memos_list`
3. Check error message for details
