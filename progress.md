# Progress Log: AI 知识图谱优化

## Session: 2026-01-28

### 14:00 - 项目分析完成
- [x] 分析了 Neo4j-KGBuilder 仓库
- [x] 对比了 MemOS 现有实现
- [x] 确定了 AI 层面优化方向
- [x] 创建了规划文件

### 优化方向确定
| 优先级 | 功能 | 状态 |
|-------|------|------|
| P0 | 三元组自动抽取 | `planned` |
| P0 | 图谱路径推理 API | `planned` |
| P1 | 上下文感知搜索 | `planned` |
| P1 | 层级树位置规划 | `planned` |
| P2 | 图谱 Schema 导出 | `planned` |
| P2 | 记忆质量评估 | `planned` |

### 下一步
- [x] 开始 Phase 1: 探索现有代码结构
- [x] 确认扩展点位置
- [x] 设计新模块接口
- [x] Phase 2: 实现三元组自动抽取
- [x] Phase 3: 实现图谱路径推理 API
- [x] Phase 4: 增强上下文感知搜索
- [x] Phase 5: 图谱 Schema 导出
- [x] Phase 6: 集成测试与文档

### 本次 Session 完成的工作
1. **三元组抽取模块** (`src/memos/memories/textual/tree_text_memory/organize/triple_extractor.py`)
   - 支持从记忆文本中抽取 (subject, predicate, object) 三元组
   - 12 种预定义关系类型 (WORKS_AT, LOCATED_IN, CAUSED 等)
   - 自动谓词标准化和置信度验证

2. **图谱 AI Prompts** (`src/memos/templates/graph_ai_prompts.py`)
   - TRIPLE_EXTRACTION_PROMPT - 三元组抽取
   - SEARCH_INTENT_PROMPT - 搜索意图分析
   - GRAPH_SCHEMA_INFERENCE_PROMPT - Schema 推理
   - MEMORY_QUALITY_EVALUATION_PROMPT - 记忆质量评估

3. **路径追踪功能** (`src/memos/graph_dbs/neo4j.py`)
   - `get_path()` - 简单路径查询
   - `trace_path()` - 完整路径追踪 (含节点和边详情)
   - `get_schema_statistics()` - 详细图谱统计信息

4. **上下文感知搜索** (`src/memos/memories/textual/tree_text_memory/organize/context_aware_searcher.py`)
   - `ContextAwareSearcher` 类使用 LLM 分析搜索意图
   - 支持从对话历史中提取上下文
   - 自动生成查询扩展和过滤建议
   - 识别意图类型: factual, relational, temporal, causal, exploratory

5. **新 API 端点**
   - `POST /product/graph/trace_path` - 路径追踪 API
   - `POST /product/graph/schema` - Schema 导出 API (增强版，含详细统计)
   - `POST /product/search` 增加 `enable_context_analysis` 参数

6. **新 MCP 工具**
   - `memos_trace_path` - 支持 AI 推理两个记忆节点之间的关系路径
   - `memos_search_context` - 支持带对话上下文的智能搜索
   - `memos_export_schema` - 导出图谱 Schema 和健康度评估

---

## Test Results
- Integration tests created at `tests/integration/test_ai_graph_features.py`
- Test classes: TestTripleExtraction, TestPathTracing, TestContextAwareSearch, TestSchemaExport, TestGraphDataExport, TestEndToEndWorkflow
- Run with: `pytest tests/integration/test_ai_graph_features.py -v`

## Phase 6 Completion Summary
1. **Integration Tests** (`tests/integration/test_ai_graph_features.py`)
   - TestTripleExtraction: Module import, prompt validation, predicate definition tests
   - TestPathTracing: API existence, structure validation, path depth tests
   - TestContextAwareSearch: Module import, context parameter, intent analysis tests
   - TestSchemaExport: API structure, edge distribution, time range tests
   - TestEndToEndWorkflow: Search-then-trace and schema health check workflows

2. **Documentation Updates**
   - CLAUDE.md: Added AI Graph Intelligence section with new MCP tools
   - README.md: Added new MCP tools to both EN/CN tool tables
   - README.md: Added "AI Graph Intelligence (New in v0.5.0)" section

## All Phases Complete
| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Explore existing code structure | Completed |
| Phase 2 | Implement triple extraction (P0) | Completed |
| Phase 3 | Implement graph path reasoning API (P0) | Completed |
| Phase 4 | Enhance context-aware search (P1) | Completed |
| Phase 5 | Graph schema export (P2) | Completed |
| Phase 6 | Integration tests and documentation | Completed |

## Blockers
(none)

---

# MCP Server Optimization - 2026-01-28

## Summary
重构 `mcp-server/memos_mcp_server.py`，消除重复代码，修复 bug，提升可维护性。

## Changes Made

### 新增辅助函数
| 函数 | 位置 | 作用 |
|------|------|------|
| `get_http_client()` | line ~480 | 共享 HTTP 客户端，连接池复用 |
| `close_http_client()` | line ~493 | 清理共享客户端 |
| `api_call_with_retry()` | line ~502 | 统一 API 调用 + 自动重注册重试 |
| `extract_memories_from_response()` | line ~560 | 统一记忆提取，修复 tree_text 模式 |
| `compute_memory_stats()` | line ~589 | 统一统计计算 |

### Bug 修复
- **P0**: `memos_get_graph` tree_text 解析 bug
  - 问题: `memories.extend(cube_data.get("memories", []))` 在 tree_text 模式下错误处理 dict
  - 修复: 使用 `extract_memories_from_response()` 正确检测 `nodes` 键

### 配置改进
- Neo4j 凭证改为环境变量:
  - `NEO4J_HTTP_URL` (默认: `http://localhost:7474/db/neo4j/tx/commit`)
  - `NEO4J_USER` (默认: `neo4j`)
  - `NEO4J_PASSWORD` (默认: `12345678`)

### 新增参数
- `memos_search` 新增 `top_k` 参数，允许控制返回结果数量 (默认: 10)

### 代码精简
| 工具 | 重试逻辑行数变化 |
|------|------------------|
| `memos_search` | ~25 行 → 8 行 |
| `memos_save` | ~40 行 → 8 行 |
| `memos_list` | ~25 行 → 8 行 |
| `memos_get_stats` | ~60 行 → 12 行 |

### 性能改进
- HTTP 客户端连接复用 (max_connections=20, max_keepalive=10)
- 避免每次工具调用创建新连接

## Verification
- Python 语法检查: ✅ 通过
