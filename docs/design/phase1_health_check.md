# Phase 1: 健康检查端点详细设计

## 概述

为 MemOS API 添加健康检查端点，用于监控系统各组件的运行状态。

## API 设计

### 1. `GET /health` - 简单健康检查

**用途**: k8s liveness/readiness probe、负载均衡器健康检查

**响应 Schema**:
```python
class HealthStatus(BaseModel):
    status: Literal["ok", "degraded", "down"]
    timestamp: str  # ISO 8601

class HealthResponse(BaseResponse[HealthStatus]):
    pass
```

**状态判定逻辑**:
- `ok`: 所有核心组件正常
- `degraded`: 部分非核心组件异常（如 Ollama）
- `down`: 核心组件（Neo4j 或 Qdrant）异常

**示例响应**:
```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "status": "ok",
    "timestamp": "2026-02-05T10:30:00Z"
  }
}
```

### 2. `GET /health/detail` - 详细健康检查

**用途**: 运维监控、问题排查

**响应 Schema**:
```python
class ComponentHealth(BaseModel):
    status: Literal["ok", "error", "unavailable"]
    latency_ms: float | None = None
    error: str | None = None
    version: str | None = None  # 可选

class HealthDetailData(BaseModel):
    overall_status: Literal["ok", "degraded", "down"]
    timestamp: str
    uptime_seconds: float
    components: dict[str, ComponentHealth]

class HealthDetailResponse(BaseResponse[HealthDetailData]):
    pass
```

**示例响应**:
```json
{
  "code": 200,
  "message": "All systems operational",
  "data": {
    "overall_status": "ok",
    "timestamp": "2026-02-05T10:30:00Z",
    "uptime_seconds": 3600.5,
    "components": {
      "neo4j": {
        "status": "ok",
        "latency_ms": 12.3
      },
      "qdrant": {
        "status": "ok",
        "latency_ms": 5.1
      },
      "redis": {
        "status": "ok",
        "latency_ms": 1.2
      },
      "ollama": {
        "status": "unavailable",
        "error": "Connection refused"
      }
    }
  }
}
```

## 组件检查实现

### Neo4j 检查
```python
def check_neo4j(graph_db) -> ComponentHealth:
    """执行简单 Cypher 查询测试连接"""
    start = time.perf_counter()
    try:
        # 使用 driver.verify_connectivity() 或简单查询
        with graph_db.driver.session() as session:
            session.run("RETURN 1").single()
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(status="ok", latency_ms=latency)
    except Exception as e:
        return ComponentHealth(status="error", error=str(e))
```

### Qdrant 检查
```python
def check_qdrant(vector_db) -> ComponentHealth:
    """获取集合信息测试连接"""
    start = time.perf_counter()
    try:
        # Qdrant client 有 get_collections() 方法
        vector_db.client.get_collections()
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(status="ok", latency_ms=latency)
    except Exception as e:
        return ComponentHealth(status="error", error=str(e))
```

### Redis 检查
```python
def check_redis(redis_client) -> ComponentHealth:
    """使用 PING 命令测试"""
    start = time.perf_counter()
    try:
        redis_client.ping()
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(status="ok", latency_ms=latency)
    except Exception as e:
        return ComponentHealth(status="error", error=str(e))
```

### Ollama 检查 (可选)
```python
def check_ollama(llm) -> ComponentHealth:
    """调用 list models 测试"""
    if not hasattr(llm, 'client'):
        return ComponentHealth(status="unavailable", error="Not configured")
    start = time.perf_counter()
    try:
        llm.client.list()
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(status="ok", latency_ms=latency)
    except Exception as e:
        return ComponentHealth(status="error", error=str(e))
```

## 文件变更计划

### 1. 新增文件
- `src/memos/api/handlers/health_handler.py` - 健康检查处理器

### 2. 修改文件
- `src/memos/api/product_models.py` - 添加响应模型
- `src/memos/api/routers/server_router.py` - 添加路由端点

### 3. 可选：MCP 集成
- `mcp-server/api_client.py` - 将 `wait_for_api_ready()` 改用 `/health` 端点

## 实现细节

### health_handler.py 结构
```python
"""Health check handler for MemOS API."""

import time
from datetime import datetime, timezone
from typing import Literal

from memos.api.handlers.base_handler import BaseHandler, HandlerDependencies
from memos.api.product_models import (
    ComponentHealth,
    HealthDetailData,
    HealthDetailResponse,
    HealthResponse,
    HealthStatus,
)
from memos.log import get_logger

logger = get_logger(__name__)

# 服务启动时间，用于计算 uptime
_start_time = time.time()


class HealthHandler(BaseHandler):
    """Handler for health check endpoints."""

    # 核心组件（任一失败 = down）
    CRITICAL_COMPONENTS = {"neo4j", "qdrant"}

    def __init__(self, dependencies: HandlerDependencies, redis_client=None, llm=None):
        super().__init__(dependencies)
        self.redis_client = redis_client
        self.llm = llm

    def handle_health(self) -> HealthResponse:
        """简单健康检查 - 快速返回"""
        components = self._check_all_components()
        overall = self._compute_overall_status(components)

        return HealthResponse(
            code=200,
            message=overall,
            data=HealthStatus(
                status=overall,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        )

    def handle_health_detail(self) -> HealthDetailResponse:
        """详细健康检查"""
        components = self._check_all_components()
        overall = self._compute_overall_status(components)

        return HealthDetailResponse(
            code=200,
            message=self._get_status_message(overall),
            data=HealthDetailData(
                overall_status=overall,
                timestamp=datetime.now(timezone.utc).isoformat(),
                uptime_seconds=time.time() - _start_time,
                components=components,
            ),
        )

    def _check_all_components(self) -> dict[str, ComponentHealth]:
        """检查所有组件"""
        return {
            "neo4j": self._check_neo4j(),
            "qdrant": self._check_qdrant(),
            "redis": self._check_redis(),
            "ollama": self._check_ollama(),
        }

    def _compute_overall_status(
        self, components: dict[str, ComponentHealth]
    ) -> Literal["ok", "degraded", "down"]:
        """计算总体状态"""
        critical_ok = all(
            components.get(c, ComponentHealth(status="error")).status == "ok"
            for c in self.CRITICAL_COMPONENTS
        )
        all_ok = all(c.status == "ok" for c in components.values())

        if not critical_ok:
            return "down"
        elif not all_ok:
            return "degraded"
        return "ok"

    def _get_status_message(self, status: str) -> str:
        return {
            "ok": "All systems operational",
            "degraded": "Some non-critical components unavailable",
            "down": "Critical components unavailable",
        }.get(status, "Unknown status")

    def _check_neo4j(self) -> ComponentHealth:
        # ... 实现略
        pass

    def _check_qdrant(self) -> ComponentHealth:
        # ... 实现略
        pass

    def _check_redis(self) -> ComponentHealth:
        # ... 实现略
        pass

    def _check_ollama(self) -> ComponentHealth:
        # ... 实现略
        pass
```

### server_router.py 添加路由
```python
# 在文件顶部 imports 添加
from memos.api.handlers.health_handler import HealthHandler
from memos.api.product_models import HealthResponse, HealthDetailResponse

# 初始化 handler（在其他 handler 初始化之后）
health_handler = HealthHandler(
    dependencies,
    redis_client=redis_client,
    llm=llm,
)

# 添加端点（放在文件开头，其他端点之前）
@router.get("/health", summary="Health check", response_model=HealthResponse)
def health_check():
    """Simple health check for load balancers and k8s probes."""
    return health_handler.handle_health()


@router.get("/health/detail", summary="Detailed health check", response_model=HealthDetailResponse)
def health_check_detail():
    """Detailed health check showing all component statuses."""
    return health_handler.handle_health_detail()
```

## 配置选项

可添加到 `.env`：
```bash
# 健康检查超时（毫秒）
HEALTH_CHECK_TIMEOUT_MS=5000

# 是否检查 Ollama（可选组件）
HEALTH_CHECK_OLLAMA=true
```

## 测试计划

### 单元测试
1. `test_health_all_ok` - 所有组件正常 → status=ok
2. `test_health_degraded` - Ollama 异常 → status=degraded
3. `test_health_down` - Neo4j 异常 → status=down
4. `test_health_latency` - 验证 latency_ms 正确计算

### 集成测试
1. 启动服务后调用 `/health` 返回 200
2. 停止 Neo4j 后调用 `/health` 返回 down
3. 验证 `/health/detail` 返回完整组件信息

## 注意事项

1. **无认证**: 健康检查端点不需要认证，便于监控系统调用
2. **超时控制**: 每个组件检查应有独立超时（建议 5s）
3. **缓存**: 可选添加短期缓存（1-5s）避免频繁检查
4. **错误隔离**: 单个组件检查失败不应影响其他组件
5. **向后兼容**: 现有的 `GET /users` 探针可继续工作

## 依赖关系

```
HealthHandler
├── graph_db (Neo4j) - 来自 HandlerDependencies
├── vector_db (Qdrant) - 来自 HandlerDependencies
├── redis_client - 需要单独传入
└── llm (Ollama) - 需要单独传入
```

## 验收标准

- [ ] `GET /health` 返回 200 + status
- [ ] `GET /health/detail` 返回所有组件状态
- [ ] Neo4j 不可用时 status=down
- [ ] Qdrant 不可用时 status=down
- [ ] Ollama 不可用时 status=degraded（不是 down）
- [ ] 响应时间 < 5s（正常情况 < 100ms）
- [ ] FastAPI docs 自动生成 schema
