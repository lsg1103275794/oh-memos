# Project Memory 技能

<div align="center">

**Claude Code 智能项目记忆**

*让 AI 真正理解你的项目历史*

[![MemOS](https://img.shields.io/badge/Powered%20by-MemOS-blue)](https://github.com/MemTensor/MemOS)
[![Claude Code](https://img.shields.io/badge/For-Claude%20Code-orange)](https://claude.ai)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

---

## 安装方式

### 方式 1：从 MemOS 项目安装（推荐）

如果你已经在使用 MemOS 项目：

```bash
# 1. 复制 skill 到你的项目
cp -r /path/to/MemOS/.claude/skills/project-memory /your-project/.claude/skills/

# 2. 复制或创建 CLAUDE.md（可选但推荐）
cp /path/to/MemOS/CLAUDE.md /your-project/CLAUDE.md
# 然后修改 CLAUDE.md 中的项目特定配置
```

### 方式 2：独立安装

直接下载 skill：

```bash
# 1. 创建技能目录
mkdir -p ~/.claude/skills/project-memory

# 2. 复制文件
# 最少需要 SKILL.md
cp project-memory/SKILL.md ~/.claude/skills/project-memory/
```

---

## 与 CLAUDE.md 配合使用

### 为什么需要两个文件？

| 文件 | 职责 | 加载时机 |
|------|------|----------|
| `CLAUDE.md` | 项目配置兜底（~100行） | **每次对话开始** |
| `SKILL.md` | MCP 操作规则详解（~500行） | **使用 `/project-memory` 时** |

### 职责划分

**CLAUDE.md（项目根目录）**：
- 项目概述
- 核心记忆规则（简化版）
- 服务端口配置
- API Endpoints
- 指向 SKILL.md 的引用

**SKILL.md（.claude/skills/project-memory/）**：
- MUST/MUST NOT 强制规则
- 类型选择决策树
- 错误/正确示范
- 置信度机制
- 健康检查说明
- MCP 工具完整参考
- 触发规则表格
- Auto-Registration 说明

### 配置示例

```
your-project/
├── CLAUDE.md                           # 项目配置（每次加载）
└── .claude/
    └── skills/
        └── project-memory/
            └── SKILL.md                # 详细规则（按需加载）
```

**CLAUDE.md 核心内容**：

```markdown
# 你的项目名

保持中文交流

## 记忆系统 (核心规则)

**保存记忆时必须显式指定 `memory_type` 参数**

类型速查：
- Bug 修复 → `BUGFIX` 或 `ERROR_PATTERN`
- 技术决策 → `DECISION`
- 发现陷阱 → `GOTCHA`

**详细操作规则见 `/project-memory` skill**

## Project Configuration

### Memory Cube
- **Cube ID**: `your_project_cube`

### Service Ports
| Service | Port |
|---------|------|
| MemOS API | 18000 |
| Neo4j | 7474/7687 |
```

---

## 两种使用模式

### MCP 模式（推荐）

AI **主动** 使用记忆工具，无需手动调用：

```
用户：启动应用时出现 ConnectionRefusedError

AI：[自动搜索 ERROR_PATTERN...]
    找到匹配的错误模式！解决方案是...
```

**启用方式**：配置 MCP Server（见 MemOS 项目 README）

### Skill 模式

用户**手动**调用 `/project-memory`：

```
用户：/project-memory 搜索之前的错误解决方案

AI：[执行搜索...]
    找到 3 条相关记忆...
```

---

## 记忆类型

| 类型 | 用途 | 示例 |
|------|------|------|
| `ERROR_PATTERN` | 错误签名 + 解决方案 | ModuleNotFoundError 解决方案 |
| `BUGFIX` | 一次性 Bug 修复 | 修复了登录按钮无响应 |
| `DECISION` | 架构/设计决策 | 选择 PostgreSQL 而非 MySQL |
| `GOTCHA` | 坑点和注意事项 | Neo4j 需要 Java 17+ |
| `CODE_PATTERN` | 可复用代码模板 | 异步重试装饰器 |
| `MILESTONE` | 重要里程碑 | v1.0 发布完成 |
| `CONFIG` | 配置变更 | 更新了 Redis 超时设置 |
| `FEATURE` | 新功能实现 | 添加了用户认证模块 |
| `PROGRESS` | 纯进度更新（慎用） | 完成了 50% |

### 类型选择决策树

```
是否解决了一个错误/Bug？
├─ 是 → 是否有通用复用价值？
│       ├─ 是 → ERROR_PATTERN
│       └─ 否 → BUGFIX
└─ 否 → 是否做出了技术选择？
        ├─ 是 → DECISION
        └─ 否 → 是否发现了非显而易见的问题？
                ├─ 是 → GOTCHA
                └─ 否 → PROGRESS（仅限纯进度汇报）
```

---

## MCP 工具速查

| 工具 | 用途 | 示例 |
|------|------|------|
| `memos_search` | 搜索记忆 | `query: "ERROR_PATTERN 连接失败"` |
| `memos_save` | 保存记忆 | `content: "...", memory_type: "BUGFIX"` |
| `memos_list` | 列出记忆 | `cube_id: "dev_cube", limit: 10` |
| `memos_get_graph` | 查看关系图 | `query: "Neo4j"` |
| `memos_trace_path` | 追溯因果链 | `source_id: "...", target_id: "..."` |
| `memos_list_cubes` | 发现可用 cubes | `include_status: true` |

---

## 智能触发器

### 自动搜索

| 你说的话 | AI 自动执行 |
|----------|------------|
| "之前"、"上次" | 搜索历史记录 |
| "为什么"、"原因" | 搜索 DECISION |
| "错误"、"error" | 搜索 ERROR_PATTERN |
| "配置"、"config" | 搜索 CONFIG |

### 自动保存

| 场景 | 保存类型 |
|------|----------|
| 修复了 Bug | `ERROR_PATTERN` 或 `BUGFIX` |
| 做出决策 | `DECISION` |
| 完成任务 | `MILESTONE` |
| 发现坑点 | `GOTCHA` |

---

## 目录结构

```
project-memory/
├── SKILL.md                    # AI 行为指令（核心）
├── README.md                   # 英文文档
├── README_CN.md                # 本文件
├── LICENSE
└── hooks/                      # Claude Code Hooks
    └── README.md
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API 地址 |
| `MEMOS_USER` | `dev_user` | 默认用户 ID |
| `MEMOS_DEFAULT_CUBE` | `dev_cube` | 默认 Cube ID |
| `MEMOS_CUBES_DIR` | `G:/test/MemOS/data/memos_cubes` | Cube 存储目录 |

---

## 前置要求

- [MemOS](https://github.com/MemTensor/MemOS) 运行在 `localhost:18000`
- Neo4j Community Edition（可选，用于知识图谱）
- Qdrant（向量数据库）
- Claude Code CLI

---

## 常见问题

### Cube 找不到

```bash
# 使用 MCP 工具查看可用 cubes
memos_list_cubes()

# 手动注册
memos_register_cube(cube_id="your_cube")
```

### 记忆保存失败

1. 检查 MemOS API 是否运行：`curl http://localhost:18000/docs`
2. 检查 cube 是否已注册
3. 查看 SKILL.md 的 Troubleshooting 部分

### PROGRESS 类型过多

`memos_get_stats` 会在 PROGRESS 占比 >70% 时警告。解决方法：
1. 保存时显式指定 `memory_type`
2. 参考类型选择决策树

---

## 相关链接

- [MemOS](https://github.com/MemTensor/MemOS) - 记忆后端
- [Claude Code](https://claude.ai) - Anthropic CLI
- [MCP 配置指南](../docs/MCP_GUIDE.md) - MCP Server 配置

---

## 许可证

MIT License
