---
name: project-memory
description: "Proactive project memory management via MemOS MCP. USE MCP TOOLS AUTOMATICALLY when: (1) Starting work - memos_search for context, (2) Completing tasks - memos_save as MILESTONE, (3) Fixing bugs - memos_save as ERROR_PATTERN, (4) Making decisions - memos_save as DECISION, (5) Encountering errors - memos_search for solutions, (6) User mentions '之前/上次/previously' - memos_search history. Available MCP tools: memos_search, memos_save, memos_list, memos_suggest."
---

# Project Memory (MCP Powered)

Intelligent project memory system powered by **MemOS MCP Server**. Use MCP tools directly - no scripts needed!

---

## Quick Reference: MCP Tools

| Tool | When to Use | Example |
|------|-------------|---------|
| `memos_search` | Find related memories, solutions, patterns | `query: "ERROR_PATTERN ModuleNotFoundError"` |
| `memos_save` | Record important information | `content: "Fixed X by Y", memory_type: "BUGFIX"` |
| `memos_list` | See all memories in project | `cube_id: "dev_cube", limit: 10` |
| `memos_suggest` | Get search suggestions | `context: "Connection refused error"` |

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
