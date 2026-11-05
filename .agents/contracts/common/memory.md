# 项目记忆（oh-memos）

记忆通过 oh-memos MCP 读写，规则来自 `project-memory` 技能。**不要手动建记忆目录或文件。** 记忆服务不可用时，仓库里的 Markdown 仍是事实依据。

## 三件事

1. **开工前查**：复杂问题或新功能动手前，用 `memos_search` 查相关记忆；上下文被压缩后用 `memos_context_resume` 恢复。
2. **做完存**：修好 bug、做出决策、踩到坑、完成功能时，用 `memos_save` 存一条。
3. **两个参数必传**：
   - `project_path="G:/test/oh-memos"`（WSL 下是 `/mnt/g/test/oh-memos`）：记忆进本项目自己的 cube `oh_memos_cube`，不要写死 `cube_id`。
   - `memory_type`：按下表选，不要默认 `PROGRESS`。

| 发生了什么 | memory_type |
|---|---|
| 修好 bug（可复用的写成模式） | `BUGFIX`（`ERROR_PATTERN`） |
| 做了技术选择 | `DECISION` |
| 发现不明显的坑 | `GOTCHA` |
| 新增功能 / 完成里程碑 | `FEATURE` / `MILESTONE` |
| 改了配置 | `CONFIG` |
| 可复用的代码模板 | `CODE_PATTERN` |
| 只是进度 | `PROGRESS` |

内容写清楚：改了哪些文件、为什么、怎么验证的、还有什么限制。提交号要在提交之后从 `git log` 读出来再写；没有提交就写「未提交」，不要预填。其他工具的用法见 `project-memory` 技能。

本仓库开发的就是 oh-memos 本身：记忆工具表现不对（搜不到刚存的、保存报错）时，先当作本项目的 bug 来查，不要绕开。
