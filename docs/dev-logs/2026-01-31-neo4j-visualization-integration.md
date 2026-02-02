# 开发日志：Neo4j 知识图谱可视化集成 (Openwork Desktop)

**日期：** 2026-01-31
**版本：** v1.0.0
**状态：** 已完成

## 1. 任务背景
在 `ddsp-svc-6.3` 等复杂 AI 工作流中，用户需要直观地查看 MemOS 中存储的记忆节点及其关系。本项目旨在将 MemOS 的 Neo4j 图数据通过 IPC 通道引入 Openwork 桌面端，并实现交互式可视化。

## 2. 关键变更

### 后端服务 (Electron Main Process)
- **文件：** `src/main/services/memory.ts`
  - 新增 `getGraphData(projectId, page, pageSize)` 函数。
  - 对接 MemOS API `/product/graph/data`。
  - 实现了基于 `projectId` 的过滤逻辑。
- **文件：** `src/main/ipc/handlers.ts`
  - 注册 `memory:get-graph-data` IPC 句柄。
  - 引入 `sanitizeString` 增强输入安全性。

### 渲染进程集成 (Electron Renderer)
- **文件：** `src/preload/index.ts`
  - 通过 `contextBridge` 将 `getGraphData` 暴露给前端。
- **依赖：** 安装了 `react-force-graph-2d` 和 `d3`。
- **组件：** `src/renderer/components/memory/KnowledgeGraph.tsx`
  - 实现基于 Canvas 的高性能力导向图。
  - 根据 `memory_type`（LongTermMemory, WorkingMemory 等）进行颜色区分。
  - 支持节点悬停显示详细记忆内容。
- **集成：** `src/renderer/pages/Execution.tsx`
  - 在执行页面增加“知识图谱”切换按钮。
  - 默认针对 `ddsp-svc-6.3` 项目进行展示。

## 3. 遇到的问题与解决方案
- **依赖编译错误：** 在 Windows 环境下 `pnpm add` 触发 `electron-rebuild` 失败（由于缺少 VS 构建工具）。
  - **对策：** 使用 `--ignore-scripts` 绕过脚本执行，手动管理依赖。
- **IPC 插入点定位：** `handlers.ts` 文件较大，初次搜索失败。
  - **对策：** 通过分段读取文件确定了 `memory:clear-api-key` 后的安全插入位置。

## 4. 后续规划
- 增加节点搜索功能。
- 支持直接在图谱中点击节点编辑记忆。
- 增加路径追踪 (`trace_path`) 的可视化展示。
