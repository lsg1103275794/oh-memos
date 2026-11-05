# 测试产物路径

测试和验证产生的文件只能写进下表的位置。不得新建其他 `runtime/` 顶层目录，也不得写到项目之外（系统临时目录 `%TEMP%` / `/tmp`、用户目录、工作区根）。

| 用途 | 位置 | 谁来清 |
|---|---|---|
| Node 测试和 smoke 脚本的临时文件 | `runtime/scratch/node/`，统一用 `mcp-server-node/scripts/_scratch.mjs` 的 `scratchDir(前缀)`；`scratch-contract.test.ts` 会拦住新的 `os.tmpdir()` | 调用者自己删；崩溃留下的超过一天由下次运行清掉 |
| pytest 临时文件 | `runtime/scratch/pytest/<pid>/`，由 `tests/conftest.py` 自动设置 | 全绿时会话结束自动删除。失败的保留现场，一天后由下一次会话清掉。手动传 `--basetemp` 时由调用者自己管 |
| 一个任务的验证、诊断、调研 | `runtime/<task>-<yyyymmdd>/`，一个任务一个目录，入口是 `REPORT.md`；长任务边做边写 `PROGRESS.md` | 任务结束时按 [wrap-up.md](wrap-up.md) 处理 |
| 隔离的 git worktree | `runtime/worktrees/<分支名>/`，不要建在仓库外 | 分支合并后 `git worktree remove`、`git branch -d` |

## 必须保留的应用目录

不归测试管，不许清：`data/`（用户的 cube、canvas、访问统计）、`logs/`（服务日志）、仓库根的 `.env`。

## 契约之前留下的目录

`.claude/worktrees/agent-*`：其他会话的 worktree 和分支。它们不归当前任务所有，不要因为不合契约就删；要清理先问用户。

`runtime/scratch/` 里不允许留下文件；空的子目录可以保留。`runtime/` 不进 Git。
