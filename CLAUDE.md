# MemOS Project Guide

> This file provides project-specific context to Claude Code.
保持中文交流
---

## Project Overview

**MemOS** is a persistent project memory solution for AI assistants, featuring:

- **MCP Server**: Proactive memory tools (memos_search, memos_save, memos_list, memos_suggest, memos_list_cubes)
- **Neo4j Knowledge Graph**: Structured memory with relationships (tree_text mode)
- **Qdrant Vector Database**: Semantic similarity search
- **LLM Memory Extraction**: Auto-extract key, tags, background, confidence
- **AI Graph Intelligence**: Path tracing, context-aware search, schema analysis
- **Smart Cube Management**: Auto-register cubes, path verification, helpful error messages

---

## 🚨 记忆类型分类规范 (MUST READ)

### 强制规则 (MUST/MUST NOT)

#### MUST (必须遵守)

1. **修复 Bug 后必须保存为 `BUGFIX` 或 `ERROR_PATTERN`**，不得使用 PROGRESS
2. **做出技术决策后必须保存为 `DECISION`**，包含理由和备选方案
3. **发现非显而易见的陷阱必须保存为 `GOTCHA`**
4. **保存时必须显式指定 `memory_type` 参数**，不依赖自动检测

#### MUST NOT (禁止)

1. **禁止将 PROGRESS 作为默认/万能类型**
2. **禁止省略 memory_type 参数** (除非是纯进度汇报)
3. **禁止在 PROGRESS 中包含错误解决方案、技术决策、陷阱警告**

### 类型选择决策树

```
是否解决了一个错误/Bug？
├─ 是 → 是否有通用价值？
│       ├─ 是 → ERROR_PATTERN (错误模式，可复用)
│       └─ 否 → BUGFIX (一次性修复)
└─ 否 → 是否做出了技术选择？
        ├─ 是 → DECISION
        └─ 否 → 是否发现了非显而易见的问题？
                ├─ 是 → GOTCHA
                └─ 否 → 是否是可复用的代码模板？
                        ├─ 是 → CODE_PATTERN
                        └─ 否 → 是否修改了配置？
                                ├─ 是 → CONFIG
                                └─ 否 → 是否完成了重大里程碑？
                                        ├─ 是 → MILESTONE
                                        └─ 否 → 是否新增了功能？
                                                ├─ 是 → FEATURE
                                                └─ 否 → PROGRESS (仅限纯进度)
```

### 错误示范 vs 正确示范

❌ **错误**: `memos_save(content="修复了模型路径问题")` → 默认 PROGRESS
✅ **正确**: `memos_save(content="修复了模型路径问题...", memory_type="BUGFIX")`

❌ **错误**: `memos_save(content="决定采用WebSocket方案")` → 可能被误检测
✅ **正确**: `memos_save(content="决定采用WebSocket方案...", memory_type="DECISION")`

❌ **错误**: `memos_save(content="注意: Neo4j需要Java 17+")` → 可能落入 PROGRESS
✅ **正确**: `memos_save(content="注意: Neo4j需要Java 17+...", memory_type="GOTCHA")`

### 置信度机制

`detect_memory_type()` 返回 `(类型, 置信度)` 元组：

| 置信度 | 含义 |
|--------|------|
| 1.0 | 显式指定类型 |
| 0.85-0.95 | 强特征匹配（如 traceback、决定采用） |
| 0.7-0.84 | 中等特征匹配 |
| 0.3 | 默认 PROGRESS（无特征匹配，会触发警告） |

**当置信度 < 0.6 且类型为 PROGRESS 时，系统会输出警告提示显式指定类型。**

### 健康检查

`memos_get_stats` 会在 PROGRESS 占比 >70% 时输出健康警告：

```
⚠️ 健康警告: PROGRESS 类型占比过高 (>70%)

这可能导致 Neo4j 知识图谱无法建立有效关系。建议:
1. 保存记忆时显式指定 memory_type 参数
2. 参考类型选择决策树
```

---

## Memory System (MCP) - IMPORTANT

### Proactive Trigger Rules

**MUST search memory (memos_search) when:**

| Trigger Keywords | Action | Example |
|------------------|--------|---------|
| 错误/error/exception/failed | Search ERROR_PATTERN | `memos_search("ERROR_PATTERN xxx")` |
| 之前/上次/previously/last time | Search history | `memos_search("xxx history")` |
| 注意/warning/watch out/careful | Search GOTCHA | `memos_search("GOTCHA xxx")` |
| 怎么做/how to/how did we | Search related patterns | `memos_search("xxx implementation")` |
| 配置/config/setup | Search CONFIG | `memos_search("CONFIG xxx")` |
| 决定/为什么/why did we/decision | Search DECISION | `memos_search("DECISION xxx")` |

**MUST save memory (memos_save) when:**

| Trigger Situation | Memory Type | Example |
|-------------------|-------------|---------|
| 修复了 Bug / Fixed bug | ERROR_PATTERN | `[ERROR_PATTERN] Issue: xxx, Solution: xxx` |
| 完成任务 / Task completed | MILESTONE | `[MILESTONE] Completed xxx feature` |
| 做出决策 / Made decision | DECISION | `[DECISION] Chose xxx because xxx` |
| 发现坑 / Found gotcha | GOTCHA | `[GOTCHA] Watch out: xxx when doing xxx` |
| 优化方案 / Optimization plan | DECISION | `[DECISION] Optimization: xxx approach` |
| 新功能 / New feature | FEATURE | `[FEATURE] Added xxx functionality` |
| 改配置 / Config change | CONFIG | `[CONFIG] Updated xxx to xxx` |
| 代码模式 / Code pattern | CODE_PATTERN | `[CODE_PATTERN] Template for xxx` |

### Memory Types Reference

| Type | When to Use |
|------|-------------|
| `ERROR_PATTERN` | Error encountered + solution found |
| `DECISION` | Architecture/design choice with rationale |
| `MILESTONE` | Significant project achievement |
| `BUGFIX` | Bug fix with root cause |
| `FEATURE` | New functionality added |
| `CONFIG` | Environment or configuration change |
| `CODE_PATTERN` | Reusable code template |
| `GOTCHA` | Non-obvious issue or workaround |
| `PROGRESS` | General progress update |

---

## Advanced AI Graph Tools

### Path Tracing (`memos_trace_path`)

Trace reasoning paths between two memory nodes to understand causality and connections.

**When to use:**
- Understanding how one issue led to another
- Finding the root cause chain of an error
- Exploring indirect relationships between concepts

**Example:**
```
memos_trace_path(
  source_id="<memory-id-1>",
  target_id="<memory-id-2>",
  max_depth=5
)
```

**Returns:** Path with nodes and relationship types (CAUSE, RELATE, CONFLICT, CONDITION)

### Context-Aware Search (`memos_search_context`)

Smart search that analyzes conversation context to understand intent.

**When to use:**
- Query is ambiguous (e.g., "what was the solution?")
- Need to find related concepts, not just exact matches
- Want better recall through automatic query expansion

**Example:**
```
memos_search_context(
  query="what was the solution?",
  context=[
    {"role": "user", "content": "I'm debugging the login module"},
    {"role": "assistant", "content": "Let me help with that."}
  ]
)
```

### Graph Schema Export (`memos_export_schema`)

Export knowledge graph structure and health statistics.

**When to use:**
- Understanding what kind of information has been stored
- Checking graph health (orphan nodes, connectivity)
- Reviewing relationship type distribution

**Returns:**
- Total nodes/edges
- Edge type distribution (CAUSE, RELATE, etc.)
- Memory type distribution
- Top tags
- Connectivity metrics
- Health assessment

### Graph Visualization (`memos_get_graph`)

Get memory relationships for a specific topic.

**When to use:**
- Visualizing how memories connect
- Understanding context around a topic
- Finding related information

### Cube Discovery (`memos_list_cubes`)

List all available memory cubes in the system.

**When to use:**
- Encountering "cube not found" errors
- User asks which cubes are available
- Verifying a cube exists before using it
- Starting a new project and want to see existing cubes

**Example:**
```
memos_list_cubes()
memos_list_cubes(include_status=True)  # Check registration status
```

**Returns:**
- List of available cube IDs with their paths
- Registration status for each cube (if requested)
- Helpful guidance if no cubes are found

---

## Auto-Registration & Auto-Creation

The MCP server now includes **smart cube management**:

1. **Auto-Creation**: New projects automatically get their own cube (cloned from `dev_cube` template)
2. **Automatic Registration**: Cubes are auto-registered on first use
3. **Path Verification**: Checks if cube directory exists before registration
4. **Helpful Error Messages**: If a cube is not found and cannot be created, shows available cubes
5. **Cube Discovery**: Use `memos_list_cubes` to see all available cubes

**How it works for new projects:**
```
User starts Claude Code in ~/projects/my-new-project/
        ↓
MCP derives cube_id: "my_new_project_cube"
        ↓
Cube not found? Auto-create from dev_cube template
        ↓
Auto-register with MemOS API
        ↓
Ready to use!
```

**Requirements:**
- `dev_cube` must exist as template in `MEMOS_CUBES_DIR`
- Cubes directory must be writable

If you see "Cube Registration Failed" error:
1. Use `memos_list_cubes()` to see available cubes
2. Verify `dev_cube` exists as template
3. Check cubes directory permissions

```bash
# Manual registration (fallback)
curl -X POST "http://localhost:18000/mem_cubes" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"dev_user","mem_cube_name_or_path":"G:/test/MemOS/data/memos_cubes/dev_cube"}'
```

---

## Project Configuration

### Memory Cube
- **Cube ID**: `dev_cube`
- **Storage Path**: `data/memos_cubes/dev_cube`
- **Full Path**: `G:/test/MemOS/data/memos_cubes/dev_cube`

### Memory Mode
- **Backend**: `tree_text` (Knowledge Graph)
- **Graph DB**: Neo4j Community Edition (localhost:7687)
- **Vector DB**: Qdrant Local (localhost:6333)

### Service Ports
| Service | Port | URL |
|---------|------|-----|
| MemOS API | 18000 | http://localhost:18000/docs |
| Qdrant | 6333 | http://localhost:6333/dashboard |
| Neo4j | 7474/7687 | http://localhost:7474 |
| Ollama | 11434 | http://localhost:11434 |

### MCP Server Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API base URL |
| `MEMOS_USER` | `dev_user` | Default user ID |
| `MEMOS_DEFAULT_CUBE` | `dev_cube` | Default memory cube ID |
| `NEO4J_HTTP_URL` | `http://localhost:7474/db/neo4j/tx/commit` | Neo4j HTTP endpoint |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `12345678` | Neo4j password |
| `MEMOS_ENABLE_DELETE` | `false` | Enable delete functionality |

---

## API Endpoints

### Graph API (New)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/product/graph/data` | POST | Export graph nodes and edges |
| `/product/graph/trace_path` | POST | Trace paths between two nodes |
| `/product/graph/schema` | POST | Export graph schema and statistics |
| `/product/search` | POST | Search with optional `enable_context_analysis` |

### Example: Trace Path API

```json
POST /product/graph/trace_path
{
  "user_id": "dev_user",
  "source_id": "<uuid>",
  "target_id": "<uuid>",
  "max_depth": 5,
  "include_all_paths": false
}
```

### Example: Context-Aware Search

```json
POST /product/search
{
  "user_id": "dev_user",
  "query": "what was the solution?",
  "readable_cube_ids": ["dev_cube"],
  "enable_context_analysis": true,
  "chat_history": [
    {"role": "user", "content": "I'm debugging login errors"}
  ]
}
```

---

## Key Files

| File | Purpose |
|------|---------|
| `scripts/local/start.bat` | One-click silent launcher |
| `.env` | Environment configuration |
| `mcp-server/memos_mcp_server.py` | MCP server implementation |
| `data/memos_cubes/dev_cube/config.json` | Cube configuration |

---

## Quick Start

```bash
# Start all services (silent databases + API)
scripts/local/start.bat

# Stop databases
scripts/local/stop_db_silent.bat
```

---

*This file is read by Claude Code at conversation start to provide project context.*
