# Task Plan: MCP Server 代码优化

## Goal
重构 `mcp-server/memos_mcp_server.py` 代码质量，消除重复代码，修复 bug，提升可维护性。

## Scope
- 抽取公共重试逻辑
- 修复 tree_text 模式下的解析 bug
- Neo4j 凭证改为可配置
- 复用 httpx 客户端
- 合并冗余工具定义
- 添加缺失的参数

## Current Issues (已识别)

| Issue | Severity | Location |
|-------|----------|----------|
| 重试逻辑重复 5-6 遍 | High | memos_search, memos_save, memos_list, memos_get_stats |
| `memos_get_graph` tree_text 解析 bug | High | line ~1324 |
| Neo4j 凭证硬编码 | Medium | line ~1248-1249, ~1305-1306 |
| httpx 无连接复用 | Medium | call_tool() 函数 |
| `memos_get_stats` 统计逻辑重复 | Low | retry block |
| `memos_search` 缺少 `top_k` 参数 | Low | tool definition |

## Phases

### Phase 1: 调研分析
- Status: `completed`
- Findings:
  - [x] 重试模式可抽取为装饰器或辅助函数
  - [x] `memos_get_graph` 的 `memories.extend()` 调用错误处理了 tree_text 格式
  - [x] Neo4j 配置应加入环境变量体系

### Phase 2: 抽取公共重试逻辑
- Status: `completed`
- Deliverables:
  - [x] 创建 `api_call_with_retry()` 辅助函数
  - [x] 重构 memos_search, memos_save, memos_list, memos_get_stats 使用辅助函数
  - [x] 消除了大量重复的重试代码

### Phase 3: 修复 Bug 和配置问题
- Status: `completed`
- Deliverables:
  - [x] 修复 `memos_get_graph` tree_text 解析 (使用 extract_memories_from_response)
  - [x] Neo4j 配置改为环境变量 (NEO4J_HTTP_URL, NEO4J_USER, NEO4J_PASSWORD)
  - [x] 添加 `memos_search` 的 `top_k` 参数

### Phase 4: httpx 客户端复用
- Status: `completed`
- Deliverables:
  - [x] 使用 `get_http_client()` 共享客户端
  - [x] 配置连接池 (max_connections=20, max_keepalive=10)
  - [x] 添加 `close_http_client()` 清理函数

### Phase 5: 代码清理
- Status: `completed`
- Deliverables:
  - [x] 统一所有工具处理器缩进 (8 空格 for elif)
  - [x] 抽取 `compute_memory_stats()` 辅助函数
  - [x] 抽取 `extract_memories_from_response()` 辅助函数

### Phase 6: 测试验证
- Status: `completed`
- Deliverables:
  - [x] Python 语法检查通过
  - [x] 文档更新 (CLAUDE.md, progress.md)

## Results Summary
- **代码行数**: 1684 行 (优化后)
- **Git diff**: +846 insertions, -372 deletions
- **新增辅助函数**: 5 个
- **修复 bug**: 1 个 (tree_text 解析)
- **新增参数**: 1 个 (top_k)

## Decisions Made
| Decision | Rationale | Date |
|----------|-----------|------|
| (pending) | | |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (none yet) | | |

## Files to Modify
- `mcp-server/memos_mcp_server.py` - 主要重构目标
