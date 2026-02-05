# Phase 3: PROGRESS 自动归档详细设计

## 概述

为 PROGRESS 类型记忆实现 TTL 自动归档，防止存储膨胀。

## 现有基础设施

**已存在的字段（无需新增）：**
- `created_at`: datetime - 首次创建时间
- `updated_at`: datetime - 最后更新时间
- `status`: Literal["activated", "archived", "deleted"] - 默认 "activated"

**已存在的过滤机制：**
- 搜索时 `status="activated"` 过滤已实现
- Neo4j + Qdrant 双端过滤

## 实现方案

### 1. 配置项

添加到 `.env` 和 `config.py`:
```python
# 归档阈值（天），默认 7 天
MEMOS_ARCHIVE_TTL_DAYS=7

# 是否启用自动归档
MEMOS_AUTO_ARCHIVE=true

# 归档扫描间隔（秒），默认 1 小时
MEMOS_ARCHIVE_INTERVAL=3600

# 仅对 PROGRESS 类型归档（可扩展）
MEMOS_ARCHIVE_TYPES=PROGRESS
```

### 2. 归档逻辑

```python
# src/memos/mem_scheduler/archiver.py

async def archive_expired_memories(
    graph_db,
    archive_ttl_days: int = 7,
    archive_types: list[str] = ["PROGRESS"],
    user_name: str | None = None,
) -> int:
    """
    将过期的记忆标记为 archived。

    Returns:
        归档的记忆数量
    """
    cutoff_date = datetime.now() - timedelta(days=archive_ttl_days)

    # Cypher 查询：找到过期的 PROGRESS 类型记忆
    cypher = """
    MATCH (n:Memory)
    WHERE n.status = 'activated'
      AND n.created_at < datetime($cutoff)
      AND any(tag IN n.tags WHERE tag IN $archive_types)
    SET n.status = 'archived',
        n.archived_at = datetime()
    RETURN count(n) as archived_count
    """

    # 同时更新向量 DB 的 status 字段
    ...

    return archived_count
```

### 3. 定时任务集成

**方案 A：使用现有 Scheduler**

在 `GeneralScheduler` 中添加归档任务：
```python
# general_scheduler.py
ARCHIVE_TASK_LABEL = "archive"

# 注册 handler
handlers[ARCHIVE_TASK_LABEL] = self._archive_consumer

# 启动时调度周期性任务
self._schedule_periodic_archive()
```

**方案 B：独立后台线程（更简单）**

在 API 启动时创建后台任务：
```python
# start_api.py
@app.on_event("startup")
async def startup_archiver():
    if os.getenv("MEMOS_AUTO_ARCHIVE", "true") == "true":
        asyncio.create_task(periodic_archive_task())
```

**推荐方案 B**，因为：
- 不依赖 Redis/复杂调度器
- 实现简单，风险低
- 可独立测试

### 4. 手动归档 API

添加端点用于手动触发/查询归档状态：
```
POST /archive/run     → 手动触发归档
GET  /archive/stats   → 查询归档统计
POST /archive/restore → 恢复被归档的记忆（可选）
```

### 5. MCP 工具（可选）

```python
# memos_archive_stats - 查看归档统计
# memos_restore - 恢复特定记忆（需要 MEMOS_ENABLE_DELETE=true）
```

## 文件变更计划

### 新增文件
- `src/memos/mem_scheduler/archiver.py` - 归档核心逻辑

### 修改文件
- `.env.example` - 添加归档配置项
- `src/memos/api/start_api.py` - 添加后台归档任务
- `src/memos/graph_dbs/neo4j_community.py` - 添加 archive_expired 方法（可选）

## 关键 Cypher 查询

### 归档查询
```cypher
MATCH (n:Memory)
WHERE n.status = 'activated'
  AND n.created_at < datetime($cutoff)
  AND any(tag IN n.tags WHERE tag IN $archive_types)
SET n.status = 'archived',
    n.archived_at = datetime()
RETURN count(n) as archived_count
```

### 统计查询
```cypher
MATCH (n:Memory)
WHERE n.user_name = $user_name
RETURN n.status as status, count(n) as count
```

### 恢复查询
```cypher
MATCH (n:Memory {id: $memory_id})
WHERE n.status = 'archived'
SET n.status = 'activated',
    n.restored_at = datetime()
RETURN n
```

## 向量 DB 同步

归档时需要同步更新 Qdrant 中的 status 字段：
```python
# Qdrant payload update
self.vec_db.client.set_payload(
    collection_name=self.collection_name,
    payload={"status": "archived"},
    points=memory_ids,
)
```

## 验收标准

- [ ] PROGRESS 类型记忆 7 天后自动标记为 archived
- [ ] 搜索结果不包含 archived 记忆
- [ ] 归档可通过配置禁用
- [ ] 手动可触发归档
- [ ] 可查询归档统计
- [ ] 向量 DB 与 Neo4j 状态一致

## 风险和注意事项

1. **向后兼容**: 现有数据没有问题，status 默认 activated
2. **性能**: 大量记忆时归档查询可能较慢，需要索引
3. **恢复**: 需要提供恢复机制，避免误归档
4. **测试**: 需要单独测试归档逻辑，避免影响生产数据
