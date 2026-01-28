# Findings: MCP Server 优化调研

## Session: 2026-01-28

### 1. 重试逻辑重复模式分析

**出现位置**: memos_search, memos_save, memos_list/memos_list_v2, memos_get_stats

**典型模式**:
```python
response = await client.post(...)
if response.status_code == 200:
    data = response.json()
    if data.get("code") == 200:
        # 成功处理
    else:
        # Force re-register and retry
        _registered_cubes.discard(cube_id)
        if await ensure_cube_registered(client, cube_id, force=True):
            retry_response = await client.post(...)  # 重复调用
            if retry_response.status_code == 200:
                retry_data = retry_response.json()
                if retry_data.get("code") == 200:
                    # 成功处理（重复）
```

**优化方案**: 抽取为辅助函数
```python
async def api_call_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    cube_id: str,
    **kwargs
) -> tuple[bool, dict]:
    """Make API call with automatic cube re-registration on failure."""
    ...
```

---

### 2. `memos_get_graph` tree_text 解析 Bug

**问题代码** (line ~1324):
```python
for cube_data in text_mems:
    memories.extend(cube_data.get("memories", []))  # BUG!
```

**问题**: 在 tree_text 模式下，`memories` 字段是 `{"nodes": [...], "edges": [...]}` 字典，不是列表。
`extend()` 会把整个 dict 加入列表，后续 `mem.get("memory")` 拿不到数据。

**修复方案**:
```python
for cube_data in text_mems:
    mem_data = cube_data.get("memories", [])
    if isinstance(mem_data, dict) and "nodes" in mem_data:
        memories.extend(mem_data["nodes"])
    elif isinstance(mem_data, list):
        memories.extend(mem_data)
```

---

### 3. Neo4j 凭证硬编码

**问题位置**:
- `memos_trace_path` fallback: line ~1248-1249
- `memos_get_graph`: line ~1305-1306

**当前代码**:
```python
neo4j_url = "http://localhost:7474/db/neo4j/tx/commit"
neo4j_auth = ("neo4j", "12345678")
```

**修复方案**: 添加环境变量配置
```python
NEO4J_HTTP_URL = os.environ.get("NEO4J_HTTP_URL", "http://localhost:7474/db/neo4j/tx/commit")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "12345678")
```

---

### 4. httpx 客户端生命周期

**当前**: 每次 `call_tool()` 创建新客户端
```python
async with httpx.AsyncClient(timeout=MEMOS_TIMEOUT_TOOL) as client:
    # ...所有工具逻辑
```

**问题**: 无连接复用，高频调用时效率低

**方案选项**:
1. 模块级持久客户端 + server 关闭时清理
2. 使用 `httpx.Limits` 配置连接池

**推荐方案 1**: 简单改动
```python
_http_client: httpx.AsyncClient | None = None

async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=MEMOS_TIMEOUT_TOOL)
    return _http_client
```

---

### 5. `memos_get_stats` 重复统计代码

**问题**: 统计计算逻辑在正常路径和 retry 路径各写了一遍（~30 行 x 2）

**修复**: 抽取为辅助函数
```python
def compute_memory_stats(data: dict) -> tuple[dict, int]:
    """Compute memory type statistics from API response."""
    ...
```

---

### 6. 缺少 `top_k` 参数

**工具**: `memos_search`

**当前**: 无法控制返回结果数量

**修复**: 在 inputSchema 添加 `top_k` 参数
```python
"top_k": {
    "type": "integer",
    "description": "Maximum number of results to return",
    "default": 10
}
```

---

## 优化优先级

| Priority | Task | Impact | Effort |
|----------|------|--------|--------|
| P0 | 修复 tree_text 解析 bug | High (功能修复) | Low |
| P1 | 抽取重试逻辑 | High (代码质量) | Medium |
| P2 | Neo4j 配置改环境变量 | Medium (安全性) | Low |
| P2 | 添加 `top_k` 参数 | Low (功能增强) | Low |
| P3 | httpx 客户端复用 | Medium (性能) | Medium |
| P3 | 统计函数抽取 | Low (代码质量) | Low |
