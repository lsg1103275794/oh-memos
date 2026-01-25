<div align="center">

# 🧠 MemOSlocal

**Persistent Project Memory Solution for AI Assistants**

*让 AI 拥有持久记忆的项目级解决方案*

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![License](https://img.shields.io/badge/MemOS-Apache%202.0-green.svg)](https://github.com/MemTensor/MemOS)
[![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-lightgrey.svg)]()
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-orange.svg)]()

[🚀 Quick Start](#-quick-start) · [✨ Features](#-core-features) · [📖 Documentation](#-documentation) · [中文](#-中文文档)

</div>

---

## 😫 Does This Sound Familiar?

<table>
<tr>
<td width="33%" align="center">

### 📝 Doc Overload

AI scatters `NOTES.md`, `TODO.md`, `DECISIONS.md` everywhere...

Your project becomes a documentation mess

</td>
<td width="33%" align="center">

### 🧠 Memory Loss

New conversation = Start from zero

*"Why did we choose Redis again?"*
*"How did we fix that bug?"*

**AI: I don't know, this is a new session**

</td>
<td width="33%" align="center">

### 🔁 Same Mistakes

Fixed the same bug 3 times

Fell into the same trap again

**AI never learns from history**

</td>
</tr>
</table>

<div align="center">

### ✨ Now, Try MemOSlocal

<img src="https://img.shields.io/badge/-Before-red?style=for-the-badge" alt="Before"/>

**"AI forgets everything about the project in every new conversation"**

<img src="https://img.shields.io/badge/-After-green?style=for-the-badge" alt="After"/>

**"AI remembers every decision, every bug fix, every milestone"**

</div>

---

## 🎯 What is This?

MemOSlocal is a complete **AI Project Memory Solution** that includes:

| Component | Description | Function |
|-----------|-------------|----------|
| **📦 memos-deploy** | MemOS Portable Deployment | One-click memory backend service |
| **🧠 project-memory** | Claude Code Skill | AI auto-save/search/track memories |
| **🔌 mcp-server** | MCP Protocol Server | AI **proactively** uses memory tools |

```
                    ┌──────────────────────────────────────┐
                    │           Your Project               │
                    └──────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Claude Code + Integrations                       │
│                                                                          │
│  ┌─────────────────────────────┐   ┌─────────────────────────────────┐  │
│  │   project-memory skill      │   │      MCP Server (memos)         │  │
│  │      (Passive Mode)         │   │      (Proactive Mode)           │  │
│  │                             │   │                                 │  │
│  │  User calls /project-memory │   │  AI auto-calls memos_search     │  │
│  │  to save/search memories    │   │  when encountering errors,      │  │
│  │                             │   │  making decisions, etc.         │  │
│  └──────────────┬──────────────┘   └────────────────┬────────────────┘  │
│                 │                                   │                   │
│                 └───────────────┬───────────────────┘                   │
│                                 │                                       │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         MemOS Backend                                    │
│                    http://localhost:18000                                │
│                                                                          │
│   ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐   │
│   │ 🗄️ Memory      │  │ 🔎 Vector      │  │ 🤖 LLM Context         │   │
│   │ Storage        │  │ Search         │  │ Enhancement            │   │
│   │                │  │                │  │                        │   │
│   │ Qdrant Cloud   │  │ Semantic       │  │ OpenAI Compatible      │   │
│   │ or Local       │  │ Similarity     │  │ API                    │   │
│   └────────────────┘  └────────────────┘  └────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Core Features

<table>
<tr>
<td width="50%">

### 🔄 Intelligent Auto-Memory

AI **automatically identifies** and saves key information after completing tasks:

- ✅ Milestone completion
- 🐛 Bug fix solutions
- 🏗️ Architecture decisions
- ⚠️ Gotchas & pitfalls
- ⚙️ Configuration changes

</td>
<td width="50%">

### 🔍 Context-Aware Search

**Automatically retrieves** relevant history before starting work:

- 📚 Solutions to similar problems
- 📋 Previous design decisions
- 🔧 Related configuration records
- 📈 Project progress status

</td>
</tr>
<tr>
<td width="50%">

### 📊 Smart Progress Tracking

Know your project status anytime:

```
📊 Project Progress Report

✅ Completed (5 milestones)
🔧 Recent fixes (3 bugs)
📝 Pending (2 items)
⚠️ Notes (1 gotcha)
```

</td>
<td width="50%">

### 🖥️ Cross-Platform Support

One codebase, runs everywhere:

| Platform | Status |
|----------|--------|
| Windows | ✅ Full support + Portable |
| Linux | ✅ Full support |
| macOS | ✅ Full support |

</td>
</tr>
</table>

---

## 🚀 Quick Start

### 1️⃣ Deploy MemOS Backend

<details>
<summary><b>Windows (Portable Recommended)</b></summary>

```cmd
# Step 1: Setup Python environment (first time only)
# 第一步：安装 Python 环境（仅首次需要）
Double-click setup_env.bat

# The script will show installation paths like:
# 脚本会显示安装路径，例如：
#   Python will be installed to:
#   G:\test\MemOS\conda_venv
#
#   Python executable will be at:
#   G:\test\MemOS\conda_venv\python.exe

# Step 2: Install dependencies and start (first time)
# 第二步：安装依赖并启动（首次）
Double-click install_run.bat

# Step 3: Quick start (after first setup)
# 第三步：快速启动（首次之后）
Double-click run.bat
```

</details>

<details>
<summary><b>Linux / macOS</b></summary>

```bash
# Using Docker
docker-compose up -d

# Or run directly
cd src && python -m uvicorn memos.api.start_api:app --port 18000
```

</details>

**Verify**: Visit http://localhost:18000/docs - if you see the API docs, you're good!

### 2️⃣ Install Claude Code Skill

```bash
# Linux / macOS
cp -r project-memory ~/.claude/skills/

# Windows (CMD)
xcopy /E /I project-memory %USERPROFILE%\.claude\skills\project-memory

# Windows (PowerShell)
Copy-Item -Recurse project-memory $env:USERPROFILE\.claude\skills\
```

### 3️⃣ Configure Environment (Optional)

Run the install script to add CLI tools:

```bash
# Linux / macOS
bash ~/.claude/skills/project-memory/scripts/linux/install.sh

# Windows
%USERPROFILE%\.claude\skills\project-memory\scripts\windows\install.cmd
```

### 4️⃣ Start Using

After installation, Claude Code works **automatically** - no extra steps needed!

---

## 🔌 MCP Server (Proactive Mode)

> **New in v0.3.0**: AI can now **proactively** use memory functions!
>
> **v0.3.1**: Auto-registers cubes on first use - no manual setup needed!

### What's the difference?

| Mode | Trigger | Best For |
|------|---------|----------|
| **Skill (Passive)** | User types `/project-memory` | Explicit memory operations |
| **MCP (Proactive)** | AI decides automatically | Error handling, decision tracking |

### Setup MCP Server

1. **Install dependencies**:
   ```bash
   # Option 1: Direct pip install
   pip install mcp httpx pydantic

   # Option 2: Using project optional dependencies
   pip install MemoryOS[mcp-server]
   ```

2. **Add to Claude Code settings** (`~/.claude.json` under your project):

   **For WSL environment** (recommended):
   ```json
   {
     "projects": {
       "/mnt/g/test/MemOS": {
         "mcpServers": {
           "memos": {
             "type": "stdio",
             "command": "bash",
             "args": ["/mnt/g/test/MemOS/mcp-server/run_mcp.sh"],
             "env": {
               "MEMOS_URL": "http://localhost:18000",
               "MEMOS_USER": "dev_user",
               "MEMOS_DEFAULT_CUBE": "dev_cube"
             }
           }
         }
       }
     }
   }
   ```

   **For pure Windows**:
   ```json
   {
     "mcpServers": {
       "memos": {
         "command": "G:/path/to/python.exe",
         "args": ["G:/path/to/memos_mcp_server.py"],
         "env": {
           "MEMOS_URL": "http://localhost:18000",
           "MEMOS_USER": "dev_user",
           "MEMOS_DEFAULT_CUBE": "dev_cube"
         }
       }
     }
   }
   ```

3. **Restart Claude Code**

### Proactive Features

After setup, Claude will **automatically**:

| Scenario | Action |
|----------|--------|
| 🐛 Encounter an error | Search `ERROR_PATTERN` for solutions |
| 💬 User says "之前/上次" | Search related history |
| ✅ Solve a bug | Save as `ERROR_PATTERN` with solution |
| 🏗️ Make a decision | Save as `DECISION` with rationale |
| 🆕 First use of cube | Auto-register cube (no manual setup!) |

👉 **[Full MCP Guide](docs/MCP_GUIDE.md)**

---

## 🎬 Usage Demo

### Scenario 1: Fixing a Bug

```
👤 You: Help me fix the user login issue

🤖 AI: Searching project memories...

    📚 Found relevant history:
    ┌────────────────────────────────────────────────────┐
    │ [BUGFIX] 2025-01-20                                │
    │ JWT token expiry misconfigured, expired instantly  │
    │ Fix: Modified JWT_EXPIRY = 3600 in config.py       │
    ├────────────────────────────────────────────────────┤
    │ [DECISION] 2025-01-15                              │
    │ Chose bcrypt for password hashing, cost factor=12  │
    └────────────────────────────────────────────────────┘

    Based on history, let me check if it's a similar token issue...

    [Debugging...]

    ✅ Issue identified! This time it's a session config problem.

    💾 Saving memory...
    ┌────────────────────────────────────────────────────┐
    │ [BUGFIX] Login failure - Session timeout config    │
    │ Cause: SESSION_TIMEOUT was 30 seconds (too short)  │
    │ Fix: Changed to 1800 seconds (30 minutes)          │
    │ File: src/config.py:42                             │
    └────────────────────────────────────────────────────┘
```

### Scenario 2: Checking Progress

```
👤 You: What's our project status?

🤖 AI: Retrieving project memories, generating report...

    ╔══════════════════════════════════════════════════════╗
    ║              📊 Project Progress Report               ║
    ║              my-awesome-project                       ║
    ╠══════════════════════════════════════════════════════╣
    ║                                                      ║
    ║  ✅ Completed Milestones (4)                         ║
    ║  ├── User authentication system       2025-01-15    ║
    ║  ├── Database schema design           2025-01-18    ║
    ║  ├── RESTful API framework            2025-01-20    ║
    ║  └── Unit test coverage 80%           2025-01-22    ║
    ║                                                      ║
    ║  🔧 Recent Fixes (2)                                 ║
    ║  ├── JWT token expiry issue           2025-01-20    ║
    ║  └── Session timeout config           2025-01-24    ║
    ║                                                      ║
    ║  ⚠️ Notes                                            ║
    ║  └── Docker container needs > 2GB RAM (OOM issue)   ║
    ║                                                      ║
    ║  📝 Pending                                          ║
    ║  └── Add API rate limiting (mentioned last time)    ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
```

---

## 📁 Project Structure

```
MemOSlocal/
│
├── 📂 memos-deploy/                    # MemOS Portable Deployment
│   ├── 📂 docs/
│   │   ├── 📄 DEPLOY_CN.md            # Chinese Guide
│   │   └── 📄 DEPLOY_EN.md            # English Guide
│   ├── 🔧 setup_env.bat               # Setup Python environment (first time)
│   ├── 🔧 install_run.bat             # Install dependencies + start
│   └── 🔧 run.bat                     # Quick start (after setup)
│
├── 📂 mcp-server/                      # 🔌 MCP Protocol Server (NEW!)
│   ├── 🐍 memos_mcp_server.py         # Main MCP server
│   ├── 🐍 install.py                  # Auto-configure Claude Code
│   ├── 🐍 test_server.py              # Test server functionality
│   ├── 📄 pyproject.toml              # Package configuration
│   └── 📄 README.md                   # MCP server documentation
│
├── 📂 project-memory/                  # 🧠 Claude Code Skill
│   ├── 📄 SKILL.md                    # AI behavior instructions
│   ├── 📄 README.md                   # English Docs
│   ├── 📄 README_CN.md                # Chinese Docs
│   │
│   ├── 📂 scripts/                    # Core Scripts
│   │   ├── 🐍 memos_save.py           # Save memory
│   │   ├── 🐍 memos_search.py         # Search memory
│   │   ├── 🐍 memos_init_project.py   # Initialize project
│   │   │
│   │   ├── 📂 linux/                  # Linux/macOS
│   │   │   ├── install.sh
│   │   │   ├── memos-init.sh
│   │   │   ├── memos-save.sh
│   │   │   └── memos-search.sh
│   │   │
│   │   └── 📂 windows/                # Windows
│   │       ├── install.cmd
│   │       ├── install.ps1
│   │       ├── memos-init.cmd
│   │       ├── memos-save.cmd
│   │       └── memos-search.cmd
│   │
│   └── 📂 references/
│       └── 📄 examples.md             # Memory format examples
│
├── 📂 docs/                            # 📖 Documentation
│   ├── 📄 CHANGELOG.md                # Version history
│   └── 📄 MCP_GUIDE.md                # MCP Server guide
│
├── 📄 README.md                        # This file
├── 📄 .gitignore
└── 📄 LICENSE
```

---

## 🛠️ CLI Tools

After installation, use these commands anywhere:

### Initialize Project

```bash
memos-init                    # Auto-detect git project name
memos-init -p my-project      # Specify project name
```

### Save Memory

```bash
# Basic usage
memos-save "memory content" -t TYPE

# Full example
memos-save "Implemented user avatar upload with S3 storage, supports cropping and compression" \
  -t FEATURE \
  -p my-project \
  --tags s3 upload avatar

# Memory Types
# MILESTONE - Milestone     BUGFIX   - Bug fix
# FEATURE   - New feature   DECISION - Decision
# GOTCHA    - Pitfall       CONFIG   - Config change
# PROGRESS  - Progress update
```

### Search Memory

```bash
memos-search "keyword"              # Current project
memos-search "keyword" --all        # All projects
memos-search "keyword" --json       # JSON output
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API URL |
| `MEMOS_USER` | `dev_user` | Default user ID |
| `MEMOS_CUBES_DIR` | `~/.memos_cubes` | Memory storage directory |

### Memory Format

```markdown
[BUGFIX] Project: my-project | Date: 2025-01-25

## Summary
Fixed user login session timeout issue

## Context
Users reported being logged out quickly after login

## Details
- Cause: SESSION_TIMEOUT = 30 (seconds) was too short
- Fix: Changed to 1800 (30 minutes)
- File: src/config.py:42

## Outcome
- Tests passed
- Deployed to production

Tags: bugfix, auth, session, config
```

---

## 📋 Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Python** | 3.10+ | 3.11+ |
| **MemOS** | - | localhost:18000 |
| **Ollama** | - | nomic-embed-text |
| **Qdrant** | - | Cloud free tier |
| **Memory** | 4GB | 8GB+ |

---

## 📖 Documentation

### Quick Navigation

| Document | Description | Language |
|----------|-------------|----------|
| [**Changelog**](docs/CHANGELOG.md) | Project updates and fixes | English |
| [**🔌 MCP Server Guide**](docs/MCP_GUIDE.md) | Proactive memory integration | EN/中文 |
| [**Deployment Guide**](memos-deploy/docs/DEPLOY_EN.md) | Full setup: environment, database, embedding, LLM | English |
| [**部署指南**](memos-deploy/docs/DEPLOY_CN.md) | 完整部署：环境、数据库、嵌入模型、LLM | 中文 |
| [**Skill README**](project-memory/README.md) | Claude Code skill usage | English |
| [**技能说明**](project-memory/README_CN.md) | Claude Code 技能使用说明 | 中文 |
| [**Memory Examples**](project-memory/references/examples.md) | Memory format templates | English |

### Key Topics

<details>
<summary><b>🗄️ Database Setup (Qdrant)</b></summary>

**Qdrant Cloud (Recommended)** - Free 1GB storage, no local resources needed:

```env
QDRANT_MODE=cloud
QDRANT_URL=https://your-cluster.aws.qdrant.io:6333
QDRANT_API_KEY=your-api-key
```

**Local Qdrant** - Full offline, Docker required:

```env
QDRANT_MODE=local
QDRANT_URL=http://localhost:6333
```

👉 [Full Database Guide](memos-deploy/docs/DEPLOY_EN.md#database-configuration)

</details>

<details>
<summary><b>🤖 Embedding Model (Ollama)</b></summary>

```bash
# Install Ollama: https://ollama.ai/download
ollama pull nomic-embed-text
```

```env
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

👉 [Full Embedding Guide](memos-deploy/docs/DEPLOY_EN.md#embedding-model-configuration)

</details>

<details>
<summary><b>🔑 LLM API (OpenAI Compatible)</b></summary>

```env
# OpenAI
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Or other compatible APIs (DeepSeek, local Ollama, etc.)
```

👉 [Full LLM Guide](memos-deploy/docs/DEPLOY_EN.md#llm-api-configuration)

</details>

---

## 🔗 Related Links

<table>
<tr>
<td align="center">
<a href="https://github.com/MemTensor/MemOS">
<img src="https://img.shields.io/badge/MemOS-Official-blue?style=for-the-badge" alt="MemOS"/>
</a>
<br/>Memory OS
</td>
<td align="center">
<a href="https://claude.ai">
<img src="https://img.shields.io/badge/Claude-Code-orange?style=for-the-badge" alt="Claude Code"/>
</a>
<br/>Anthropic CLI
</td>
<td align="center">
<a href="https://qdrant.tech">
<img src="https://img.shields.io/badge/Qdrant-Vector%20DB-red?style=for-the-badge" alt="Qdrant"/>
</a>
<br/>Vector Database
</td>
<td align="center">
<a href="https://ollama.ai">
<img src="https://img.shields.io/badge/Ollama-Local%20LLM-green?style=for-the-badge" alt="Ollama"/>
</a>
<br/>Local Models
</td>
</tr>
</table>

---

## 📄 License

| Component | License |
|-----------|---------|
| MemOS Deployment Docs | Apache License 2.0 (based on [MemOS](https://github.com/MemTensor/MemOS)) |
| Project Memory Skill | MIT License |

---

## 📖 中文文档

<details>
<summary><b>点击展开中文说明</b></summary>

### 😫 你是否也有这些烦恼？

| 问题 | 症状 | MemOSlocal 解决方案 |
|------|------|---------------------|
| **📝 文档臃肿** | AI 到处写 NOTES.md、TODO.md，项目越来越乱 | 统一存储到向量数据库，项目保持整洁 |
| **🧠 记忆断层** | 新对话就忘光，"之前为什么选 Redis？" | 语义搜索自动召回相关决策记忆 |
| **🔁 重蹈覆辙** | 同样的 Bug 修了三遍，AI 记吃不记打 | ERROR_PATTERN 自动匹配，主动提醒解决方案 |

### 这是什么？

MemOSlocal 是一套完整的 **AI 项目记忆解决方案**：

- **📦 memos-deploy**: MemOS 便携部署包，一键启动记忆后端
- **🧠 project-memory**: Claude Code 技能，AI 自动记忆/搜索/追踪
- **🔌 mcp-server**: MCP 协议服务器，AI **主动**调用记忆功能

### 核心特性

| 特性 | 描述 |
|------|------|
| 🔄 智能自动记忆 | AI 完成任务后自动保存关键信息 |
| 🔍 上下文感知搜索 | 开始工作前自动检索相关历史 |
| 📊 智能进度追踪 | 随时了解项目全貌 |
| 🖥️ 全平台支持 | Windows / Linux / macOS |
| 🔌 **MCP 主动模式** | AI 自动判断何时搜索/保存记忆 |

### 快速开始

```bash
# 1. 安装 Python 环境 (Windows, 首次)
双击 setup_env.bat

# 2. 安装依赖并启动 (首次)
双击 install_run.bat

# 3. 快速启动 (之后)
双击 run.bat

# 4. 配置 MCP (推荐)
# 编辑 ~/.claude.json，添加 memos MCP 服务器配置

# 5. 开始使用 - AI 主动工作！
```

### MCP 工具 (推荐)

现在推荐使用 MCP 工具，AI 会自动调用：

| 工具 | 功能 | 触发场景 |
|------|------|----------|
| `memos_search` | 搜索记忆 | 遇到错误、用户说"之前" |
| `memos_save` | 保存记忆 | 修复 Bug、做出决策 |
| `memos_list` | 列出记忆 | 查看项目进度 |
| `memos_suggest` | 搜索建议 | 不确定搜什么 |

👉 [MCP 配置指南](docs/MCP_GUIDE.md) | [完整中文文档](project-memory/README_CN.md)

</details>

---

## 🤝 Contributing

Contributions welcome! Please check out our [Contributing Guide](CONTRIBUTING.md).

---

<div align="center">

**Making AI Remember Every Project Decision** 🧠

*让 AI 记住你的每一个项目决策*

[![Star](https://img.shields.io/github/stars/lsg1103275794/MemOSlocal?style=social)](https://github.com/lsg1103275794/MemOSlocal)

</div>
