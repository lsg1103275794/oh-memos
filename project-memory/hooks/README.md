# MemOS Hooks

Claude Code hooks for enhanced memory integration.

## Quick Start

**选择适合你平台的文件夹：**

| 平台 | 文件夹 | 适用场景 |
|------|--------|----------|
| 🌐 **node/** | Cross-platform | ✅ **推荐** - Windows + WSL 都能用 |
| 🐧 **bash/** | Linux/macOS/WSL | 纯 Linux 或 macOS 用户 |
| 🪟 **powershell/** | Windows Only | 纯 Windows 用户 (不用 WSL) |

## Installation

### Option 1: Cross-platform (Recommended) 🌐

**适用：Windows + WSL 混合使用**

```bash
# 复制 node/ 文件夹的配置
cp project-memory/hooks/node/settings.json .claude/settings.json
```

### Option 2: Bash (Linux/macOS/WSL) 🐧

**适用：纯 Linux、macOS 或只在 WSL 中使用**

```bash
cp project-memory/hooks/bash/settings.json .claude/settings.json
```

### Option 3: PowerShell (Windows Only) 🪟

**适用：纯 Windows，不使用 WSL**

```powershell
Copy-Item project-memory\hooks\powershell\settings.json .claude\settings.json
```

## 文件结构

```
project-memory/hooks/
├── README.md
│
├── 🌐 node/                      ← Cross-platform (推荐)
│   ├── settings.json             ← 配置文件
│   ├── memos_user_prompt.js
│   ├── memos_block_sensitive.js
│   ├── memos_log_commands.js
│   └── memos_notify_milestone.js
│
├── 🐧 bash/                      ← Linux/macOS/WSL
│   ├── settings.json
│   ├── memos_user_prompt.sh
│   ├── memos_block_sensitive.sh
│   ├── memos_log_commands.sh
│   └── memos_notify_milestone.sh
│
└── 🪟 powershell/                ← Windows Only
    ├── settings.json
    ├── memos_user_prompt.ps1
    ├── memos_user_prompt.cmd
    ├── memos_block_sensitive.ps1
    ├── memos_log_commands.ps1
    └── memos_notify_milestone.ps1
```

## Hook 功能说明

| Hook | 触发时机 | 功能 |
|------|----------|------|
| `memos_user_prompt` | 用户发送消息 | 确认记忆系统激活 |
| `memos_block_sensitive` | 编辑文件前 | 警告敏感文件 (.env, credentials 等) |
| `memos_log_commands` | 执行命令后 | 记录 bash 命令历史 |
| `memos_notify_milestone` | 编辑文件后 | 提示保存里程碑 |

## 跨平台原理 (node/)

Node.js 脚本自动检测运行环境：

```javascript
process.platform === 'win32'
  ? 'G:/path/to/script.js'      // Windows
  : '/mnt/g/path/to/script.js'  // WSL/Linux
```

这样同一个配置文件可以在 Windows CMD 和 WSL 中都正常工作。

## 自定义

### 添加敏感文件模式

编辑 `node/memos_block_sensitive.js`:

```javascript
const sensitivePatterns = [
  '.env',
  'credentials',
  'your_pattern_here'  // 添加自定义模式
];
```

### 添加里程碑文件

编辑 `node/memos_notify_milestone.js`:

```javascript
const milestoneFiles = [
  'README.md',
  'your_file_here'  // 添加自定义文件
];
```

## 调试

```bash
claude --debug
```

## 相关文档

- [MCP Guide](../../docs/MCP_GUIDE.md) - MCP 记忆工具
- [CLAUDE.md](../../CLAUDE.md) - 项目配置
