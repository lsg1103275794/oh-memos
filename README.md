<div align="center">

# 🧠 MemOSLocal-SM

**Persistent Project Memory for AI Assistants**

*让 AI 拥有持久记忆的项目级解决方案*

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-lightgrey.svg)]()
[![Neo4j](https://img.shields.io/badge/Graph-Neo4j-blue.svg)](https://neo4j.com)
[![Qdrant](https://img.shields.io/badge/Vector-Qdrant-red.svg)](https://qdrant.tech)

[🚀 Quick Start](#-quick-start) · [✨ Features](#-key-features) · [🏗️ Architecture](#-architecture) · [📖 Docs](#-documentation)

<img src="docs/images/cover.jpg" width="70%" alt="MemOSLocal-SM"/>

</div>

---

## 😫 The Problem

| Issue | Symptom |
|-------|---------|
| **Memory Loss** | New chat = AI forgets everything. *"Why did we choose Redis again?"* |
| **Repeat Mistakes** | Same bug fixed 3 times. AI never learns from history. |
| **Doc Overload** | AI scatters `NOTES.md`, `TODO.md` everywhere. Project becomes a mess. |

**MemOSLocal-SM transforms AI from a "stateless chatbot" into a "Senior Project Partner".**

---

## ✨ Key Features

<table>
<tr>
<td width="50%">
<img src="docs/images/feature-auto-memory.jpg" alt="Auto Memory"/>
</td>
<td width="50%">

### 🧠 Intelligent Auto-Memory

AI **proactively saves** key information:
- ✅ Milestones & decisions
- 🐛 Bug fixes & solutions
- ⚠️ Gotchas & configurations

**No manual note-taking required.**

</td>
</tr>
<tr>
<td width="50%">

### 🔍 Context-Aware Search

AI **auto-retrieves** history before work:
- Similar problem solutions
- Past design decisions
- Related configurations

**Never repeat the same mistake.**

</td>
<td width="50%">
<img src="docs/images/feature-retrieval.jpg" alt="Smart Retrieval"/>
</td>
</tr>
</table>

---

## 🏗️ Architecture

<div align="center">
<img src="docs/images/architecture-mindmap.png" width="85%" alt="Architecture"/>
</div>

### Dual-Engine Design

| Engine | Role | Technology |
|--------|------|------------|
| **Knowledge Graph** | Logical relationships (CAUSE, CONDITION, RELATE) | Neo4j |
| **Vector Search** | Semantic similarity matching | Qdrant |
| **LLM Extraction** | Auto-extract key, tags, confidence | Ollama / OpenAI |

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code / AI                         │
│                          ↓                                  │
│                   ┌─────────────┐                           │
│                   │ MCP Server  │  ← Proactive memory tools │
│                   └──────┬──────┘                           │
│                          ↓                                  │
│   ┌──────────────────────────────────────────────────────┐  │
│   │              MemOS Backend (localhost:18000)         │  │
│   │                                                      │  │
│   │   ┌────────────┐    ┌────────────┐    ┌──────────┐   │  │
│   │   │   Neo4j    │    │   Qdrant   │    │  Ollama  │   │  │
│   │   │   :7687    │    │   :6333    │    │  :11434  │   │  │
│   │   │  (Graph)   │    │  (Vector)  │    │  (LLM)   │   │  │
│   │   └────────────┘    └────────────┘    └──────────┘   │  │
│   └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 🔒 Privacy-First

- **100% Local**: All data stays on your machine
- **No Cloud Required**: Neo4j + Qdrant + Ollama run locally
- **Optional Cloud**: Qdrant Cloud for cross-device sync (vectors only)

---

## 🔬 Technical Evolution

MemOSLocal-SM is constantly evolving based on the latest academic research. We have recently implemented:

- **MAGMA Multi-Graph Routing**: Intent-based sub-graph filtering to boost precision and reduce latency.
- **HippoRAG 2 PPR**: Personalized PageRank for deep causality tracing and associative memory.
- **EverMemOS Self-Organization**: (Experimental) Memory lifecycle management and episodic trace consolidation.

> 📖 View the full list of research-inspired changes in [**Changelog**](docs/CHANGELOG.md).

---

## 🚀 Quick Start

### Option 1: Bundle Install (Recommended)

Everything included - no manual setup!

| Platform | Download |
|----------|----------|
| **Windows x64** | [**夸克网盘下载**](https://pan.quark.cn/s/d24876f7c167) |

```cmd
:: 1. Extract and install
scripts\bundle\install.bat

:: 2. Configure LLM API key
notepad .env

:: 3. Start all services
scripts\bundle\start.bat
```

### Option 2: Manual Setup

<details>
<summary>Click to expand</summary>

```bash
# 1. Clone repo
git clone https://github.com/lsg1103275794/MemOSLocal-SM.git
cd MemOSLocal-SM

# 2. Setup environment (Windows)
setup_env.bat && install_run.bat

# 3. Configure MCP (Claude Code)
# Add to ~/.claude.json - see docs/MCP_GUIDE.md
```

</details>

---

## 🔌 MCP Tools

AI uses these tools **automatically** when MCP is configured:

| Tool | Function |
|------|----------|
| `memos_search` | Search project memories (auto-compresses >15 results) |
| `memos_save` | Save memories (BUGFIX, DECISION, MILESTONE...) |
| `memos_list_v2` | List all memories (with compression) |
| `memos_get` | Get full memory details by ID |
| `memos_get_graph` | Query knowledge graph relationships |

> 📖 Full setup: [MCP Configuration Guide](docs/MCP_GUIDE.md)

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [**🚀 Bundle Quick Start**](docs/QUICKSTART_BUNDLE.md) | One-click installation guide |
| [**🔌 MCP Guide**](docs/MCP_GUIDE.md) | MCP server setup & tools (EN/中文) |
| [**📦 Deployment Guide**](docs/DEPLOY_EN.md) | Full manual setup |
| [**📝 Changelog**](docs/CHANGELOG.md) | Version history |
| [**🔧 API Reference**](docs/product-api-tests.md) | Backend API docs |

---

## 🔗 Links

| Resource | Link |
|----------|------|
| **This Repo** | [lsg1103275794/MemOSLocal-SM](https://github.com/lsg1103275794/MemOSLocal-SM) |
| **Upstream** | [MemTensor/MemOS](https://github.com/MemTensor/MemOS) |
| **Neo4j** | [neo4j.com](https://neo4j.com) |
| **Qdrant** | [qdrant.tech](https://qdrant.tech) |
| **Ollama** | [ollama.ai](https://ollama.ai) |

---

<div align="center">

**Making AI Remember Every Project Decision** 🧠

*让 AI 记住你的每一个项目决策*

[![Star](https://img.shields.io/github/stars/lsg1103275794/MemOSLocal-SM?style=social)](https://github.com/lsg1103275794/MemOSLocal-SM)

MIT License · Copyright © 2026

</div>
