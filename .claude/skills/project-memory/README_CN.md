# 项目记忆技能 (Project Memory Skill)

基于 [MemOS](https://github.com/MemTech/MemOS) 的 Claude Code 项目记忆管理技能，让 AI 能够主动记忆和回忆项目信息。

## 概述

此技能使 AI 能够在对话之间自动记住和回忆项目特定信息。它与 MemOS API 集成，提供持久化、可搜索的记忆存储。

## 功能特点

- **自动创建记忆**：AI 主动保存重要的里程碑、bug 修复、决策和踩坑记录
- **上下文感知搜索**：在开始项目工作前搜索相关记忆
- **进度追踪**：将当前状态与历史记录进行比较
- **项目隔离**：每个项目有独立的记忆库
- **跨平台支持**：支持 Linux、macOS 和 Windows

## 目录结构

```
project-memory/
├── SKILL.md                           # AI 技能指令
├── README.md                          # 英文文档
├── README_CN.md                       # 中文文档
├── references/
│   └── examples.md                    # 记忆内容示例
└── scripts/
    ├── memos_init_project.py          # 核心 Python 脚本
    ├── memos_save.py
    ├── memos_search.py
    ├── linux/                         # Linux/macOS
    │   ├── install.sh                 # 安装脚本
    │   ├── memos-init.sh
    │   ├── memos-save.sh
    │   └── memos-search.sh
    └── windows/                       # Windows
        ├── install.cmd                # CMD 安装脚本
        ├── install.ps1                # PowerShell 安装脚本
        ├── memos-init.cmd
        ├── memos-save.cmd
        └── memos-search.cmd
```

## 前置要求

- [MemOS](https://github.com/MemTech/MemOS) 服务运行在 `http://localhost:18000`
- Python 3.8+
- （可选）自定义配置的环境变量

## 快速开始

### 安装

| 平台 | 命令 |
|------|------|
| Linux/macOS | `bash ~/.claude/skills/project-memory/scripts/linux/install.sh` |
| Windows CMD | `%USERPROFILE%\.claude\skills\project-memory\scripts\windows\install.cmd` |
| Windows PowerShell | `& "$env:USERPROFILE\.claude\skills\project-memory\scripts\windows\install.ps1"` |

### 安装后可用命令

| 命令 | 描述 |
|------|------|
| `memos-init` | 初始化项目记忆库 |
| `memos-save "内容" -t 类型` | 保存记忆 |
| `memos-search "关键词"` | 搜索记忆 |

## 详细安装说明

技能位于 Claude Code 的技能目录：

```
~/.claude/skills/project-memory/
```

### Linux / macOS

```bash
# 运行安装脚本
bash ~/.claude/skills/project-memory/scripts/linux/install.sh

# 或手动添加到 ~/.bashrc 或 ~/.zshrc:
export PATH="$HOME/.local/bin:$PATH"
```

安装后可使用：
```bash
memos-init                           # 初始化项目
memos-save "内容" -t MILESTONE       # 保存记忆
memos-search "关键词"                # 搜索记忆
```

### Windows (CMD 命令提示符)

```cmd
REM 运行安装脚本
%USERPROFILE%\.claude\skills\project-memory\scripts\windows\install.cmd
```

### Windows (PowerShell)

```powershell
# 运行安装脚本（可能需要先执行: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned）
& "$env:USERPROFILE\.claude\skills\project-memory\scripts\windows\install.ps1"
```

安装后重启终端即可使用。

## 使用方式

### 自动模式（推荐）

AI 会在以下情况自动使用此技能：

1. **开始项目工作时** - 搜索现有记忆
2. **完成任务时** - 保存里程碑和进度
3. **修复 bug 时** - 记录问题和解决方案
4. **做出决策时** - 记录决策理由

### 手动命令

初始化新项目记忆库：
```bash
memos-init
# 或
python3 ~/.claude/skills/project-memory/scripts/memos_init_project.py
```

保存记忆：
```bash
memos-save "你的记忆内容" -t MILESTONE --tags feature release
# 或
python3 ~/.claude/skills/project-memory/scripts/memos_save.py "内容" -t MILESTONE
```

搜索记忆：
```bash
memos-search "搜索关键词"
# 或
python3 ~/.claude/skills/project-memory/scripts/memos_search.py "关键词"
```

## 记忆类型

| 类型 | 描述 | 使用场景 |
|------|------|----------|
| `MILESTONE` | 重要里程碑 | 功能完成、版本发布 |
| `BUGFIX` | Bug 修复 | 问题原因和解决方案 |
| `FEATURE` | 新功能 | 功能实现细节 |
| `DECISION` | 设计决策 | 架构决策及理由 |
| `GOTCHA` | 踩坑记录 | 非显而易见的问题 |
| `CONFIG` | 配置变更 | 环境/设置修改 |
| `PROGRESS` | 进度更新 | 工作进度检查点 |

## 记忆格式

```
[类型] Project: 项目名称 | Date: YYYY-MM-DD

## Summary
简要描述

## Context
为什么需要这个

## Details
具体变更、代码片段、文件路径

## Outcome
结果和后续步骤

Tags: 标签1, 标签2, 标签3
```

## 脚本参考

### memos_init_project.py

初始化新项目记忆库，创建正确的配置。

```bash
memos-init [-p 项目名] [-u 用户ID]
```

参数：
- `-p, --project`：项目名称（从 git 自动检测）
- `-u, --user`：用户 ID（默认：dev_user）

### memos_save.py

保存格式化的记忆到 MemOS。

```bash
memos-save 内容 [-t 类型] [-p 项目名] [--tags 标签...]
```

参数：
- `-t, --type`：记忆类型（MILESTONE, BUGFIX, FEATURE 等）
- `-p, --project`：项目名称
- `--tags`：用于搜索的额外标签

### memos_search.py

搜索记忆并格式化输出。

```bash
memos-search 查询词 [-p 项目名] [--all] [--json]
```

参数：
- `-p, --project`：在特定项目中搜索
- `--all`：搜索所有项目
- `--json`：输出原始 JSON

## 环境变量

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API 地址 |
| `MEMOS_USER` | `dev_user` | 默认用户 ID |
| `MEMOS_CUBES_DIR` | `~/.memos_cubes` | 记忆库配置目录 |

## 使用的 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/mem_cubes` | POST | 注册记忆库 |
| `/memories` | POST | 保存记忆 |
| `/memories` | GET | 获取所有记忆 |
| `/search` | POST | 搜索记忆 |

## 工作流程示例

1. **开始项目工作**
   ```
   AI: 正在搜索 "my-project" 的现有记忆...
   找到 3 条记忆：认证系统完成、限流已实现...
   ```

2. **完成一个功能**
   ```
   AI: 保存里程碑 - "用户仪表板已实现，支持实时更新"
   记忆保存成功。
   ```

3. **调试问题**
   ```
   AI: 搜索类似问题...
   找到相关记忆："连接池竞态条件 - 使用互斥锁解决"
   ```

4. **稍后恢复工作**
   ```
   AI: 获取项目上下文...
   上次进度："数据库迁移完成 50%"
   下一步：完成订单表结构
   ```

## AI 自主行为说明

根据 SKILL.md 的配置，AI 会在以下场景**主动**使用此技能，无需用户提示：

### 主动搜索场景
- 开始处理项目代码前
- 调试问题时查找类似历史问题
- 用户询问项目进度或历史

### 主动保存场景
- 完成重要功能后
- 解决复杂 bug 后
- 做出架构决策时
- 发现踩坑点时
- 修改重要配置后

### 进度比对
当用户询问"我们做到哪了"、"项目进度"等问题时，AI 会：
1. 搜索所有 MILESTONE 和 PROGRESS 类型记忆
2. 对比当前 git 状态
3. 综合分析已完成和待完成的工作

## 相关项目

- [MemOS](https://github.com/MemTech/MemOS) - 记忆操作系统后端
- [Claude Code](https://claude.ai/claude-code) - Anthropic 的 Claude CLI 工具

## 许可证

MIT License
