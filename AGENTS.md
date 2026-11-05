# oh-memos · 代理须知

oh-memos 给 AI 编程助手提供跨会话的项目记忆：Python API（`src/oh_memos/`）加 Node MCP server（`mcp-server-node/`）。**全程用中文交流。**

## 红线（任何任务都适用）

- **本机 18000 端口上的 API 存着用户真实的记忆。** 测试和验证不要连它：`MEMOS_URL` 用 `http://127.0.0.1:1`，或用 Lite 模式。不要停止或重启用户的实例。
- `data/`、`logs/`、`.env` 是用户的数据和本机配置：不删、不清、不提交。
- 仓库外的文件（`~/.claude`、Codex 的配置目录等）改之前先给用户看改动，同意后再改，改之前先备份。
- `oh-memos-deploy/` 里的 hooks 由 `node scripts/sync-deploy-hooks.mjs --write` 从 `project-memory/hooks/` 生成，不要手改。
- `mcp-server/`（Python 版 MCP）已弃用，不再加功能；所有客户端加载的是 `mcp-server-node/`。
- 仓库和 npm 包是公开的：推送、打 tag、发版之前先问用户。
- 如实汇报，不夸大：写清改动文件、验证命令与输出、未完成项与已知限制。

## 细则：按任务读契约

所有细则在 [`.agents/contracts/`](.agents/contracts/README.md)，按任务只读需要的那份：

| 任务 | 契约 |
|---|---|
| 意图不清、该用哪些技能 | [common/skills.md](.agents/contracts/common/skills.md) |
| 项目记忆 | [common/memory.md](.agents/contracts/common/memory.md) |
| 代码检索 | [common/code-search.md](.agents/contracts/common/code-search.md) |
| 测试和验证文件放哪 | [common/artifacts.md](.agents/contracts/common/artifacts.md) |
| 模块做完怎么收尾 | [common/wrap-up.md](.agents/contracts/common/wrap-up.md) |
| 后端：技能、测试、验证 | [backend/skills.md](.agents/contracts/backend/skills.md) |
| 后端：接口、端口、工具 schema | [backend/interfaces.md](.agents/contracts/backend/interfaces.md) |

项目文档入口是 [README.md](README.md)，架构见 [ARCHITECTURE.md](ARCHITECTURE.md)，hooks 见 [project-memory/hooks/README.md](project-memory/hooks/README.md)。
