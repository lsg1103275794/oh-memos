# MCP Server 配置指南 | MCP Server Configuration Guide

**让 Claude Code 主动调用记忆功能**

**Enable Claude Code to proactively use memory functions**

---

## 📖 Overview | 概述

MCP (Model Context Protocol) Server 允许 Claude Code **主动调用**记忆功能，而不是被动等待用户命令。

MCP Server enables Claude Code to **proactively invoke** memory functions, instead of passively waiting for user commands.

### 对比 | Comparison

| 模式 | 触发方式 | 适用场景 |
|------|----------|----------|
| **Skill (被动)** | 用户手动调用 `/project-memory` | 明确需要记忆操作时 |
| **MCP (主动)** | AI 自动判断并调用 | 遇到错误、做决策、完成任务时 |

| Mode | Trigger | Use Case |
|------|---------|----------|
| **Skill (Passive)** | User manually calls `/project-memory` | When explicitly needing memory operations |
| **MCP (Proactive)** | AI automatically decides and calls | When encountering errors, making decisions, completing tasks |

---

## 🚀 Quick Start | 快速开始

### 1. 安装依赖 | Install Dependencies

```bash
# 方式 1: 使用 pip 直接安装
pip install mcp httpx pydantic

# 方式 2: 使用项目 optional dependencies
pip install MemoryOS[mcp-server]

# 方式 3: 使用项目自带的 Python 环境
cd /path/to/MemOS
./conda_venv/python.exe -m pip install mcp httpx pydantic
```

### 2. 配置 Claude Code | Configure Claude Code

Claude Code 的 MCP 配置支持两种方式：
- **全局配置** (推荐) - 所有项目都能使用，存储在 `~/.claude.json` 的 `mcpServers` 字段
- **项目级别配置** - 仅特定项目使用，存储在 `~/.claude.json` 的 `projects` 字段中

Claude Code MCP configuration supports two approaches:
- **Global configuration** (Recommended) - Available to all projects, stored in `mcpServers` field
- **Project-level configuration** - Project-specific only, stored under `projects` field

**对比 | Comparison:**

| 特性 | 全局配置 | 项目级别配置 |
|------|---------|-------------|
| 可用范围 | ✅ 所有项目 | ⚠️ 仅配置的项目 |
| 配置位置 | 根级 `mcpServers` | `projects[path].mcpServers` |
| 配置次数 | 一次 | 每个项目一次 |
| 推荐用途 | 日常使用 | 特殊项目需求 |

| Feature | Global | Project-level |
|---------|--------|---|
| Availability | ✅ All projects | ⚠️ Configured projects only |
| Config location | Root `mcpServers` | `projects[path].mcpServers` |
| Setup effort | Once | Per project |
| Best for | Daily use | Special requirements |


#### 🌍 全局配置 (推荐) | Global Configuration (Recommended)

全局配置使所有项目都能使用 memos MCP，无需为每个项目单独配置。

Global configuration makes memos MCP available to all projects without per-project setup.

**编辑 `~/.claude.json`，在根级 `mcpServers` 添加 memos：**

**Edit `~/.claude.json`, add memos to root-level `mcpServers`:**

> ⚠️ 替换以下路径为你的实际 MemOS 安装路径 | Replace paths with your actual MemOS installation path

```json
{
  "mcpServers": {
    "memos": {
      "type": "stdio",
      "command": "/path/to/MemOS/conda_venv/python.exe",
      "args": [
        "/path/to/MemOS/mcp-server/memos_mcp_server.py"
      ],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "/path/to/MemOS/data/memos_cubes"
      }
    }
  }
}
```

**优势 | Advantages:**
- ✅ 一次配置，所有项目可用 | Configure once, available to all projects
- ✅ 简化项目配置 | Simplified project setup
- ✅ 便于更新和维护 | Easy to update and maintain

---

#### 项目级别配置 | Project-Level Configuration

如果只需在特定项目中使用 memos，可以配置项目级别。

Configure project-specific memos if only needed in certain projects.

**方法 1: 通过 Claude Code 界面添加**

1. 在 Claude Code 中按 `Esc` 打开菜单
2. 选择 "Manage MCP servers"
3. 添加新的 MCP server

**Method 1: Add via Claude Code UI**

1. Press `Esc` in Claude Code to open menu
2. Select "Manage MCP servers"
3. Add new MCP server

**方法 2: 手动编辑配置文件**

编辑 `~/.claude.json`，找到你的项目配置（如 `/your/project/path`），添加 memos MCP：

**Method 2: Manually edit configuration file**

Edit `~/.claude.json`, find your project config (e.g., `/your/project/path`), add memos MCP:

> ⚠️ 替换以下路径为你的实际配置 | Replace paths with your actual configuration

```json
{
  "projects": {
    "/your/project/path": {
      "mcpServers": {
        "memos": {
          "type": "stdio",
          "command": "/path/to/MemOS/conda_venv/python.exe",
          "args": [
            "/path/to/MemOS/mcp-server/memos_mcp_server.py"
          ],
          "env": {
            "MEMOS_URL": "http://localhost:18000",
            "MEMOS_USER": "dev_user",
            "MEMOS_DEFAULT_CUBE": "dev_cube",
            "MEMOS_CUBES_DIR": "/path/to/MemOS/data/memos_cubes"
          }
        }
      }
    }
  }
}
```


#### ⚠️ WSL 环境 | WSL Environment

在 WSL 环境中，由于 Windows Python 无法直接处理 WSL 路径格式，需要使用 **bash wrapper 脚本**。以下配置适用于**全局配置**和**项目级别配置**：

In WSL environment, Windows Python cannot handle WSL path format directly. Use a **bash wrapper script**. Configuration below works for both **global** and **project-level** setup:

> ⚠️ 替换以下路径为你的实际配置 | Replace paths with your actual configuration

```json
"mcpServers": {
  "memos": {
    "type": "stdio",
    "command": "bash",
    "args": [
      "/path/to/MemOS/mcp-server/run_mcp.sh"
    ],
    "env": {
      "MEMOS_URL": "http://localhost:18000",
      "MEMOS_USER": "dev_user",
      "MEMOS_DEFAULT_CUBE": "dev_cube",
      "MEMOS_CUBES_DIR": "/path/to/MemOS/data/memos_cubes"
    }
  }
}
```

**Wrapper 脚本** (`mcp-server/run_mcp.sh`) 内容：

> ⚠️ 替换路径为你的实际 MemOS 安装位置 | Replace paths with your actual MemOS location

```bash
#!/bin/bash
# MCP Server wrapper script for WSL environment

export MEMOS_URL="${MEMOS_URL:-http://localhost:18000}"
export MEMOS_USER="${MEMOS_USER:-dev_user}"
export MEMOS_DEFAULT_CUBE="${MEMOS_DEFAULT_CUBE:-dev_cube}"

# WSL path for Windows Python executable
# 替换 /path/to/MemOS 为你的实际路径 | Replace /path/to/MemOS with your path
PYTHON="/path/to/MemOS/conda_venv/python.exe"

# Windows-style path for the script (Windows Python needs this)
# 替换 /path/to/MemOS 为你的实际路径 | Replace /path/to/MemOS with your path
SCRIPT="/path/to/MemOS/mcp-server/memos_mcp_server.py"

exec "$PYTHON" "$SCRIPT" "$@"
```

**为什么需要 Wrapper?** / **Why wrapper is needed?**

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| WSL 路径 `/mnt/g/...` 传给 Windows Python | Windows Python 会错误转换为 `G:\mnt\g\...` | Wrapper 使用 Windows 格式路径 `G:/...` |
| Windows 路径 `G:/...` 在 Claude Code 命令中 | WSL bash 无法直接执行 Windows 路径 | 使用 bash 执行 wrapper 脚本 |

| Problem | Cause | Solution |
|---------|-------|----------|
| WSL path `/mnt/g/...` passed to Windows Python | Windows Python incorrectly converts to `G:\mnt\g\...` | Wrapper uses Windows format `G:/...` |
| Windows path `G:/...` in Claude Code command | WSL bash cannot execute Windows path directly | Use bash to execute wrapper script |

#### 纯 Windows 环境 (非 WSL) | Pure Windows (Not WSL)

对于纯 Windows 环境（非 WSL），可以直接使用完整路径。以下配置适用于**全局配置**和**项目级别配置**：

For pure Windows (not WSL), you can use direct paths. Configuration below works for both **global** and **project-level** setup:

> ⚠️ 替换以下路径为你的实际 MemOS 安装路径 | Replace paths with your actual MemOS installation path

```json
"mcpServers": {
  "memos": {
    "type": "stdio",
    "command": "/path/to/MemOS/conda_venv/python.exe",
    "args": [
      "/path/to/MemOS/mcp-server/memos_mcp_server.py"
    ],
    "env": {
      "MEMOS_URL": "http://localhost:18000",
      "MEMOS_USER": "dev_user",
      "MEMOS_DEFAULT_CUBE": "dev_cube",
      "MEMOS_CUBES_DIR": "/path/to/MemOS/data/memos_cubes"
    }
  }
}
```

**注意**: 配置文件位置
- 全局状态: `~/.claude.json`
- 项目设置: `~/.claude/settings.json` (部分设置)
- 项目本地: `.claude/settings.local.json` (权限等)

---

## 📋 真实世界示例 | Real-World Examples

### Windows 用户 - 全局配置示例

假设你的 MemOS 安装在 `G:\test\MemOS`：

```json
{
  "mcpServers": {
    "memos": {
      "type": "stdio",
      "command": "G:/test/MemOS/conda_venv/python.exe",
      "args": [
        "G:/test/MemOS/mcp-server/memos_mcp_server.py"
      ],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "G:/test/MemOS/data/memos_cubes"
      }
    }
  }
}
```

### macOS/Linux 用户 - 全局配置示例

假设你的 MemOS 安装在 `/home/user/projects/MemOS`：

```json
{
  "mcpServers": {
    "memos": {
      "type": "stdio",
      "command": "/home/user/projects/MemOS/conda_venv/bin/python",
      "args": [
        "/home/user/projects/MemOS/mcp-server/memos_mcp_server.py"
      ],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "/home/user/projects/MemOS/data/memos_cubes"
      }
    }
  }
}
```

### WSL 用户 - 全局配置示例

假设 MemOS 在 Windows 中位置为 `G:\test\MemOS`（对应 WSL 中的 `/mnt/g/test/MemOS`）：

```json
{
  "mcpServers": {
    "memos": {
      "type": "stdio",
      "command": "bash",
      "args": [
        "/mnt/g/test/MemOS/mcp-server/run_mcp.sh"
      ],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "G:/test/MemOS/data/memos_cubes"
      }
    }
  }
}
```

对应的 `run_mcp.sh`：

```bash
#!/bin/bash
export MEMOS_URL="${MEMOS_URL:-http://localhost:18000}"
export MEMOS_USER="${MEMOS_USER:-dev_user}"
export MEMOS_DEFAULT_CUBE="${MEMOS_DEFAULT_CUBE:-dev_cube}"

PYTHON="/mnt/g/test/MemOS/conda_venv/python.exe"
SCRIPT="G:/test/MemOS/mcp-server/memos_mcp_server.py"

exec "$PYTHON" "$SCRIPT" "$@"
```

---

### 3. 重启 Claude Code | Restart Claude Code

配置生效需要重启 Claude Code。

Restart Claude Code for changes to take effect.

### 4. 验证安装 | Verify Installation

重启后，Claude Code 将拥有以下工具：

After restart, Claude Code will have these tools:

- `memos_search` - 搜索记忆 | Search memories
- `memos_save` - 保存记忆 | Save memories
- `memos_list` - 列出记忆 | List memories
- `memos_suggest` - 智能建议 | Smart suggestions

---

## 🛠️ MCP Tools Reference | MCP 工具参考

### memos_search

搜索项目记忆，获取相关上下文。

Search project memories for relevant context.

**主动触发场景 | Proactive Triggers:**

| 场景 | 搜索内容 |
|------|----------|
| 遇到错误 | `ERROR_PATTERN {error_type}` |
| 用户说"之前/上次" | 相关历史 |
| 修改代码 | `GOTCHA`, `CODE_PATTERN` |
| 配置文件操作 | `CONFIG {filename}` |

**参数 | Parameters:**

```json
{
  "query": "搜索关键词",
  "cube_id": "dev_cube"  // 可选，默认使用环境变量
}
```

**示例 | Example:**

```
Claude 遇到 ModuleNotFoundError 时自动搜索:
→ memos_search("ERROR_PATTERN ModuleNotFoundError")
→ 返回之前解决类似问题的记录
```

---

### memos_save

保存重要信息到项目记忆。

Save important information to project memory.

**主动触发场景 | Proactive Triggers:**

| 场景 | 记忆类型 |
|------|----------|
| 解决 bug | `ERROR_PATTERN` |
| 做出决策 | `DECISION` |
| 完成任务 | `MILESTONE` |
| 发现陷阱 | `GOTCHA` |

**参数 | Parameters:**

```json
{
  "content": "记忆内容",
  "memory_type": "ERROR_PATTERN",  // 可选，自动检测
  "cube_id": "dev_cube"  // 可选
}
```

**记忆类型 | Memory Types:**

| Type | 用途 | Usage |
|------|------|-------|
| `ERROR_PATTERN` | 错误+解决方案 | Error + solution |
| `DECISION` | 架构/设计决策 | Architecture/design decision |
| `MILESTONE` | 重要里程碑 | Important milestone |
| `BUGFIX` | Bug 修复详情 | Bug fix details |
| `FEATURE` | 新功能 | New feature |
| `CONFIG` | 配置变更 | Configuration change |
| `CODE_PATTERN` | 可复用代码模式 | Reusable code pattern |
| `GOTCHA` | 非显而易见的陷阱 | Non-obvious pitfall |
| `PROGRESS` | 一般进度更新 | General progress |

---

### memos_list

列出项目中的所有记忆。

List all memories in a project.

**参数 | Parameters:**

```json
{
  "cube_id": "dev_cube",
  "limit": 10  // 最多返回数量
}
```

---

### memos_suggest

根据当前上下文获取智能搜索建议。

Get smart search suggestions based on current context.

**参数 | Parameters:**

```json
{
  "context": "ModuleNotFoundError: No module named 'uvicorn'"
}
```

**返回 | Returns:**

```
Suggested Searches:
1. ERROR_PATTERN ModuleNotFoundError
2. ERROR_PATTERN solution
```

---

## ⚙️ Environment Variables | 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API 地址 |
| `MEMOS_USER` | `dev_user` | 用户 ID |
| `MEMOS_DEFAULT_CUBE` | `dev_cube` | 默认记忆 Cube |
| `MEMOS_CUBES_DIR` | `G:/test/MemOS/data/memos_cubes` | Cube 存储目录 (用于自动注册) |

### 自动注册 Cube | Auto-Register Cube

MCP Server 会在首次使用时**自动注册** cube，无需手动创建。

MCP Server will **auto-register** cube on first use, no manual creation needed.

```
首次调用 memos_search/save/list
        ↓
检查 cube 是否已注册
        ↓ (未注册)
自动调用 /mem_cubes 注册
        ↓
继续执行原操作
```

---

## 🔍 How It Works | 工作原理

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code + MCP                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  用户输入 ──────────────────────────────────────────────────│
│      │                                                       │
│      ▼                                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Claude AI 分析上下文                      │   │
│  │                                                       │   │
│  │  检测到错误? ─────> 调用 memos_search(ERROR_PATTERN)  │   │
│  │  完成任务?   ─────> 调用 memos_save(MILESTONE)        │   │
│  │  需要历史?   ─────> 调用 memos_search(相关词)         │   │
│  │                                                       │   │
│  └────────────────────────┬─────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│                    MCP Server (memos)                        │
│                           │                                  │
│                           ▼                                  │
│                    MemOS API (:18000)                        │
│                           │                                  │
│               ┌───────────┴───────────┐                     │
│               ▼                       ▼                     │
│          Embedding              Vector DB                   │
│          (Ollama)               (Qdrant)                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 Testing | 测试

### 测试 MCP Server 连接

```bash
cd mcp-server
python test_server.py
```

预期输出:

```
✅ API is running
✅ Search works
✅ Memory type detection works
✅ All tests passed!
```

### 使用 MCP Inspector 测试

```bash
npx @anthropic-ai/mcp-inspector python memos_mcp_server.py
```

---

## 🐛 Troubleshooting | 故障排除

### MCP Server 启动失败 (WSL 环境)

**症状**: MCP 显示 `✘ failed`

**常见原因 & 解决方案**:

| 原因 | 症状 | 解决方案 |
|------|------|----------|
| WSL 路径传给 Windows Python | 路径变成 `G:\mnt\g\...` | 使用 bash wrapper 脚本 |
| Windows 路径在命令中 | bash 无法执行 `G:/...` | 使用 bash 调用 wrapper |
| 脚本换行符错误 | 执行失败 | 确保 `.sh` 是 Unix 格式 (LF) |

**推荐配置 (WSL)**:

```json
"memos": {
  "type": "stdio",
  "command": "bash",
  "args": ["/mnt/g/test/MemOS/mcp-server/run_mcp.sh"],
  "env": {...}
}
```

### MCP Server 未加载

**症状**: Claude Code 没有 memos_* 工具

**解决方案**:
1. 检查 `~/.claude.json` 中项目的 `mcpServers` 配置
2. 确保 Python 路径正确（Windows 用完整路径）
3. 重启 Claude Code

### API 连接失败

**症状**: `Cannot connect to MemOS API`

**解决方案**:
1. 确保 MemOS API 正在运行: `curl http://localhost:18000/users`
2. 检查 `MEMOS_URL` 环境变量
3. 检查防火墙设置

### Cube 未注册

**症状**: `User does not have access to cube`

**解决方案**:
MCP Server 会自动尝试注册 cube，如果失败：

```bash
curl -X POST http://localhost:18000/mem_cubes \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "dev_user",
    "mem_cube_name_or_path": "/path/to/cubes/dev_cube",
    "mem_cube_id": "dev_cube"
  }'
```

---

## 📚 Related Documentation | 相关文档

- [MemOS Deployment Guide](DEPLOY_EN.md) - 完整部署指南
- [Project Memory Skill](../project-memory/README.md) - Skill 使用说明
- [Changelog](CHANGELOG.md) - 更新日志

---

## 🔮 Future Enhancements | 未来增强

- [ ] 自动检测项目切换，切换 cube
- [ ] Hooks 集成，在特定事件时自动触发
- [ ] 记忆相关性评分优化
- [ ] 多 cube 跨项目搜索

---

<div align="center">

**Proactive Memory for AI Assistants** 🧠

*让 AI 主动记忆*

</div>
