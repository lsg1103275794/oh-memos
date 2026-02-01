# Findings: 关键词查询优化调研

## 现有架构分析

### 搜索入口

**MCP Server** (`mcp-server/memos_mcp_server.py`)
- `memos_search`: 标准搜索 + 关键词排序（第 1419-1450 行）
- `memos_search_context`: 上下文感知搜索（第 1452-1520 行）

### 三路并行搜索

| 通道 | 文件 | 用途 |
|------|------|------|
| Vector | `src/memos/vec_dbs/qdrant.py` | Qdrant 向量相似度 |
| Graph | `src/memos/graph_dbs/neo4j.py` | Neo4j 图关系查询 |
| BM25 | `retrieve/bm25_util.py` | 关键词 BM25 评分 |

### 关键词处理流程

```
Query: "ERROR_PATTERN authentication"
  ↓
parse_memory_type_prefix()
  → type: ERROR_PATTERN
  → query: authentication
  ↓
extract_keywords("authentication")
  → ["authentication"]
  ↓
keyword_match_score(memory_text, ["authentication"])
  → 精确匹配 +2.0 / 子串匹配 +1.2
  ↓
最终分数 = relativity + keyword_score
```

---

## 现有关键词评分算法

```python
def keyword_match_score(text: str, keywords: list[str]) -> float:
    score = 0.0
    text_lower = text.lower()
    for kw in keywords:
        kw_lower = kw.lower()
        if len(kw_lower) > 1 and ord(kw_lower[0]) > 127:
            # 中文：精确匹配
            if kw in text:
                score += 2.0
        else:
            # 英文：词边界匹配优先
            pattern = r'\b' + re.escape(kw_lower) + r'\b'
            if re.search(pattern, text_lower):
                score += 2.0
            elif kw_lower in text_lower:
                score += 1.2
    # 匹配比例奖励
    matched = sum(1 for kw in keywords if kw.lower() in text_lower)
    if keywords:
        score += matched / len(keywords)
    return score
```

### 评分权重分析

| 匹配类型 | 分数 |
|----------|------|
| 英文词边界精确 | +2.0 |
| 中文精确包含 | +2.0 |
| 英文子串包含 | +1.2 |
| 匹配比例奖励 | 0-1.0 |

---

## 停用词列表

### 英文停用词（23个）
```
the, and, or, a, an, to, of, for, with, in, on, at, is, are,
was, were, be, been, being, this, that, it, as
```

### 中文停用词（18个）
```
的, 了, 和, 与, 在, 是, 有, 我, 你, 他, 她, 它, 这, 那, 个, 为, 及, 之
```

---

## BM25 实现细节

**EnhancedBM25** (`retrieve/bm25_util.py:18-187`)

### 搜索过程

1. **分词** - FastTokenizer 支持中英混合
2. **BM25 计分** - rank_bm25.BM25Okapi
3. **候选选择** - top_k × multiplier
4. **可选 TF-IDF 混合** - 权重 0.7 BM25 + 0.3 TF-IDF
5. **结果返回**

### 搜索目标

```python
# 从 node_dicts 构建搜索语料
searchable_text = node["metadata"]["key"] + " " + " ".join(node["metadata"]["tags"])
```

---

## 性能观察

### 当前瓶颈

1. **全量关键词遍历** - `apply_keyword_rerank` 遍历所有结果
2. **无关键词索引** - 每次查询都重新计算匹配
3. **固定权重** - 无法根据查询类型调整

### 优化机会

1. **倒排索引** - 预计算关键词到记忆的映射
2. **缓存热点** - LRU 缓存高频查询
3. **动态权重** - 根据查询意图调整

---

## 竞品/开源方案参考

### Elasticsearch
- 倒排索引 + BM25
- 支持模糊匹配、同义词
- 可配置的分析器链

### Meilisearch
- 即时搜索（< 50ms）
- 拼写容错
- 同义词支持

### 建议借鉴

1. **分词增强** - 使用 jieba 进行中文分词
2. **同义词扩展** - 维护同义词词典
3. **拼写纠错** - Levenshtein 距离容错

---

## 待调研问题

- [ ] Qdrant 是否支持关键词过滤？
- [ ] Neo4j 全文索引性能如何？
- [ ] 是否需要引入专门的搜索引擎？
