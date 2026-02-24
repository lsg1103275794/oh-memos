# MemOS Project Guide

> This file provides project-specific context to Claude Code.
保持中文交流

---

## Critical: Memory Operations via MCP Only

**禁止手动创建 memory 目录或文件。** 所有记忆操作必须通过 MCP memos 工具完成。

如果你想运行 `mkdir -p .../memory` 或用 `Write` 创建记忆文件 — **停下来**，改用 MCP memos 工具。

### Tools Available:
`memos_context_resume`, `memos_search`, `memos_save`, `memos_list_v2`, `memos_suggest`, `memos_get_stats`, `memos_get_graph`, `memos_trace_path`, `memos_export_schema`, `memos_list_cubes`, `memos_register_cube`

### Cube Routing (CRITICAL)

每个项目有自己的 memory cube。**必须传 `project_path` 参数**，让 MCP server 自动推导 cube_id。

推导规则: 取目录名 → 小写 → 替换 `-`/`.`/空格为 `_` → 追加 `_cube`

示例:
| 项目路径 | 自动推导 cube_id |
|---------|----------------|
| `/mnt/g/test/MemOS` | `memos_cube` |
| `/mnt/g/Cyber/AudioCraft Studio` | `audiocraft_studio_cube` |
| `~/projects/my-web-app` | `my_web_app_cube` |

```python
# 正确用法
memos_save(content="...", memory_type="BUGFIX", project_path="/mnt/g/test/MemOS")
memos_search(query="...", project_path="/mnt/g/test/MemOS")

# 错误用法 — 不要硬编码 dev_cube
memos_save(content="...", cube_id="dev_cube")  # ❌
```

### Operational Workflow:
1. **Before Coding (Context Retrieval)**:
    - 在回答任何复杂问题或开始新功能前，**必须**使用 `memos_search` 或 `memos_list_v2` 检索项目记忆。
    - 上下文压缩后，调用 `memos_context_resume` 恢复上下文。

2. **During Development (Dependency & Logic)**:
    - 识别当前项目的技术栈版本。
    - 如果发现现有记忆与当前代码冲突，使用 `memos_get_graph` 梳理关系。

3. **After Coding (Knowledge Consolidation)**:
    - 完成功能模块、修复Bug或达成技术决策后，**必须**使用 `memos_save` 将关键信息写入记忆。
    - **必须显式指定 `memory_type` 参数**，不依赖自动检测。

### Memory Type 速查：
- Bug 修复 → `BUGFIX` 或 `ERROR_PATTERN`
- 技术决策 → `DECISION`
- 发现陷阱 → `GOTCHA`
- 代码模板 → `CODE_PATTERN`
- 配置变更 → `CONFIG`
- 完成里程碑 → `MILESTONE`
- 新增功能 → `FEATURE`
- 纯进度汇报 → `PROGRESS`

**详细操作规则、MCP 工具使用说明、决策树见 `/project-memory` skill**

---

## Project Overview

**MemOS** is a persistent project memory solution for AI assistants, featuring:

- **MCP Server**: Proactive memory tools with project_path-based cube routing
- **Neo4j Knowledge Graph**: Structured memory with relationships (tree_text mode)
- **Qdrant Vector Database**: Semantic similarity search
- **LLM Memory Extraction**: Auto-extract key, tags, background, confidence
- **AI Graph Intelligence**: Path tracing, context-aware search, schema analysis
- **Smart Cube Management**: Auto-create, auto-register cubes from project path
- **Hooks System**: Session start, pre-compact, post-tool reminders (see `project-memory/hooks/`)

---

## Project Configuration

### Memory Cube (for MemOS development itself)
- **Cube ID**: `memos_cube` (auto-derived from project path)
- **Storage Path**: `data/memos_cubes/dev_cube`
- **Usage**: `memos_save(..., project_path="/mnt/g/test/MemOS")`

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

## Hooks for Users

MemOS provides Claude Code hooks in `project-memory/hooks/node/`. See `project-memory/hooks/settings-template.json` for setup instructions.

| Hook | Event | Purpose |
|------|-------|---------|
| `memos_session_start.js` | SessionStart | Output CWD→cube_id mapping |
| `memos_user_prompt.js` | UserPromptSubmit | Smart intent detection, suggest memos_search |
| `memos_block_mkdir_memory.js` | PreToolUse (Bash) | Block `mkdir.*memory` commands |
| `memos_auto_save.js` | PostToolUse (Bash/Edit/Write) | Suggest memory type + project_path |
| `memos_notify_milestone.js` | PostToolUse (Edit/Write) | Suggest MILESTONE for important files |
| `memos_pre_compact.js` | PreCompact | Remind: use MCP memos, not mkdir |

---

## API Endpoints

### Graph API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/product/graph/data` | POST | Export graph nodes and edges |
| `/product/graph/trace_path` | POST | Trace paths between two nodes |
| `/product/graph/schema` | POST | Export graph schema and statistics |
| `/product/search` | POST | Search with optional `enable_context_analysis` |

### Example: Context-Aware Search

```json
POST /product/search
{
  "user_id": "dev_user",
  "query": "what was the solution?",
  "readable_cube_ids": ["memos_cube"],
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
| `mcp-server/tools_registry.py` | Tool definitions (descriptions survive compaction) |
| `mcp-server/handlers/` | Tool handler implementations |
| `project-memory/SKILL.md` | Full skill documentation |
| `project-memory/hooks/` | Claude Code hooks for users |
| `data/memos_cubes/dev_cube/config.json` | Default cube configuration |

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
