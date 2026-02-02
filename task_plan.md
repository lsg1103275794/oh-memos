# Task Plan: 研究引入最新记忆技术到 MemOS

## Goal
研究 MAGMA（多图记忆架构）、EverMemOS（自组织记忆OS）、HippoRAG 2（PPR图检索）等最新技术，评估哪些可以引入 MemOS 以增强记忆能力，并制定具体的引入方案。

## Current Phase
All Implementation Phases Complete (P0-P2) ✅

## Phases

### Phase 1: 现有架构分析
- [x] 分析 MemOS 当前 Neo4j 图谱结构（节点类型、关系类型）
- [x] 分析当前记忆存储/检索流程
- [x] 分析 MCP Server 工具调用链
- [x] 识别现有架构的瓶颈和局限
- **Status:** complete

### Phase 2: 候选技术深度研究
- [x] MAGMA 多图分离架构：semantic/temporal/causal/entity
- [x] EverMemOS MemCell 结构 + Foresight 机制
- [x] HippoRAG 2 Personalized PageRank 检索
- [x] 评估每个技术的改造成本和收益
- **Status:** complete

### Phase 3: 可行性评估与方案设计
- [x] 与现有架构的兼容性分析
- [x] 优先级排序（成本/收益矩阵）
- [x] 分阶段引入路线图
- [x] 输出 findings.md
- **Status:** complete

### Implementation Phase 1: 多图视图路由 (P0)
- [x] query_processing.py: 新增 detect_query_intent(), filter_edges_by_intent()
- [x] handlers/search.py: 集成意图检测和边过滤
- [x] handlers/graph.py: 动态 Cypher 查询
- [x] 测试验证
- **Status:** complete

### Implementation Phase 2: PPR 检索增强 (P1) — ✅ 完成
- [x] 安装 Neo4j GDS 插件
- [x] 在 recall.py 增加 PPR 检索路径
- [x] neo4j.py 增加 search_by_ppr() 方法
- [x] 实验对比效果
- **Status:** complete

### Implementation Phase 3: 时序图增强 (P2) — ✅ 完成
- [x] neo4j.py: search_by_temporal() + get_temporal_context()
- [x] recall.py: _temporal_recall() + retrieve() 支持 temporal_intent
- [x] MCP handlers/search.py: 时序意图检测 + Neo4j 直查 + 结果合并
- [x] 支持时间窗口解析 (最近N小时/今天/本周)
- **Status:** complete

## Key Questions
1. 现有 Neo4j 图谱的关系类型有哪些？能否扩展为多图？
2. 当前检索流程是否支持 PPR 算法？
3. MemCell 式结构能否兼容现有 tree_text 模式？
4. 哪些改动可以在不破坏现有功能的前提下渐进引入？

## Decisions Made
| Decision | Rationale |
|----------|-----------|

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|

## Notes
- 重点关注与现有 Neo4j + Qdrant 架构的兼容性
- 优先选择改造成本最低、收益最高的方案
