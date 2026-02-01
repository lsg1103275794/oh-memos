# Task Plan: 关键词查询匹配优化

## Goal
优化 MemOS 的搜索功能，使其在记忆数量和项目规模增长时，能够通过关键词精确匹配快速找到目标记忆。

## Current Phase
Phase 1

## 现有功能分析

### 已有的搜索架构

```
MCP memos_search(query)
  │
  ├─→ parse_memory_type_prefix()     # 提取 [TYPE] 前缀
  ├─→ API POST /search
  │   ├─→ _graph_recall()            # Neo4j 图查询
  │   ├─→ _vector_recall()           # Qdrant 向量搜索
  │   └─→ _bm25_recall()             # BM25 关键词搜索
  │
  ├─→ filter_memories_by_type()      # 按类型过滤
  ├─→ apply_keyword_rerank()         # 关键词重排序
  └─→ format_memories_for_display()  # 格式化输出
```

### 现有关键词处理 (mcp-server/memos_mcp_server.py)

| 功能 | 代码行 | 说明 |
|------|--------|------|
| extract_keywords() | 804-830 | 提取中英文关键词，停用词过滤 |
| keyword_match_score() | 833-853 | 计算匹配分数：精确+2.0，子串+1.2 |
| apply_keyword_rerank() | 856-880 | 按 relativity + keyword_score 重排 |

### 现有 BM25 实现 (retrieve/bm25_util.py)

- EnhancedBM25 类
- 支持 TF-IDF 混合权重（0.7 BM25 + 0.3 TF-IDF）
- 搜索目标：key 字段 + tags

---

## 问题识别

### 问题 1: 缺乏多项目/Cube 级别的快速定位
- 当有多个项目时，用户需要记住 cube_id
- 无法跨项目搜索或模糊匹配项目名

### 问题 2: 关键词匹配精度不足
- 当前关键词评分较粗糙（仅精确/子串匹配）
- 未利用结构化字段（tags, key）的权重
- 停用词列表有限

### 问题 3: 大规模数据时性能问题
- 未有索引策略
- 全量遍历进行关键词匹配

### 问题 4: 搜索结果相关性
- 向量相似度和关键词匹配的权重固定
- 无法动态调整搜索策略

---

## Phases

### Phase 1: Requirements & Discovery
- [x] 分析现有搜索架构
- [x] 理解 MCP Server 关键词处理逻辑
- [x] 识别 BM25 和向量搜索实现
- [x] 文档化问题点
- **Status:** complete

### Phase 2: 设计优化方案
- [x] 设计多 Cube 快速索引
- [x] 设计关键词匹配增强策略
- [x] 设计权重动态调整机制
- [ ] 设计分页和缓存策略
- **Status:** complete

### Phase 3: 实现 - 关键词匹配增强
- [x] 扩展停用词库（中英文）
- [x] 增加结构化字段权重
- [x] 实现模糊匹配（Levenshtein 距离）
- [ ] 支持同义词扩展
- **Status:** complete

### Phase 4: 实现 - 多 Cube 索引
- [x] 创建 Cube 元数据索引
- [x] 实现 Cube 名称/描述搜索
- [ ] 支持跨 Cube 搜索（用户明确不需要）
- **Status:** complete

### Phase 5: 实现 - 性能优化
- [ ] 添加关键词索引（倒排索引）
- [ ] 实现查询缓存
- [ ] 优化大规模数据检索
- **Status:** pending

### Phase 6: Testing & Verification
- [x] 单元测试
- [ ] 性能基准测试
- [ ] 用户验收测试
- **Status:** in_progress

---

## Key Questions

1. 关键词匹配是否需要支持模糊匹配（拼写纠错）？
2. 是否需要支持跨 Cube 搜索？
3. 搜索结果的分页策略？
4. 是否需要搜索历史/热门搜索功能？
5. 权重调整是用户可配置还是自动学习？

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 在 MCP Server 层做关键词增强 | 保持后端 API 稳定，前端灵活 |
| 保留现有三路并行搜索 | 架构成熟，性能良好 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| (暂无) | - | - |

## 优化方案草案

### 方案 A: 增强现有关键词评分

```python
def enhanced_keyword_score(text: str, keywords: list[str], metadata: dict) -> float:
    score = 0.0

    # 1. 精确匹配（权重更高）
    for kw in keywords:
        if kw in text:
            score += 3.0 if is_exact_word_match(text, kw) else 1.5

    # 2. 结构化字段加权
    key = metadata.get("key", "")
    tags = metadata.get("tags", [])

    for kw in keywords:
        if kw in key:
            score += 4.0  # key 字段权重最高
        if any(kw in tag for tag in tags):
            score += 2.5  # tag 字段权重次之

    # 3. 模糊匹配（可选）
    for kw in keywords:
        for word in text.split():
            if levenshtein_distance(kw, word) <= 2:
                score += 0.5

    return score
```

### 方案 B: 多 Cube 索引

```python
# Cube 元数据结构
CubeIndex = {
    "cube_id": str,
    "name": str,
    "description": str,
    "project_path": str,
    "keywords": list[str],  # 从记忆中提取的高频词
    "memory_count": int,
    "last_updated": datetime
}

# 快速定位
def find_cubes_by_keyword(keyword: str) -> list[CubeIndex]:
    # 搜索 cube name, description, keywords
    pass
```

### 方案 C: 倒排索引加速

```python
# 倒排索引结构
InvertedIndex = {
    "keyword1": ["mem_id_1", "mem_id_3", "mem_id_5"],
    "keyword2": ["mem_id_2", "mem_id_3"],
    ...
}

# 查询时直接定位，无需全量遍历
def search_by_inverted_index(keywords: list[str]) -> list[str]:
    result_ids = set()
    for kw in keywords:
        if kw in inverted_index:
            result_ids.update(inverted_index[kw])
    return list(result_ids)
```

---

## Notes

- Update phase status as you progress: pending → in_progress → complete
- Re-read this plan before major decisions
- Log ALL errors - they help avoid repetition
- 现有架构已经比较完善，优化重点在增强而非重构
