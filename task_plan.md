# Task Plan: AI 层面知识图谱构建优化

## Goal
增强 MemOS 项目在 AI 层面对知识图谱的构建能力，实现：
1. **后端 LLM 对图谱结构树的智能勾画** - 自动抽取实体关系、规划节点层级
2. **MCP 调用时 AI 对项目的深层理解** - 图谱路径推理、上下文感知搜索

## Scope
- 新增三元组自动抽取模块
- 新增图谱路径推理 MCP API
- 增强 MCP 搜索的上下文感知能力
- 新增图谱 Schema 导出工具

## Phases

### Phase 1: 探索现有代码结构
- Status: `pending`
- Files to examine:
  - [ ] `src/memos/memories/textual/tree_text_memory/organize/` - 图谱组织模块
  - [ ] `src/memos/graph_dbs/neo4j*.py` - Neo4j 操作层
  - [ ] `src/memos/templates/` - LLM Prompt 模板
  - [ ] `mcp-server/memos_mcp_server.py` - MCP 服务层
  - [ ] `src/memos/api/routers/` - API 路由

### Phase 2: 实现三元组自动抽取 (P0)
- Status: `completed`
- Deliverables:
  - [x] 新增 `triple_extractor.py` 模块
  - [x] 新增 `TRIPLE_EXTRACTION_PROMPT` 模板
  - [ ] 在记忆保存流程中集成三元组抽取 (可后续增强)
  - [x] Prompt 模板包含验证谓词类型

### Phase 3: 实现图谱路径推理 API (P0)
- Status: `completed`
- Deliverables:
  - [x] 新增 `memos_trace_path` MCP 工具
  - [x] 在 Neo4j 层实现 `trace_path()` 方法
  - [x] 在 Neo4j 层实现 `get_path()` 方法
  - [x] 新增 API 路由 `/graph/trace_path`
  - [x] 新增 API 路由 `/graph/schema`
  - [x] 单元测试

### Phase 4: 增强上下文感知搜索 (P1)
- Status: `completed`
- Deliverables:
  - [x] 新增 `ContextAwareSearcher` 类
  - [x] 新增 `SEARCH_INTENT_PROMPT` 模板 (Phase 2 已完成)
  - [x] 在 `SearchHandler` 中集成 `handle_context_aware_search` 方法
  - [x] 在 `APISearchRequest` 中添加 `enable_context_analysis` 参数
  - [x] 新增 `memos_search_context` MCP 工具

### Phase 5: 图谱 Schema 导出 (P2)
- Status: `completed`
- Deliverables:
  - [x] 新增 `memos_export_schema` MCP 工具
  - [x] 新增 API 路由 `/graph/schema` (Phase 3 已完成)
  - [x] 实现 `get_schema_statistics()` 方法 in Neo4jGraphDB
  - [x] 增强 GraphSchemaData 模型包含详细统计信息
  - [x] 图谱健康度评估 (orphan ratio, connectivity)

### Phase 6: 集成测试与文档
- Status: `completed`
- Deliverables:
  - [x] 端到端测试用例
  - [x] 更新 CLAUDE.md 使用说明
  - [x] 更新 README

## Decisions Made
| Decision | Rationale | Date |
|----------|-----------|------|
| 优先实现 P0 功能 | 三元组抽取和路径推理是核心能力 | 2026-01-28 |
| 基于现有 RelationAndReasoningDetector 扩展 | 复用已有的 LLM 调用和关系检测逻辑 | 2026-01-28 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (none yet) | | |

## Files Created/Modified
- `src/memos/templates/graph_ai_prompts.py` - NEW: AI prompts for graph operations
- `src/memos/memories/textual/tree_text_memory/organize/triple_extractor.py` - NEW: Triple extraction module
- `src/memos/memories/textual/tree_text_memory/organize/context_aware_searcher.py` - NEW: Context-aware search module
- `src/memos/graph_dbs/neo4j.py` - MODIFIED: Added `get_path()`, `trace_path()`, and `get_schema_statistics()` methods
- `src/memos/api/product_models.py` - MODIFIED: Added TracePathRequest/Response, enhanced GraphSchemaData with statistics
- `src/memos/api/handlers/graph_handler.py` - MODIFIED: Added `handle_trace_path()` and enhanced `handle_get_schema()`
- `src/memos/api/handlers/search_handler.py` - MODIFIED: Added `handle_context_aware_search()` and ContextAwareSearcher integration
- `src/memos/api/routers/server_router.py` - MODIFIED: Added `/graph/trace_path`, `/graph/schema` endpoints, updated search to support context analysis
- `mcp-server/memos_mcp_server.py` - MODIFIED: Added `memos_trace_path`, `memos_search_context`, and `memos_export_schema` MCP tools
- `tests/api/test_graph_api.py` - MODIFIED: Comprehensive graph API tests
