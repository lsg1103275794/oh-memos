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

## 记忆系统 (核心规则)

**保存记忆时必须显式指定 `memory_type` 参数**，不依赖自动检测。

类型速查：
- Bug 修复 → `BUGFIX` 或 `ERROR_PATTERN`
- 技术决策 → `DECISION`
- 发现陷阱 → `GOTCHA`
- 完成里程碑 → `MILESTONE`
- 纯进度汇报 → `PROGRESS`

**详细操作规则、MCP 工具使用说明、决策树见 `/project-memory` skill**

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

---

## API Endpoints

### Graph API

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
