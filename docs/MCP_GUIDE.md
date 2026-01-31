# MCP Server 配置指南 | MCP Server Configuration Guide

> ⚠️ **重要提示 | IMPORTANT**:
> 本文档中的所有路径（如 `G:/test/MemOS`）均为**示例路径**。在实际配置时，请务必将其替换为您电脑上 MemOSLocal-SM 项目的**具体部署路径**。
> All paths in this document (e.g., `G:/test/MemOS`) are **example paths**. Please replace them with the **actual deployment path** of MemOS on your machine.

---

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

## 🚀 各平台配置示例 | Platform Configuration Examples

根据你使用的平台，选择对应的配置文件进行设置。以下示例均以当前项目路径 `G:/test/MemOS` 为准。

### 1. Claude Code (CLI)

**配置文件**: `~/.claude.json`

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
        "MEMOS_CUBES_DIR": "G:/test/MemOS/data/memos_cubes",
        "MEMOS_TIMEOUT_TOOL": "120.0",
        "MEMOS_TIMEOUT_STARTUP": "30.0",
        "MEMOS_TIMEOUT_HEALTH": "5.0",
        "MEMOS_API_WAIT_MAX": "60.0",
        "MEMOS_ENABLE_DELETE": "false"
      },
      "alwaysAllow": [
        "memos_search",
        "memos_save",
        "memos_list",
        "memos_suggest",
        "memos_get_graph",
        "memos_get_stats",
        "memos_trace_path",
        "memos_search_context",
        "memos_export_schema"
      ]
    }
  }
}
```

### 2. Trae (IDE)

**配置路径**: `设置 (Settings)` -> `AI` -> `MCP` -> `Add Server`

- **Name**: `memos`
- **Type**: `command`
- **Command**: `G:/test/MemOS/conda_venv/python.exe G:/test/MemOS/mcp-server/memos_mcp_server.py`
- **Env Vars**:
  - `MEMOS_URL`: `http://localhost:18000`
  - `MEMOS_USER`: `dev_user`
  - `MEMOS_DEFAULT_CUBE`: `dev_cube`
  - `MEMOS_CUBES_DIR`: `G:/test/MemOS/data/memos_cubes`

### 3. Cursor (IDE)

**配置路径**: `Settings` -> `Features` -> `MCP` -> `+ Add Server`

- **Name**: `memos`
- **Type**: `stdio`
- **Command**: `G:/test/MemOS/conda_venv/python.exe G:/test/MemOS/mcp-server/memos_mcp_server.py`

> 注意：Cursor 目前主要通过命令行参数传递环境变量，或在启动 Cursor 的 shell 中预设。

### 4. Claude Desktop

**配置文件**: 
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "memos": {
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

### 5. Windsurf (IDE)

**配置文件**: `~/.codeium/windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "memos": {
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

### 6. Cline / Roo Code (VS Code Extensions)

**配置路径**: 点击插件图标 -> `Settings (齿轮)` -> `MCP Servers` -> `Edit Config`

```json
{
  "mcpServers": {
    "memos": {
      "command": "G:/test/MemOS/conda_venv/python.exe",
      "args": [
        "G:/test/MemOS/mcp-server/memos_mcp_server.py"
      ],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "G:/test/MemOS/data/memos_cubes"
      },
      "disabled": false
    }
  }
}
```

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
      "command": "G:/test/MemOS/conda_venv/python.exe",
      "args": [
        "G:/test/MemOS/mcp-server/memos_mcp_server.py"
      ],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "G:/test/MemOS/data/memos_cubes"
      },
      "alwaysAllow": [
        "memos_search",
        "memos_save",
        "memos_list",
        "memos_suggest",
        "memos_get_graph"
      ]
    }
  }
}
```

> **`alwaysAllow` 说明**: 列出的工具将自动授权，无需每次确认。建议不要将 `memos_delete` 加入此列表。
>
> **`alwaysAllow` note**: Listed tools are auto-approved without confirmation. It's recommended NOT to include `memos_delete` in this list.

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
          "command": "G:/test/MemOS/conda_venv/python.exe",
          "args": [
            "G:/test/MemOS/mcp-server/memos_mcp_server.py"
          ],
          "env": {
            "MEMOS_URL": "http://localhost:18000",
            "MEMOS_USER": "dev_user",
            "MEMOS_DEFAULT_CUBE": "dev_cube",
            "MEMOS_CUBES_DIR": "G:/test/MemOS/data/memos_cubes"
          },
          "alwaysAllow": [
            "memos_search",
            "memos_save",
            "memos_list",
            "memos_suggest",
            "memos_get_graph"
          ]
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
      "/mnt/g/test/MemOS/mcp-server/run_mcp.sh"
    ],
    "env": {
      "MEMOS_URL": "http://localhost:18000",
      "MEMOS_USER": "dev_user",
      "MEMOS_DEFAULT_CUBE": "dev_cube",
      "MEMOS_CUBES_DIR": "G:/test/MemOS/data/memos_cubes"
    },
    "alwaysAllow": [
      "memos_search",
      "memos_save",
      "memos_list",
      "memos_suggest",
      "memos_get_graph"
    ]
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
PYTHON="/mnt/g/test/MemOS/conda_venv/python.exe"

# Windows-style path for the script (Windows Python needs this)
# 替换 /path/to/MemOS 为你的实际路径 | Replace /path/to/MemOS with your path
SCRIPT="G:/test/MemOS/mcp-server/memos_mcp_server.py"

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
    "command": "G:/test/MemOS/conda_venv/python.exe",
    "args": [
      "G:/test/MemOS/mcp-server/memos_mcp_server.py"
    ],
    "env": {
      "MEMOS_URL": "http://localhost:18000",
      "MEMOS_USER": "dev_user",
      "MEMOS_DEFAULT_CUBE": "dev_cube",
      "MEMOS_CUBES_DIR": "G:/test/MemOS/data/memos_cubes"
    },
    "alwaysAllow": [
      "memos_search",
      "memos_save",
      "memos_list",
      "memos_suggest",
      "memos_get_graph"
    ]
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

假设你的 MemOS 安装在 `C:\path\to\MemOS`：

```json
{
  "mcpServers": {
    "memos": {
      "type": "stdio",
      "command": "C:/path/to/MemOS/conda_venv/python.exe",
      "args": [
        "C:/path/to/MemOS/mcp-server/memos_mcp_server.py"
      ],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "C:/path/to/MemOS/data/memos_cubes",
        "MEMOS_TIMEOUT_TOOL": "120.0",
        "MEMOS_TIMEOUT_STARTUP": "30.0",
        "MEMOS_TIMEOUT_HEALTH": "5.0",
        "MEMOS_API_WAIT_MAX": "60.0",
        "MEMOS_ENABLE_DELETE": "false"
      },
      "alwaysAllow": [
        "memos_search",
        "memos_save",
        "memos_list",
        "memos_suggest",
        "memos_get_graph"
      ]
    }
  }
}
```

> 此为完整配置示例，包含所有可选超时参数。超时参数可省略（使用默认值）。
>
> This is the full config example with all optional timeout parameters. Timeout params can be omitted (defaults apply).

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
      },
      "alwaysAllow": [
        "memos_search",
        "memos_save",
        "memos_list",
        "memos_suggest",
        "memos_get_graph"
      ]
    }
  }
}
```

### WSL 用户 - 全局配置示例

假设 MemOS 在 Windows 中位置为 `C:\path\to\MemOS`（对应 WSL 中的 `/mnt/c/path/to/MemOS`）：

```json
{
  "mcpServers": {
    "memos": {
      "type": "stdio",
      "command": "bash",
      "args": [
        "/mnt/c/path/to/MemOS/mcp-server/run_mcp.sh"
      ],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "C:/path/to/MemOS/data/memos_cubes"
      },
      "alwaysAllow": [
        "memos_search",
        "memos_save",
        "memos_list",
        "memos_suggest",
        "memos_get_graph"
      ]
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

PYTHON="/mnt/c/path/to/MemOS/conda_venv/python.exe"
SCRIPT="C:/path/to/MemOS/mcp-server/memos_mcp_server.py"

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
- `memos_get_graph` - 知识图谱查询 | Knowledge graph query (relationships: CAUSE/RELATE/CONFLICT/CONDITION)
- `memos_delete` - 删除记忆 | Delete memories (需启用 `MEMOS_ENABLE_DELETE=true` | requires `MEMOS_ENABLE_DELETE=true`)

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

### memos_get_graph

查询知识图谱，获取记忆之间的关系。

Query knowledge graph to understand relationships between memories.

**关系类型 | Relationship Types:**

| 关系 | 含义 | Meaning |
|------|------|---------|
| `CAUSE` | 因果关系 | A caused B |
| `RELATE` | 关联关系 | A is related to B |
| `CONFLICT` | 冲突关系 | A conflicts with B |
| `CONDITION` | 条件关系 | A depends on condition B |

**参数 | Parameters:**

```json
{
  "query": "搜索关键词",
  "cube_id": "dev_cube"  // 可选
}
```

**示例 | Example:**

```
查询 Neo4j 启动失败的关系:
→ memos_get_graph("Neo4j startup failure")
→ 返回:
  [Java not installed] ──CAUSE──> [Neo4j failed to start]
  [Port 7687 in use] ──RELATE──> [Neo4j failed to start]
```

---

### memos_delete

删除记忆。**默认禁用**，需设置 `MEMOS_ENABLE_DELETE=true` 启用。

Delete memories. **Disabled by default**, requires `MEMOS_ENABLE_DELETE=true` to enable.

**参数 | Parameters:**

```json
{
  "memory_id": "xxx",       // 删除单条记忆 | Delete single memory
  "cube_id": "dev_cube",    // 可选
  "delete_all": false        // ⚠️ 设为 true 删除全部 | Set true to delete all
}
```

**安全特性 | Safety Features:**

| 特性 | 说明 | Description |
|------|------|-------------|
| 默认禁用 | 需 `MEMOS_ENABLE_DELETE=true` | Disabled by default |
| 工具隐藏 | 禁用时 AI 看不到此工具 | Hidden from AI when disabled |
| 确认要求 | AI 删除前必须确认 | AI must confirm before deleting |
| 批量保护 | `delete_all` 需二次确认 | Bulk delete requires extra confirmation |

---

## ⚙️ Environment Variables | 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API 地址 |
| `MEMOS_USER` | `dev_user` | 用户 ID |
| `MEMOS_DEFAULT_CUBE` | `dev_cube` | 默认记忆 Cube |
| `MEMOS_CUBES_DIR` | *(需配置)* | Cube 存储目录 (用于自动注册) |
| `MEMOS_TIMEOUT_TOOL` | `120.0` | 工具调用超时 (秒) - 大文档+向量化时需更长 |
| `MEMOS_TIMEOUT_STARTUP` | `30.0` | 启动注册超时 (秒) |
| `MEMOS_TIMEOUT_HEALTH` | `5.0` | 健康检查超时 (秒) |
| `MEMOS_API_WAIT_MAX` | `60.0` | 等待 API 就绪最大时间 (秒) |
| `MEMOS_ENABLE_DELETE` | `false` | ⚠️ 启用删除功能 (危险操作，默认禁用) |

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API URL |
| `MEMOS_USER` | `dev_user` | Default user ID |
| `MEMOS_DEFAULT_CUBE` | `dev_cube` | Default memory cube |
| `MEMOS_CUBES_DIR` | *(must configure)* | Cube storage directory (for auto-registration) |
| `MEMOS_TIMEOUT_TOOL` | `120.0` | Tool call timeout (seconds) - for large documents with embedding |
| `MEMOS_TIMEOUT_STARTUP` | `30.0` | Startup cube registration timeout (seconds) |
| `MEMOS_TIMEOUT_HEALTH` | `5.0` | Health check timeout (seconds) |
| `MEMOS_API_WAIT_MAX` | `60.0` | Max wait time for API ready (seconds) |
| `MEMOS_ENABLE_DELETE` | `false` | ⚠️ Enable delete functionality (dangerous, disabled by default) |

> **超时说明**: 当保存或搜索大文档时，embedding 模型处理需要较长时间。`MEMOS_TIMEOUT_TOOL` 默认 120 秒，可按需调整。
>
> **Timeout note**: When saving/searching large documents, embedding model processing takes longer. `MEMOS_TIMEOUT_TOOL` defaults to 120s, adjust as needed.

### 自动注册 Cube | Auto-Register Cube

MCP Server 会在首次使用时**自动注册** cube，无需手动创建。启动时还会等待 API 就绪并预注册。

MCP Server will **auto-register** cube on first use, no manual creation needed. It also waits for API readiness and pre-registers at startup.

```
MCP Server 启动 | Startup
        ↓
等待 API 就绪 (最长 MEMOS_API_WAIT_MAX 秒)
Wait for API ready (up to MEMOS_API_WAIT_MAX seconds)
        ↓
预注册 cube (最多 3 次重试)
Pre-register cube (up to 3 retries)
        ↓
首次调用 memos_search/save/list
First call to memos_search/save/list
        ↓
验证 cube 已加载 | Verify cube loaded
        ↓ (未加载 | not loaded)
自动注册并重试 | Auto-register and retry
        ↓
继续执行 | Continue operation
```

---

## 🔒 Safety: Delete Functionality | 安全: 删除功能

`memos_delete` 工具**默认禁用**，防止 AI 意外删除数据。

The `memos_delete` tool is **DISABLED by default** to prevent accidental data loss by AI.

### 启用删除 | Enable Delete

在 MCP 配置的 `env` 中显式设置:

Explicitly set in your MCP config `env`:

```json
"env": {
  "MEMOS_ENABLE_DELETE": "true"
}
```

### 安全机制 | Safety Mechanisms

```
用户启用 MEMOS_ENABLE_DELETE=true
        ↓
工具对 AI 可见 | Tool visible to AI
        ↓
AI 收到删除请求 | AI receives delete request
        ↓
AI 必须向用户确认 | AI must confirm with user
        ↓
确认后执行删除 | Execute after confirmation
```

| 安全层 | 说明 | Safety Layer | Description |
|--------|------|-------------|-------------|
| 环境变量开关 | 默认 `false` | Env var switch | Default `false` |
| 工具隐藏 | 禁用时 AI 无法看到工具 | Tool hiding | AI can't see tool when disabled |
| 确认提示 | 工具描述要求 AI 确认 | Confirmation | Tool description requires AI to confirm |
| 双重调用 | 禁用时调用返回错误提示 | Double check | Returns error message if called when disabled |

---

## 🔍 How It Works | 工作原理

```
+-------------------------------------------------------------+
|                    Claude Code + MCP                        |
+-------------------------------------------------------------+
|                                                             |
|  User Input                                                 |
|      |                                                      |
|      v                                                      |
|  +-------------------------------------------------------+  |
|  |             Claude AI Analyzes Context                |  |
|  |                                                       |  |
|  |  Error detected? ----> memos_search(ERROR_PATTERN)    |  |
|  |  Task completed? ----> memos_save(MILESTONE)          |  |
|  |  Need history?   ----> memos_search(keywords)         |  |
|  |  Need relations? ----> memos_get_graph(query)         |  |
|  |  Cleanup needed? ----> memos_delete(memory_id)        |  |
|  |                                                       |  |
|  +--------------------------+----------------------------+  |
|                             |                               |
|                             v                               |
|                      MCP Server (memos)                     |
|                             |                               |
|                             v                               |
|                      MemOS API (:18000)                     |
|                             |                               |
|                  +----------+----------+                    |
|                  v          v          v                    |
|             Embedding    Vector DB   Graph DB               |
|             (Ollama)     (Qdrant)    (Neo4j)                |
|                                                             |
+-------------------------------------------------------------+
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
- [CLAUDE.md](../CLAUDE.md) - 项目上下文配置
- [Changelog](CHANGELOG.md) - 更新日志

---

## 🔮 Future Enhancements | 未来增强

- [ ] 自动检测项目切换，切换 cube
- [x] ~~Hooks 集成，在特定事件时自动触发~~ ✅ 已完成
- [x] ~~CLAUDE.md 项目上下文~~ ✅ 已完成
- [x] ~~知识图谱关系查询 (memos_get_graph)~~ ✅ 已完成
- [x] ~~安全删除功能 (memos_delete + 安全开关)~~ ✅ 已完成
- [x] ~~可配置超时参数~~ ✅ 已完成
- [x] ~~启动时自动注册 + 重试机制~~ ✅ 已完成
- [ ] 记忆相关性评分优化
- [ ] 多 cube 跨项目搜索
- [ ] 记忆过期/归档机制
- [ ] 多用户协作支持

---

## 📄 CLAUDE.md Integration | CLAUDE.md 集成

> **v0.4.0** - 项目级上下文增强

在项目根目录创建 `CLAUDE.md`，Claude Code 会在对话开始时自动读取。

Create `CLAUDE.md` in project root. Claude Code reads it at conversation start.

### 示例 | Example

```markdown
# My Project Guide

## Memory System
- Cube ID: `my_project_cube`
- Memory Mode: `tree_text`

## Auto Behaviors
- Search ERROR_PATTERN on errors
- Save MILESTONE after completing features

## Key Files
- `src/config.py` - Main configuration
```

### 好处 | Benefits

| 好处 | Benefit |
|------|---------|
| 项目特定上下文 | Project-specific context |
| 一致的记忆行为 | Consistent memory behaviors |
| 跨会话持久 | Persists across sessions |

👉 查看示例: [CLAUDE.md](../CLAUDE.md)

---

## 🪝 Hooks Integration | Hooks 集成

> **v0.4.0** - 事件驱动的记忆触发

Claude Code Hooks 可以在特定事件时自动执行脚本。

Claude Code Hooks can automatically execute scripts on specific events.

### 可用 Hooks | Available Hooks

| Script | Event | Purpose |
|--------|-------|---------|
| `memos_user_prompt.sh` | UserPromptSubmit | 确认记忆系统活跃 |
| `memos_block_sensitive.sh` | PreToolUse | 敏感文件编辑警告 |
| `memos_log_commands.sh` | PostToolUse | 记录 bash 命令 |
| `memos_notify_milestone.sh` | PostToolUse | 里程碑保存提醒 |

### 配置 | Configuration

在 `.claude/settings.json` 中配置:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/memos_user_prompt.sh"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/memos_block_sensitive.sh"
          }
        ]
      }
    ]
  }
}
```

### Hook 工作原理 | How Hooks Work

```
User Action
         |
         v
Claude Code Detect Event
         |
         v
Match Hook Config
         |
         v
Execute Script (stdin: JSON)
         |
         v
Return Result
    +-- continue: true  -> proceed
    +-- continue: false -> block
```

👉 详细文档: [.claude/hooks/README.md](../.claude/hooks/README.md)

---

## 🧠 Advanced: Neo4j Knowledge Graph Mode | 高级: Neo4j 知识图谱模式

> **v0.4.0 Preview** - 从扁平记忆升级为知识图谱记忆

### 对比 | Comparison

| 特性 | general_text | tree_text |
|------|--------------|-----------|
| 存储 | Qdrant 向量 | Neo4j 图 + Qdrant 向量 |
| 结构 | 原始文本 | LLM 提炼 (key, tags, background) |
| 记忆层级 | 单层 | WorkingMemory + LongTermMemory |
| 置信度 | 无 | confidence scoring |
| 关系 | 无 | CAUSE/CONDITION/CONFLICT/RELATE |
| 可视化 | 无 | Neo4j Browser 图谱 |

### 架构 | Architecture

```
Memory Save Flow (tree_text mode):

      User Input: "[MILESTONE] Completed login feature"
                                |
                                v
          +------------------------------------------+
          |           LLM Memory Extraction          |
          |     (Uses OPENAI_API_KEY from .env)      |
          |                                          |
          |   Extract: key, tags, background         |
          |   Evaluate: confidence                   |
          |   Classify: WorkingMemory/LongTermMemory |
          +------------------------------------------+
                                |
                       +--------+--------+
                       v                 v
                  +--------+        +--------+
                  | Neo4j  |        | Qdrant |
                  | (Graph)|        |(Vector)|
                  +--------+        +--------+
```

### 配置要求 | Requirements

1. **Neo4j Community Edition** (免费)
   ```bash
   # Docker
   docker run -d -p 7474:7474 -p 7687:7687 neo4j:community

   # 或下载: https://neo4j.com/download-center/
   ```

2. **配置 .env**
   ```env
   MOS_TEXT_MEM_TYPE=tree_text
   MOS_ENABLE_REORGANIZE=true

   NEO4J_BACKEND=neo4j-community
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   NEO4J_DB_NAME=neo4j

   # LLM 用于记忆提炼 (重要!)
   OPENAI_API_KEY=sk-xxx
   OPENAI_API_BASE=https://api.openai.com/v1
   ```

3. **配置 cube config.json** (首次需要)
   ```json
   {
     "text_mem": {
       "backend": "tree_text",
       "config": {
         "graph_db": {
           "backend": "neo4j-community",
           "config": {
             "uri": "bolt://localhost:7687",
             "user": "neo4j",
             "password": "your_password",
             "db_name": "neo4j",
             "use_multi_db": false,
             "user_name": "dev_user",
             "vec_config": { ... }
           }
         }
       }
     }
   }
   ```

### 可视化查询 | Visualization

在 Neo4j Browser (http://localhost:7474) 中：

```cypher
-- 查看所有记忆节点
MATCH (n:Memory) RETURN n LIMIT 50

-- 按标签统计
MATCH (n:Memory) UNWIND n.tags AS tag
RETURN tag, count(*) ORDER BY count(*) DESC

-- 按类型分布
MATCH (n:Memory)
RETURN n.memory_type as type, count(*) as count
```

---

<div align="center">

**Proactive Memory for AI Assistants** 🧠

*让 AI 主动记忆*

</div>
