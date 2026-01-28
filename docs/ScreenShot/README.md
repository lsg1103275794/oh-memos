# 🎬 MemOS 项目截图库 (ScreenShot Gallery)

本目录存储了 MemOS 项目开发过程中的关键功能演示、系统架构以及调试过程的截图。

## 🖼️ 图片列表与标题

| 文件名 | 标题 (Title) | 描述 (Description) |
| :--- | :--- | :--- |
| `neo4j-Graph.png` | **Neo4j 知识图谱可视化** | 展示 MemOS 在 `tree_text` 模式下生成的记忆节点及其关联关系。 |
| `ScreenShot_2026-01-26_070316_014.png` | **MCP 服务启动与工具注册** | 展示 MCP Server 启动时自动加载的 8 个核心记忆管理工具。 |
| `ScreenShot_2026-01-26_070454_641.png` | **Claude Code 识别 MCP 工具** | AI 客户端成功连接并识别出 `memos_search` 等工具的日志。 |
| `ScreenShot_2026-01-26_070557_587.png` | **主动式记忆搜索 - 错误处理** | AI 在遇到运行错误时，自动触发 `ERROR_PATTERN` 记忆搜索。 |
| `ScreenShot_2026-01-26_071123_615.png` | **记忆保存 - 自动类型检测** | AI 完成任务后，自动识别并保存 `MILESTONE` 或 `BUGFIX` 类型记忆。 |
| `ScreenShot_2026-01-26_071137_624.png` | **记忆立方体 (MemCube) 自动初始化** | 演示 MCP Server 在无须手动干预的情况下自动创建和配置记忆存储路径。 |
| `ScreenShot_2026-01-26_071212_222.png` | **MCP 记忆搜索结果展示** | 展示 AI 检索到的历史决策、代码模式以及环境配置信息。 |
| `ScreenShot_2026-01-26_072404_067.png` | **跨项目记忆检索 (Part 1)** | 在项目 A (DDSP-SVC) 中向 AI 询问项目 B (MemOS) 的配置问题。 |
| `ScreenShot_2026-01-26_072809_934.png` | **跨项目记忆检索 (Part 2)** | AI 成功跨项目命中记忆，实现无感知的知识迁移。 |
| `ScreenShot_2026-01-28_091319_520.png` | **记忆删除同步优化 - 验证运行** | 运行 `verify_mems.py` 脚本验证删除操作在多数据库间的同步性。 |
| `ScreenShot_2026-01-28_091723_892.png` | **Qdrant 向量库删除确认** | 截图证实记忆删除后，Qdrant 向量索引已同步清除。 |
| `ScreenShot_2026-01-28_091739_975.png` | **Neo4j 节点删除确认** | 截图证实 Neo4j 中的图节点及关联边已通过 `DETACH DELETE` 物理移除。 |

---

*最后更新日期: 2026-01-28*
