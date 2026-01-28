# MemOS Project Guide

> This file provides project-specific context to Claude Code.

---

## Project Overview

**MemOS** is a persistent project memory solution for AI assistants, featuring:

- **MCP Server**: Proactive memory tools (memos_search, memos_save, memos_list, memos_suggest)
- **Neo4j Knowledge Graph**: Structured memory with relationships (tree_text mode)
- **Qdrant Vector Database**: Semantic similarity search
- **LLM Memory Extraction**: Auto-extract key, tags, background, confidence
- **AI Graph Intelligence**: Path tracing, context-aware search, schema analysis

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

---

## Auto-Registration

The MCP server auto-registers the default cube on startup. If you see "MemCube not loaded" error:

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
