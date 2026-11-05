# 后端技能契约

后端范围是 `src/oh_memos/`（Python API）、`mcp-server-node/`（MCP server）、`project-memory/hooks/`、`scripts/` 和 `tools/memory-admin/`。技能由 agent 按任务自己选，下表是统筹建议，不是强制清单。通用规则（意图不清先追问、TDD、调试、完成前验证）见 [../common/skills.md](../common/skills.md)。

## 按任务选技能

| 任务 | 首选 | 可以配合 |
|---|---|---|
| 新接口、新工具、新 hook | `tdd-workflow` | `backend-patterns`（接口设计）；动到模块边界时用 `codebase-design` |
| bug、测试失败、行为异常 | `systematic-debugging` | 偶发、性能、并发问题用 `diagnosing-bugs` |
| 检索质量、记忆提取结果「不对劲」 | `systematic-debugging`：一次只改一个变量，用客观指标加人工确认 | 需要的话先 `grilling` 对齐「用户看到的问题」到底是什么 |
| 处理用户输入、文件路径、外部进程参数 | `security-review` | 对外接口加固用 `api-security-hardener` |
| 大的重构、拆模块、找架构问题 | `improve-codebase-architecture` | `codebase-design` |
| 给 API 补测试 | `api-test-suite-generator` | — |
| 合并前 | `code-review`，再 `verification-before-completion` | — |

## 后端特有的验证要求

- **单元测试**，两套分开跑，环境变量和 CI 一致（`MEMOS_URL` 指向空端口，不连本机 18000）：
  - Node：在 `mcp-server-node/` 下设 `MEMOS_URL=http://127.0.0.1:1 MEMOS_USER=ci MEMOS_DEFAULT_CUBE=ci_cube MEMOS_CUBES_DIR=<runtime/scratch 下的目录>`，跑 `npm run build`、`npm test`。
  - Python：在仓库根跑 `pytest -q tests/ --ignore=tests/test_search_project.py --ignore=tests/test_graph_data.py -p no:cacheprovider`。
- **MCP 的 smoke 检查**：`npm run test:protocol`、`npm run test:lite-smoke`、`npm run schema:budget`、`npm run schema:semantic`、`npm run test:pack`。
- **hooks**：改完跑 `node scripts/sync-deploy-hooks.mjs --write` 和 `node scripts/lint-hook-matchers.mjs`。hook 只有 `hookSpecificOutput.additionalContext`（以及 SessionStart、UserPromptSubmit 的 stdout）能送进模型，其他输出只给用户看，细节见 [hooks README](../../../project-memory/hooks/README.md)。
- **真实验证**：单元测试通过不等于可用。
  - 改到 API、记忆提取用的 LLM、Qdrant 或 Neo4j 存储时，起一个隔离实例跑一遍（换端口，数据目录放进任务目录），不要用用户 18000 上的实例。
  - 改到 MCP 工具的行为或描述时，在真实客户端会话里确认工具能看到、调用结果对。
  - 能逐条对比的，和已验证的结果对比；证据放进任务目录（见 [../common/artifacts.md](../common/artifacts.md)）。
- 接口、端口、工具 schema 方面的约定见 [interfaces.md](interfaces.md)。

## 交付

- 最终报告写：改动文件、验证命令与输出、未完成项与已知限制，如实汇报，不夸大。
- 按 [../common/wrap-up.md](../common/wrap-up.md) 收尾，杀掉自己启动的进程，不留资源占用。
