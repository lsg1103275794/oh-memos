# 后端接口与资源约定

架构见 [ARCHITECTURE.md](../../../ARCHITECTURE.md)，MCP 工具和部署见 [docs/MCP_GUIDE.md](../../../docs/MCP_GUIDE.md)。

## 目录

```
src/oh_memos/                Python API（本地入口 src/oh_memos/api/start_api.py）
mcp-server-node/src/         Node MCP server，所有客户端加载它；工具定义在 tools-registry.ts
project-memory/hooks/        hooks 的正本；oh-memos-deploy/ 里是同步出来的副本
tools/memory-admin/          独立的记忆管理界面，API 没启动也能用（memory-admin.bat）
scripts/local/               本机启停脚本（start.bat、stop.bat 等，部分只在本机、不进 Git）
mcp-server/                  已弃用的 Python 版 MCP，只留作参考
```

## 接口

- 本地 API 只启动 `start_api.py`。搜索是 `POST /search`，cube 用 `install_cube_ids`；图接口是 `/product/graph/data`、`/product/graph/trace_path`、`/product/graph/schema`（另有 `/graph/...` 别名）和 `/product/graph/relation`。
- **不要写 `/product/search`**：它只挂在 `product_api.py` / `server_api.py` 上，本地不启动。`readable_cube_ids`、`chat_history` 只属于 `server_api.py` 的 `APISearchRequest`；`enable_context_analysis` 在 `src/` 里没有声明。
- Pydantic 会静默丢弃模型上不存在的字段：传错字段不会报错，只会不生效。
- cube id 由 `project_path` 的最后一级目录推导（`mcp-server-node/src/keyword-enhancer.ts` 的 `detectCubeFromPath`）。hooks 各自带一份同样的规则，`hook-context.test.ts` 保证它们一致。

## MCP 工具 schema

- 改 `tools-registry.ts` 里的描述或参数后，要同时更新：`npm run schema:semantic:freeze`、`npm run schema:budget:freeze`，以及 `src/protocol-contract.test.ts` 的 `EXPECTED_SCHEMA_HASHES`。CI 会逐项检查。
- `MEMOS_ALWAYS_LOAD`（默认开）决定是否发送 server instructions、是否让 `memos_save` 和 `memos_search` 常驻；文字在 `server-instructions.ts`。

## 端口

- 18000：API，存着用户真实的记忆；测试和验证不要连。
- 18010：memory-admin 界面。
- 16333：Qdrant（Windows 本机；docker 里是 6333）。
- 7474 / 7687：Neo4j。
- 11434：Ollama，可选，当前配置不依赖它。
- 验证用的隔离实例用别的端口，数据目录放进任务目录。
