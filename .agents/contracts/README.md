# 契约目录

AGENTS.md 只放红线和本目录的入口。细则在这里，**按任务读对应的那一份，不用全读**。
改规则只改这里的文件；AGENTS.md 里不复述细则，避免两处不一致。

| 我要做的事 | 读这份 |
|---|---|
| 任何任务开工前，意图或目标不清楚时 | [common/skills.md](common/skills.md) |
| 读写项目记忆 | [common/memory.md](common/memory.md) |
| 找代码、查调用关系 | [common/code-search.md](common/code-search.md) |
| 写测试、跑验证、产生任何临时文件 | [common/artifacts.md](common/artifacts.md) |
| 模块做完、准备交付或合并 | [common/wrap-up.md](common/wrap-up.md) |
| 后端开发（API、MCP server、hooks、脚本） | [backend/skills.md](backend/skills.md)、[backend/interfaces.md](backend/interfaces.md) |

## 规则的优先级

1. 用户在当前对话里的明确要求。
2. AGENTS.md 的红线。
3. 本目录的契约。
4. 技能自己的默认做法。技能和契约冲突时以契约为准，例如技能要把文件存到别处，就按 [common/artifacts.md](common/artifacts.md) 改存位置。

## 维护

- 一份契约只管一件事。新增契约时在上表加一行，不要在别的契约里重复写同一条规则。
- 契约写「做什么、在哪里、谁来清」，不写某次任务的过程记录；过程和结论写进项目记忆或任务目录的 `REPORT.md`。
- 用户纠正了本项目的某个约定时，提议把它改进管它的那份契约，先给用户看改动，同意后再改。
