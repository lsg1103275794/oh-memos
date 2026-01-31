---
name: project-memory
description: "Proactive project memory management via MemOS MCP. USE MCP TOOLS AUTOMATICALLY when: (1) Starting work - memos_search for context, (2) Completing tasks - memos_save as MILESTONE, (3) Fixing bugs - memos_save as ERROR_PATTERN, (4) Making decisions - memos_save as DECISION, (5) Encountering errors - memos_search for solutions, (6) User mentions '之前/上次/previously' - memos_search history, (7) Need to understand dependencies/causality - memos_get_graph or memos_trace_path for relationships, (8) Cube not found - memos_list_cubes to discover available cubes. Available MCP tools: memos_search, memos_search_context, memos_save, memos_list, memos_suggest, memos_list_cubes, memos_get_graph, memos_trace_path, memos_export_schema."
---

# Project Memory (MCP Powered)

Intelligent project memory system powered by **MemOS MCP Server**. Use MCP tools directly - no scripts needed!

---

## Quick Reference: MCP Tools

| Tool | When to Use | Example |
|------|-------------|---------|
| `memos_search` | Find related memories, solutions, patterns | `query: "ERROR_PATTERN ModuleNotFoundError"` |
| `memos_search_context` | **Smart search with conversation context** | `query: "what was the solution?"` |
| `memos_save` | Record important information | `content: "Fixed X by Y", memory_type: "BUGFIX"` |
| `memos_list` | See all memories in project | `cube_id: "dev_cube", limit: 10` |
| `memos_list_cubes` | **Discover available cubes** | `include_status: true` |
| `memos_suggest` | Get search suggestions | `context: "Connection refused error"` |
| `memos_get_graph` | View dependency/causal relationships | `query: "Neo4j"` → shows CAUSE/RELATE/CONFLICT |
| `memos_trace_path` | **Trace paths between memories** | `source_id: "...", target_id: "..."` |
| `memos_export_schema` | **View graph structure and health** | Shows node/edge counts, types, connectivity |

---

## Proactive Triggers (Use MCP Automatically!)

### When to Search (`memos_search`)

| User Says / Context | Search Query |
|---------------------|--------------|
| "之前", "上次", "previously" | `{topic} history` |
| "为什么", "why did we" | `DECISION {topic}` |
| "怎么解决", "how to fix", error message | `ERROR_PATTERN {error_type}` |
| "类似", "similar" | `CODE_PATTERN {pattern}` |
| Working with config file | `CONFIG {filename}` |
| Opening file for editing | `{filename} gotcha` |

### When to Get Graph (`memos_get_graph`) - NEW!

| User Says / Context | Query | Returns |
|---------------------|-------|---------|
| "依赖关系", "dependencies" | `{component}` | CAUSE/RELATE relationships |
| "为什么失败", "why failed", "root cause" | `{error/feature}` | Causal chain (A→B→C) |
| "相关的", "related to", "关联" | `{topic}` | RELATE relationships |
| "冲突", "conflict", "矛盾" | `{topic}` | CONFLICT relationships |
| "影响", "impact", "会影响什么" | `{change}` | What depends on this |
| Debugging complex issues | `{error_keyword}` | Full context graph |

**Example Output:**
```
[Neo4j需要Java 17+]
    ──CAUSE──>
[Neo4j启动失败, JAVA_HOME not set]
```

### When to Trace Path (`memos_trace_path`) - NEW!

| Scenario | Use Case |
|----------|----------|
| 追溯根因 | `source_id: "症状ID", target_id: "根因ID"` → 显示完整因果链 |
| 理解影响 | 从决策A到结果B的路径 |
| 调试复杂问题 | 找到错误之间的关联 |

**Example:**
```
memos_trace_path(source_id="uuid1", target_id="uuid2", max_depth=5)
→ [决策A] ──CAUSE──> [变更B] ──CAUSE──> [问题C]
```

### When to List Cubes (`memos_list_cubes`) - NEW!

| Scenario | Action |
|----------|--------|
| 遇到 "cube not found" 错误 | `memos_list_cubes()` 查看可用 cubes |
| 切换项目 | `memos_list_cubes(include_status=true)` 查看注册状态 |
| 初始化项目 | 确认 cube 是否存在 |

### When to Export Schema (`memos_export_schema`) - NEW!

| Scenario | What You Get |
|----------|--------------|
| 理解知识库结构 | 节点/边总数, 类型分布 |
| 检查健康状态 | 孤立节点数, 连接度 |
| 查看常用标签 | Top 20 tags |

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
│  TRIGGER              MCP TOOL              ACTION              │
│  ───────              ────────              ──────              │
│                                                                 │
│  Start working   ───> memos_search    ───> Get project context  │
│                                                                 │
│  Hit error       ───> memos_search    ───> Find ERROR_PATTERN   │
│                       query: "ERROR_PATTERN {type}"             │
│                                                                 │
│  Need context    ───> memos_search_context ─> Smart search      │
│                       with conversation history                 │
│                                                                 │
│  Need root cause ───> memos_get_graph ───> View CAUSE chain     │
│                       query: "{error_keyword}"                  │
│                                                                 │
│  Trace path      ───> memos_trace_path ──> A→B→C chain          │
│                       source_id, target_id                      │
│                                                                 │
│  Check deps      ───> memos_get_graph ───> View relationships   │
│                       query: "{component}"                      │
│                                                                 │
│  Cube not found  ───> memos_list_cubes ──> Discover cubes       │
│                       include_status: true                      │
│                                                                 │
│  Graph health    ───> memos_export_schema > Stats & structure   │
│                                                                 │
│  Solved error    ───> memos_save      ───> Save ERROR_PATTERN   │
│                       memory_type: "ERROR_PATTERN"              │
│                                                                 │
│  Make decision   ───> memos_save      ───> Save DECISION        │
│                       memory_type: "DECISION"                   │
│                                                                 │
│  Complete task   ───> memos_save      ───> Save MILESTONE       │
│                       memory_type: "MILESTONE"                  │
│                                                                 │
│  "之前/上次"     ───> memos_search    ───> Find history         │
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
| `MEMOS_DEFAULT_CUBE` | `dev_cube` | Default memory cube |
| `MEMOS_CUBES_DIR` | `G:/test/MemOS/data/memos_cubes` | Cube storage (for auto-registration) |

---

## Troubleshooting

### Cube Not Found Error

1. **Use `memos_list_cubes()` to see available cubes**
2. Check if the cube directory exists with `config.json`
3. Verify correct `cube_id` is being used
4. MCP will show available cubes in error message

### MCP Tool Returns Error

1. **Check MemOS API is running**: `curl http://localhost:18000/users`
2. **Check MCP connection**: In Claude Code, run `/mcp` to see server status
3. **Restart Claude Code** if MCP shows as disconnected

### Memory Not Found

1. Use `memos_list` to see what's in the cube
2. Try `memos_search_context` with conversation context for smarter search
3. Try broader search terms
4. Check if searching correct `cube_id`

### Save Failed

1. Check API is running
2. MCP auto-registers cubes, but verify with `memos_list_cubes`
3. Check error message for details
