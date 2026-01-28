# Findings: AI 知识图谱优化研究

## 1. 现有代码架构发现

### 1.1 图谱组织模块 (tree_text_memory/organize/)
- `relation_reason_detector.py` - 核心关系推理检测器
  - 支持 CAUSE/CONDITION/CONFLICT/RELATE 关系检测
  - 使用 `BATCH_PAIRWISE_RELATION_PROMPT` 批量推理
  - 已有 `_infer_fact_nodes_from_relations` 推理新节点能力
  - **可扩展点**: 可在此基础上增加三元组抽取

### 1.2 LLM Prompt 模板 (templates/)
- `tree_reorganize_prompts.py` - 图谱重组相关 Prompt
  - `BATCH_PAIRWISE_RELATION_PROMPT` - 批量关系检测
  - `INFER_FACT_PROMPT` - 事实推理
  - `AGGREGATE_PROMPT` - 聚合概念
  - **可扩展点**: 新增三元组抽取和意图分析 Prompt

### 1.3 Neo4j 数据层
- `neo4j.py` - 企业版实现
- `neo4j_community.py` - 社区版实现
  - `search_by_embedding` - 向量搜索
  - **缺失**: 多跳路径查询方法

### 1.4 MCP 服务层
- `memos_mcp_server.py` - 当前 MCP 工具
  - `memos_search` - 基础搜索
  - `memos_save` - 基础保存 (基于规则的类型检测)
  - `memos_get_graph` - 图谱查询 (仅直接关系)
  - **缺失**: 路径推理、Schema 导出

## 2. Neo4j-KGBuilder 借鉴点

### 2.1 可借鉴
- 批量操作 API 设计
- 三元组导入/导出格式

### 2.2 不适用
- 领域隔离方式 (MemOS 多租户方案更成熟)
- 纯关键词搜索 (MemOS 向量搜索是优势)

## 3. 技术决策

### 3.1 三元组抽取位置
- **决策**: 在 `organize/` 模块新增 `triple_extractor.py`
- **理由**: 与现有 `relation_reason_detector.py` 平级，共用 LLM 调用逻辑

### 3.2 路径查询实现
- **决策**: 在 `neo4j.py` 基类新增 `trace_path` 方法
- **理由**: 社区版和企业版共用同一 Cypher 逻辑

### 3.3 Prompt 模板组织
- **决策**: 新增 `graph_ai_prompts.py` 存放新 Prompt
- **理由**: 与现有 `tree_reorganize_prompts.py` 分离，职责清晰

## 4. 关键代码位置

| 功能 | 文件位置 | 关键方法/类 |
|-----|---------|------------|
| 关系检测 | `organize/relation_reason_detector.py` | `RelationAndReasoningDetector` |
| Prompt 模板 | `templates/tree_reorganize_prompts.py` | 多个 PROMPT 常量 |
| Neo4j 操作 | `graph_dbs/neo4j.py` | `Neo4jGraphDB` |
| MCP 工具 | `mcp-server/memos_mcp_server.py` | `@server.call_tool()` |
| API 路由 | `api/routers/` | 各 router 文件 |

## 5. 待确认问题
- [x] 三元组抽取是否在保存时同步执行，还是异步后台处理？**决策**: 异步后台，集成到现有 MemoryManager 流程
- [ ] 路径推理的最大深度限制？**建议**: 默认 3 跳，可配置
- [ ] 上下文感知搜索需要多少对话历史？**建议**: 最近 5 轮对话

## 6. Phase 1 探索完成 - 代码位置总结

### 6.1 MCP Server 层 (`mcp-server/memos_mcp_server.py`)
- **现有工具**:
  - `memos_search` - 语义搜索 (line 461-491)
  - `memos_save` - 保存记忆 (line 492-536)
  - `memos_get_graph` - 获取图谱关系 (line 623-656, 直接查 Neo4j)
- **扩展点**: 在 `list_tools()` 中添加新工具定义，在 `call_tool()` 中实现处理逻辑
- **关键发现**: `memos_get_graph` 直接调用 Neo4j HTTP API，未走 MemOS API 层

### 6.2 API 路由层 (`src/memos/api/routers/server_router.py`)
- **架构模式**: 使用 Handler 类进行依赖注入
- **现有 Handler**:
  - `SearchHandler` - 搜索处理
  - `GraphHandler` - 图谱数据导出 (line 113-119)
  - `AddHandler` - 添加记忆
  - `ChatHandler` - 对话处理
- **扩展点**: 创建新 Handler 类，在 router 中注册端点

### 6.3 GraphHandler (`src/memos/api/handlers/graph_handler.py`)
- 仅 60 行，负责调用 `graph_db.export_graph()`
- **扩展点**: 添加 `handle_trace_path()` 方法

### 6.4 Product Models (`src/memos/api/product_models.py`)
- 完整的 Request/Response 模型定义
- `GraphNode`, `GraphEdge`, `GraphData` 已定义
- **扩展点**: 添加 `TracePathRequest`, `TracePathResponse`, `SchemaExportResponse` 等
