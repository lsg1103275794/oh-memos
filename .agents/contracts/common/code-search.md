# 代码检索（jCodeMunch）

查调用关系、改动影响、某功能是否已有实现时，用 jCodeMunch MCP（`mcp__jcodemunch__order`）。已经知道名字或文件、范围又小时，内置的搜索和读文件同样可以，选步数少的。

| 要做的事 | action |
|---|---|
| 会话开始 | `resolve_repo`（传绝对路径）；没建索引时 `index_folder` |
| 一个具体任务的上下文 | `assemble_task_context` |
| 按名字找符号 | `search_symbols` |
| 文本、配置值、注释 | `search_text` |
| 谁在调用、改动影响多大 | `find_references`、`find_importers`、`get_blast_radius` |

- 改完文件后用 `register_edit` 登记改动路径。
- 文档、生成文件、命令输出和马上要编辑的文件可以直接读。
- 在 `runtime/worktrees/` 下的 worktree 里工作时，`resolve_repo` 会提示用主仓库的索引做只读查询；需要看分支里未提交的代码时再单独建索引。
