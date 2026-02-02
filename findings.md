# Findings: 最新记忆技术引入 MemOS 研究

## 候选技术

### 1. MAGMA — 多图记忆架构
- **论文**: arxiv.org/abs/2601.03236 (2026.01)
- **核心**: 4 个正交关系图 (semantic/temporal/causal/entity)
- **GitHub**: github.com/FredJiang0324/MAMGA
- **亮点**: Token 消耗减少 95%，延迟 1.47s（快 40%）

### 2. EverMemOS — 自组织记忆OS
- **论文**: arxiv.org/abs/2601.02163 (2026.01)
- **核心**: MemCell 生命周期 + Foresight 预测信号
- **GitHub**: github.com/EverMind-AI/EverMemOS
- **亮点**: Episodic→Semantic Consolidation→Reconstructive Recollection 三阶段

### 3. HippoRAG 2 — PPR 图检索
- **论文**: arxiv.org/abs/2502.14802 (ICML 2025)
- **核心**: 双节点 KG + Personalized PageRank
- **GitHub**: github.com/OSU-NLP-Group/HippoRAG
- **亮点**: 关联记忆任务比 embedding 高 7% F1，且不牺牲简单事实检索

---

## 现有架构分析

### Neo4j 图谱结构

**节点 (Label: Memory)**
```
属性:
  - id: UUID
  - memory: 记忆内容
  - memory_type: WorkingMemory | LongTermMemory | UserMemory | OuterMemory
  - status: activated | archived
  - key: 摘要关键词
  - tags: [tag1, tag2, ...]
  - background: 背景描述
  - confidence: 置信度 0-1
  - type: normal | reasoning (推理节点)
  - sources: [来源ID列表]
  - user_name: 租户标识 (cube_id)
  - created_at, updated_at: 时间戳
  - embedding: (存储在 Qdrant，非 Neo4j)
```

**关系类型**
```
已实现:
  - CAUSE: 因果关系 (A 导致 B)
  - CONDITION: 条件关系 (A 是 B 的前提)
  - RELATE: 相关关系 (A 与 B 相关)
  - CONFLICT: 冲突关系 (A 与 B 矛盾)
  - PARENT: 层次结构 (A 是 B 的父节点)
  - FOLLOWS: 时序关系 (A 发生在 B 之后)

关系创建:
  - relation_reason_detector.py: LLM 批量检测 CAUSE/CONDITION/RELATE/CONFLICT
  - 基于标签重叠找邻居，然后 LLM 判断关系类型
```

### 检索流程

```
query → GraphMemoryRetriever.retrieve()
         ├── _graph_recall()    # Neo4j: 按 key/tags 匹配
         ├── _vector_recall()   # Qdrant: embedding 相似度
         ├── _bm25_recall()     # BM25 关键词匹配 (可选)
         └── _fulltext_recall() # Neo4j 全文索引 (可选)
         → 合并去重 → rerank → 返回
```

**关键文件:**
- `neo4j_community.py`: 双存储 (Neo4j 图 + Qdrant 向量)
- `recall.py`: GraphMemoryRetriever 混合检索
- `relation_reason_detector.py`: 关系检测
- `reorganizer.py`: 调用关系检测器，写入边

### 当前局限

1. **单一关系图**: 所有关系混在一起，无法按意图路由
2. **无时序图分离**: FOLLOWS 边存在但未充分利用
3. **无 PPR 检索**: 只有向量相似度 + 图结构匹配
4. **无 Foresight**: 不能预测未来可能用到的记忆
5. **无记忆生命周期**: 扁平存储，无 episodic→consolidated 演进

---

## 兼容性评估

| 技术 | 改造难度 | 兼容性 | 收益 |
|------|---------|--------|------|
| **MAGMA 多图分离** | ⭐⭐ 中 | ✅ 高 | 🔥🔥🔥 高 |
| EverMemOS MemCell | ⭐⭐⭐ 高 | ⚠️ 中 | 🔥🔥 中 |
| HippoRAG 2 PPR | ⭐⭐ 中 | ✅ 高 | 🔥🔥 中 |
| EverMemOS Foresight | ⭐⭐⭐ 高 | ⚠️ 中 | 🔥 低-中 |

### MAGMA 多图分离 — 推荐优先引入

**为什么推荐:**
- 现有架构已有 4 种关系 (CAUSE/CONDITION/RELATE/CONFLICT)，天然可分为多图
- 改造集中在查询层，不需要改变存储结构
- 收益显著: Token 减少 95%，延迟减少 40%

**改造方案:**
```python
# 新增: 多图视图查询器
class MultiGraphQueryRouter:
    def route_query(self, query: str, intent: str) -> list[str]:
        """根据意图选择要查询的关系图"""
        intent_to_graphs = {
            "why": ["CAUSE", "CONDITION"],      # 为什么？→ 因果图
            "what_related": ["RELATE"],         # 相关？→ 语义图
            "conflict": ["CONFLICT"],           # 冲突？→ 冲突图
            "when": ["FOLLOWS"],                # 什么时候？→ 时序图
            "default": ["CAUSE", "RELATE"]      # 默认
        }
        return intent_to_graphs.get(intent, intent_to_graphs["default"])
```

**涉及文件:**
- `mcp-server/handlers/search.py` — 增加意图识别
- `src/memos/memories/textual/tree_text_memory/retrieve/recall.py` — 增加图过滤
- `mcp-server/query_processing.py` — 扩展查询处理

### HippoRAG 2 PPR — 第二优先

**为什么推荐:**
- Neo4j 原生支持 PageRank 算法
- 可以在现有图结构上直接添加 PPR 检索路径

**改造方案:**
```cypher
# Neo4j PPR 查询
CALL gds.pageRank.stream('memory_graph', {
  relationshipWeightProperty: 'weight',
  personalizations: [{nodeIds: [$query_node_ids]}]
})
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).id AS id, score
ORDER BY score DESC
LIMIT $top_k
```

**注意:** 需要 Neo4j GDS 插件 (Graph Data Science)

---

## 推荐方案 — 分阶段引入

### Phase 1: 多图视图路由 (2-3 天)
- 在查询层增加意图识别
- 根据意图过滤要查询的关系类型
- 不改变存储结构，只改变查询方式

### Phase 2: PPR 检索增强 (3-5 天)
- 安装 Neo4j GDS 插件
- 增加 PPR 检索路径作为 vector recall 的补充
- 实验对比效果

### Phase 3: 时序图增强 (2 天)
- 充分利用现有 FOLLOWS 关系
- 增加时间窗口查询
- 支持"最近的..."类查询

### Phase 4 (可选): Foresight 机制
- 保存记忆时预测未来可能的查询
- 类似 EverMemOS 的前瞻信号

---

## 代码参考

### 已实现: Multi-Graph View Routing (P0)

**改动文件:**
- `mcp-server/query_processing.py` — 新增意图检测和边过滤
- `mcp-server/handlers/search.py` — 集成多图路由
- `mcp-server/handlers/graph.py` — 动态 Cypher 查询

**核心函数:**
```python
# query_processing.py

def detect_query_intent(query: str) -> str:
    """检测意图: causal/related/conflict/temporal/default"""
    # 中英文模式匹配
    causal_patterns = [r"为什么", r"why", r"原因", r"cause", ...]
    ...

def get_graphs_for_intent(intent: str) -> list[str]:
    """意图 → 关系类型"""
    INTENT_TO_GRAPHS = {
        "causal": ["CAUSE", "CONDITION"],
        "related": ["RELATE"],
        "conflict": ["CONFLICT"],
        "temporal": ["FOLLOWS"],
        "default": ["CAUSE", "RELATE", "CONDITION"],
    }
    return INTENT_TO_GRAPHS.get(intent, ...)

def filter_edges_by_intent(data: dict, intent: str) -> dict:
    """过滤边 + boost 匹配节点"""
    allowed = get_graphs_for_intent(intent)
    # 只保留 allowed 类型的边
    # boost 有边的节点 relativity +0.5
```

**使用示例:**
```
查询: "为什么 Neo4j 连接超时?"
  → 意图: causal
  → 只查询 CAUSE/CONDITION 边
  → boost 有因果关系的记忆节点
```

### 当前关系检测 (relation_reason_detector.py:83-122)
```python
def _detect_pairwise_causal_condition_relations(self, node, nearest_nodes):
    """LLM 批量判断关系类型"""
    # 构建 node pairs
    # 调用 LLM 判断 CAUSE/CONDITION/RELATE/CONFLICT
    # 返回 relations 列表
```

### 当前检索 (recall.py:35-136)
```python
def retrieve(self, query, parsed_goal, top_k, memory_scope, ...):
    """混合检索: 图 + 向量 + BM25"""
    # 并行执行:
    #   - _graph_recall: Neo4j key/tags 匹配
    #   - _vector_recall: Qdrant embedding 搜索
    #   - _bm25_recall: BM25 关键词 (可选)
    # 合并去重返回
```

### 当前边操作 (neo4j.py:402-427)
```python
def add_edge(self, source_id, target_id, type, user_name=None):
    """创建任意类型的边"""
    query = f"MERGE (a)-[:{type}]->(b)"
    # 已支持动态关系类型
```
