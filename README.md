<div align="center">

# 🧠 MemOSLocal-SM

**Persistent Project Memory Solution for AI Assistants**

*让 AI 拥有持久记忆的项目级解决方案*

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![License](https://img.shields.io/badge/MemOS-Apache%202.0-green.svg)](https://github.com/MemTensor/MemOS)
[![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-lightgrey.svg)]()
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-orange.svg)]()
[![Neo4j](https://img.shields.io/badge/Neo4j-Knowledge%20Graph-blue.svg)](https://neo4j.com)
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

### ✨ Now, Try MemOSLocal-SM

<img src="https://img.shields.io/badge/-Before-red?style=for-the-badge" alt="Before"/>

**"AI forgets everything about the project in every new conversation"**

<img src="https://img.shields.io/badge/-After-green?style=for-the-badge" alt="After"/>

**"AI remembers every decision, every bug fix, every milestone"**

</div>

---

## 🎯 What is This?

MemOSLocal-SM is a complete **AI Project Memory Solution** that includes:

| Component | Description | Function |
|-----------|-------------|----------|
| **📦 memos-deploy** | MemOS Portable Deployment | One-click memory backend service |
| **🧠 project-memory** | Claude Code Skill | AI auto-save/search/track memories |
| **🔌 mcp-server** | MCP Protocol Server | AI **proactively** uses memory tools |

### 💡 Deploy Claude Skill (Recommended)

To give Claude **full awareness** of your project and enable **proactive memory tracking**, deploy the `project-memory` skill:

1. Create the directory `.claude/skills/project-memory/` in your project root.
2. Copy `project-memory/SKILL.md` to `.claude/skills/project-memory/SKILL.md`.

**Benefits:**
- **Zero Config**: Automatically derives `cube_id` from your project folder name.
- **Deep Awareness**: Claude will know it has "persistent memory" and proactively save milestones, architecture decisions, and bugfixes.
- **Smart Triggers**: Claude will automatically call `memos_search` when you ask "remember?" or "how did we do X?".

### Two Memory Modes

| Mode | Storage | Features | Best For |
|------|---------|----------|----------|
| **`general_text`** | Qdrant only | Vector similarity search | Simple projects, quick setup |
| **`tree_text`** | Neo4j + Qdrant | Knowledge graph + LLM extraction | Large projects, rich context |

```
                      ┌────────────────────────────────────┐
                      │           Your Project             │
                      └─────────────────┬──────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                        Claude Code + Integrations                         │
│                                                                           │
│   ┌───────────────────────────────┐   ┌───────────────────────────────┐   │
│   │    project-memory skill       │   │     MCP Server (memos)        │   │
│   │       (Passive Mode)          │   │     (Proactive Mode)          │   │
│   │                               │   │                               │   │
│   │  User calls /project-memory   │   │  AI auto-calls memos_search   │   │
│   │  to save/search memories      │   │  when encountering errors,    │   │
│   │                               │   │  making decisions, etc.       │   │
│   └───────────────┬───────────────┘   └───────────────┬───────────────┘   │
│                   │                                   │                   │
│                   └─────────────────┬─────────────────┘                   │
│                                     │                                     │
└─────────────────────────────────────┼─────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        MemOS Backend (localhost:18000)                   │
│                                                                          │
│   ┌─── Memory Mode ──────────────────────────────────────────────────┐   │
│   │                                                                  │   │
│   │   general_text (Flat)         tree_text (Knowledge Graph)        │   │
│   │   ┌───────────────┐          ┌──────────────────────────────┐    │   │
│   │   │    Qdrant     │          │        Save Pipeline         │    │   │
│   │   │   (Vector)    │          │                              │    │   │
│   │   │   Only        │          │  Input ──> LLM Extraction    │    │   │
│   │   └───────────────┘          │           (key, tags, conf.) │    │   │
│   │                              │               │              │    │   │
│   │                              │        ┌──────┴──────┐       │    │   │
│   │                              │        ▼             ▼       │    │   │
│   │                              │   ┌────────┐   ┌────────┐    │    │   │
│   │                              │   │ Neo4j  │   │ Qdrant │    │    │   │
│   │                              │   │(Graph) │   │(Vector)│    │    │   │
│   │                              │   └───┬────┘   └────────┘    │    │   │
│   │                              │       │                      │    │   │
│   │                              │       ▼                      │    │   │
│   │                              │  ┌─────────────────────┐     │    │   │
│   │                              │  │  Reorganizer (Async) │    │    │   │
│   │                              │  │  LLM detects links:  │    │    │   │
│   │                              │  │  CAUSE / CONDITION   │    │    │   │
│   │                              │  │  RELATE / CONFLICT   │    │    │   │
│   │                              │  └─────────────────────┘     │    │   │
│   │                              └──────────────────────────────┘    │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   ┌─── Services ─────────────────────────────────────────────────────┐   │
│   │                                                                  │   │
│   │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐  │   │
│   │  │ Qdrant       │  │   Neo4j      │  │   LLM (OpenAI API)     │  │   │
│   │  │ :6333        │  │   :7687      │  │   via Ollama :11434    │  │   │
│   │  │              │  │              │  │                        │  │   │
│   │  │ Embedding    │  │ Knowledge    │  │ 1. Memory Extraction   │  │   │
│   │  │ + Semantic   │  │ Graph +      │  │    (key/tags/conf.)    │  │   │
│   │  │   Search     │  │ Relationship │  │ 2. Relationship        │  │   │
│   │  │              │  │ Edges        │  │    Detection (Reorg.)  │  │   │
│   │  └──────────────┘  └──────────────┘  └────────────────────────┘  │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
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

## 🧠 Knowledge Graph Memory Mode (v0.4.0 Preview)

> **Upgrade from flat memory to intelligent knowledge graph!**

### What's Different?

| Feature | `general_text` (Flat) | `tree_text` (Knowledge Graph) |
|---------|----------------------|------------------------------|
| **Storage** | Qdrant vectors only | Neo4j graph + Qdrant vectors |
| **Structure** | Raw text | LLM-extracted: key, tags, background |
| **Memory Layers** | Single layer | WorkingMemory + LongTermMemory |
| **Confidence** | None | Auto-scoring (0.0 - 1.0) |
| **Relationships** | None | CAUSE / CONDITION / CONFLICT / RELATE |
| **Visualization** | None | Neo4j Browser graph view |

### How It Works

```
Memory Save Flow (tree_text mode):

     User Input: "[MILESTONE] Completed user authentication"
                                   │
                                   ▼
             ┌─────────────────────────────────────────┐
             │         ① LLM Memory Extraction         │
             │      (OpenAI-compatible API / Ollama)   │
             │                                         │
             │   Input:  raw text                      │
             │   Output: key, tags, background         │
             │   Evaluate: confidence (0.0 - 1.0)      │
             │   Classify: WorkingMemory / LongTerm    │
             └─────────────────────────────────────────┘
                                   │
                          ┌───────┴───────┐
                          ▼               ▼
                    ┌──────────┐    ┌──────────┐
                    │  Neo4j   │    │  Qdrant  │
                    │ (Graph   │    │ (Vector  │
                    │  Node)   │    │  Index)  │
                    └──────────┘    └──────────┘
                          │
                          ▼
             ┌─────────────────────────────────────────┐
             │    ② Reorganizer (Async Background)     │
             │                                         │
             │   1. Fetch new unprocessed nodes        │
             │   2. Compare with existing memories     │
             │   3. LLM analyzes pairwise relations    │
             │   4. Create relationship edges:         │
             │      CAUSE / CONDITION / RELATE /       │
             │      CONFLICT                           │
             │   5. Write edges back to Neo4j          │
             └─────────────────────────────────────────┘
```

```
Memory Search Flow (tree_text mode):

     User Query: "Why did Neo4j fail to start?"
                                   │
                          ┌───────┴───────┐
                          ▼               ▼
                    ┌──────────┐    ┌──────────┐
                    │  Qdrant  │    │  Neo4j   │
                    │ Semantic │    │  Graph   │
                    │  Search  │    │ Traverse │
                    └────┬─────┘    └────┬─────┘
                         │               │
                         └───────┬───────┘
                                 ▼
                    ┌──────────────────────┐
                    │  Merged Results      │
                    │                      │
                    │  Memories + Related  │
                    │  Nodes + Edges       │
                    │  (CAUSE chains,      │
                    │   CONDITION deps)    │
                    └──────────────────────┘
```

```
LLM Usage Summary:

  ┌──────────────────────────────────────────────────────────┐
  │                   LLM is used TWICE                      │
  ├──────────────────────────────────────────────────────────┤
  │                                                          │
  │  ① During Save (Extraction):                             │
  │     Raw text ──LLM──> key, tags, background, confidence  │
  │     Runs: synchronously on every save                    │
  │                                                          │
  │  ② During Reorganize (Relationship Detection):           │
  │     Memory A + Memory B ──LLM──> Relationship type       │
  │     Runs: asynchronously in background thread            │
  │     Detects: CAUSE, CONDITION, RELATE, CONFLICT          │
  │                                                          │
  └──────────────────────────────────────────────────────────┘
```

### Memory Node Structure

```json
{
  "key": "user_auth_complete",
  "memory": "Completed user authentication system with JWT",
  "background": "Project needed secure login for API access",
  "tags": ["auth", "jwt", "milestone", "security"],
  "confidence": 0.85,
  "memory_type": "MILESTONE",
  "status": "LongTermMemory"
}
```

### Quick Setup

1. **Install Neo4j Community Edition** (free):
   ```bash
   # Docker
   docker run -d -p 7474:7474 -p 7687:7687 neo4j:community

   # Or download: https://neo4j.com/download-center/
   ```

2. **Update `.env`**:
   ```env
   MOS_TEXT_MEM_TYPE=tree_text
   MOS_ENABLE_REORGANIZE=true

   NEO4J_BACKEND=neo4j-community
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   ```

3. **Visualize in Neo4j Browser** (http://localhost:7474):
   ```cypher
   -- View all memory nodes
   MATCH (n:Memory) RETURN n LIMIT 50

   -- Filter by tags
   MATCH (n:Memory) WHERE "auth" IN n.tags RETURN n
   ```

### Relationship Detection (Auto-Enabled)

When `MOS_ENABLE_REORGANIZE=true`, MemOS automatically detects relationships between memories:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Memory Relationship Types                    │
├──────────────┬──────────────────────────────────────────────────┤
│  CAUSE       │  A causes B (error → solution, bug → fix)        │
│  CONDITION   │  A is required for B (Java 17 → Neo4j runs)      │
│  RELATE      │  A and B are related (same feature, project)     │
│  CONFLICT    │  A contradicts B (old config ↔ new config)       │
└──────────────┴──────────────────────────────────────────────────┘
```

**Example: Auto-detected causal chain**
```
[Neo4j需要Java 17+]
    ──CAUSE──>
[Neo4j启动失败, JAVA_HOME not set]
```

**Query relationships with MCP:**
```python
# Use memos_get_graph tool
memos_get_graph(query="Neo4j")  # Returns all CAUSE/RELATE/CONFLICT for Neo4j
```

**Query in Neo4j Browser:**
```cypher
-- View all causal relationships
MATCH (a)-[r:CAUSE]->(b) RETURN a.memory, r, b.memory

-- Find what caused an error
MATCH (cause)-[:CAUSE]->(effect)
WHERE effect.memory CONTAINS "failed"
RETURN cause.memory AS root_cause
```

👉 **[Full Knowledge Graph Guide](docs/MCP_GUIDE.md#-advanced-neo4j-knowledge-graph-mode--高级-neo4j-知识图谱模式)**

### AI Graph Intelligence (New in v0.5.0)

> **Advanced AI capabilities for deeper knowledge graph understanding**

| Feature | Description | MCP Tool |
|---------|-------------|----------|
| **Triple Extraction** | Auto-extract (subject, predicate, object) from text | Integrated in save flow |
| **Path Tracing** | Find relationship paths between any two memories | `memos_trace_path` |
| **Context-Aware Search** | LLM analyzes search intent from conversation | `memos_search_context` |
| **Schema Export** | Graph statistics, health metrics, edge distribution | `memos_export_schema` |

**Path Tracing Example:**
```python
# Find how "login bug" relates to "JWT config"
memos_trace_path(source_query="login bug", target_query="JWT config", max_depth=5)

# Returns: paths with nodes and edges showing the relationship chain
```

**Context-Aware Search:**
```python
# Search with conversation history for better understanding
memos_search_context(
    query="Why did it fail?",
    context="We were discussing Neo4j startup issues",
    top_k=10
)
```

**Schema Health Check:**
```python
# Get graph health metrics
memos_export_schema(sample_size=100)

# Returns: total_nodes, orphan_ratio, avg_connections, edge_type_distribution
```

---

## 🔒 Privacy-First Architecture

> **Why "local" in MemOSLocal-SM?** Your sensitive data never leaves your machine.

```
┌───────────────────────────────────────────────────────────────────────┐
│  [LOCAL] YOUR MACHINE                                                 │
│                                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌───────────────────────────┐  │
│  │ Claude Code │───>│  MCP Server │───>│       MemOS API           │  │
│  │             │    │             │    │   (localhost:18000)       │  │
│  └─────────────┘    └─────────────┘    └─────────────┬─────────────┘  │
│                                                      │                │
│  ┌───────────────────────────────────────────┐       │                │
│  │  [Ollama] Local LLM + Embedding           │<──────┤                │
│  │                                           │       │                │
│  │  ① Embedding (nomic-embed-text):          │       │                │
│  │     "Fix login bug" → [0.23, -0.87, ...]  │       │                │
│  │                                           │       │                │
│  │  ② Memory Extraction (tree_text):         │       │                │
│  │     Raw text → {key, tags, confidence}    │       │                │
│  │                                           │       │                │
│  │  ③ Relationship Detection (Reorganizer):  │       │                │
│  │     Memory A + B → CAUSE/RELATE/...       │       │                │
│  │                                           │       │                │
│  │  * All LLM processing stays local         │       │                │
│  └───────────────────────────────────────────┘       │                │
│                                                      │                │
│  ┌───────────────────────────────────────────┐       │                │
│  │  [Neo4j] Knowledge Graph (localhost:7687)  │<──────┤               │
│  │                                           │       │                │
│  │  Nodes: Memory with key, tags, confidence │       │                │
│  │  Edges: CAUSE, CONDITION, RELATE, CONFLICT│       │                │
│  │                                           │       │                │
│  │  * 100% local, never leaves machine       │       │                │
│  └───────────────────────────────────────────┘       │                │
│                                                      │                │
└──────────────────────────────────────────────────────┼────────────────┘
                                                       │
                           Only numerical vectors      │
                           (no readable text)          v
┌───────────────────────────────────────────────────────────────────────┐
│  [CLOUD or LOCAL] QDRANT                                              │
│                                                                       │
│  Option A: Qdrant Cloud (cross-device sync)                           │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  ID: abc123  ->  [0.23, -0.87, 0.45, 0.12, ...]                 │  │
│  │  ID: def456  ->  [0.91, 0.33, -0.28, 0.67, ...]                 │  │
│  │  X Cannot reverse vectors to original text                      │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  Option B: Qdrant Local (localhost:6333, 100% offline)                │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  Same vector storage, but completely local                      │  │
│  │  * No data leaves your machine at all                           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

<table>
<tr>
<td width="50%" align="center">

### What Stays Local

- Original text content
- Code snippets
- API keys & secrets
- Error messages
- Embedding process (Ollama)
- **Neo4j knowledge graph (all nodes + edges)**
- **LLM extraction & relationship detection**

</td>
<td width="50%" align="center">

### What Goes to Cloud (Qdrant Cloud only)

- Numerical vectors only
- Memory IDs
- Timestamps
- **No readable text**
- **No source code**
- **No graph relationships**

</td>
</tr>
</table>

> **100% Local Mode**: Use local Qdrant + local Neo4j + Ollama for fully offline operation. Zero data leaves your machine.

### 🔌 MCP Configuration (Proactive Mode)

MCP (Model Context Protocol) allows AI to **proactively** use memory tools.

> 📖 **Full Setup Guide**: For detailed configuration on **Trae, Cursor, Windsurf, Claude Desktop, and more**, please refer to the [MCP Server Configuration Guide](docs/MCP_GUIDE.md).

**Example (Claude Code `~/.claude.json`):**

```json
{
  "mcpServers": {
    "memos": {
      "type": "stdio",
      "command": "G:/test/MemOS/conda_venv/python.exe",
      "args": ["G:/test/MemOS/mcp-server/memos_mcp_server.py"],
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

2. **Add to Claude Code settings** (`~/.claude.json` global or project-level):

   **For WSL environment** (recommended):
   ```json
   {
     "projects": {
       "/mnt/c/path/to/MemOS": {
         "mcpServers": {
           "memos": {
             "type": "stdio",
             "command": "bash",
             "args": ["/mnt/c/path/to/MemOS/mcp-server/run_mcp.sh"],
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
     }
   }
   ```

   **For pure Windows** (global `~/.claude.json`):
   ```json
   {
     "mcpServers": {
       "memos": {
         "type": "stdio",
         "command": "C:/path/to/MemOS/conda_venv/python.exe",
         "args": ["C:/path/to/MemOS/mcp-server/memos_mcp_server.py"],
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

   > **Note**: `alwaysAllow` enables AI to use these tools automatically without confirmation prompts. Remove tools from this list if you want manual approval.

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
| 🔗 User asks "why failed/dependencies" | Query knowledge graph relationships |

👉 **[Full MCP Guide](docs/MCP_GUIDE.md)**

### 🚀 Enhance with CLAUDE.md (Recommended)

Add a `CLAUDE.md` file to your project root for **project-specific context**:

```markdown
# My Project Guide

## Memory System
- Cube ID: `my_project_cube`
- Memory Mode: `tree_text`

## Auto Behaviors
- Search ERROR_PATTERN on errors
- Save MILESTONE after completing features
- Save DECISION for architecture choices

## Key Files
- `src/config.py` - Main configuration
- `src/auth/` - Authentication module
```

**Benefits**:
- Claude reads this at conversation start
- Project-specific memory triggers
- Consistent behavior across sessions

**Example**: See [CLAUDE.md](CLAUDE.md) in this project.

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
    ║               Project Progress Report                ║
    ║              my-awesome-project                      ║
    ╠══════════════════════════════════════════════════════╣
    ║                                                      ║
    ║     Completed Milestones (4)                         ║
    ║  ├── User authentication system       2025-01-15     ║
    ║  ├── Database schema design           2025-01-18     ║
    ║  ├── RESTful API framework            2025-01-20     ║
    ║  └── Unit test coverage 80%           2025-01-22     ║
    ║                                                      ║
    ║     Recent Fixes (2)                                 ║
    ║  ├── JWT token expiry issue           2025-01-20     ║
    ║  └── Session timeout config           2025-01-24     ║
    ║                                                      ║
    ║     Notes                                            ║
    ║  └── Docker container needs > 2GB RAM (OOM issue)    ║
    ║                                                      ║
    ║     Pending                                          ║
    ║  └── Add API rate limiting (mentioned last time)     ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
```

### Scenario 3: Cross-Project Memory Retrieval 🔥

> **Real demo from our development!** AI seamlessly retrieves memories across different projects.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [Project A] DDSP-SVC-6.0 (discussing skill implementation)             │
│                                                                         │
│  You: "How to configure Neo4j knowledge graph?"                         │
│                                                                         │
│  AI: [Automatically detects need for memory search]                     │
│                                                                         │
│      ┌─────────────────────────────────────────────────────────────┐    │
│      │  memos_search (MCP)                                         │    │
│      │  query: "Neo4j knowledge graph config"                      │    │
│      │                                                             │    │
│      │  [*] Searching across ALL projects...                       │    │
│      │                                                             │    │
│      │  [OK] Found in: dev_cube (MemOS project!)                   │    │
│      │  [Date] January 25, 2026 at 10:59 PM                        │    │
│      │  [Memo] "Updated README.md to showcase Neo4j Knowledge..."  │    │
│      └─────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  AI: Found relevant memory! Here's the Neo4j configuration:             │
│                                                                         │
│      tree_text mode requires:                                           │
│      - Neo4j Community Edition (bolt://localhost:7687)                  │
│      - MOS_TEXT_MEM_TYPE=tree_text in .env                              │
│      - Cube config with graph_db backend...                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Key Points:
   - Working in Project A, asking about Project B's config
   - AI automatically searches memory (no manual command!)
   - Cross-project knowledge retrieval works seamlessly
   • Zero context switching needed
```

<div align="center">

**🧠 One Memory System, All Your Projects**

*Screenshots: [docs/ScreenShot/README.md](docs/ScreenShot/README.md)*

</div>

---

## 📁 Project Structure

```
MemOSLocal-SM/
│
├── 📄 CLAUDE.md                        # 🆕 Project context for Claude Code
│
├── 📂 memos-deploy/                    # MemOS Portable Deployment
│   ├── 📂 docs/
│   │   ├── 📄 DEPLOY_CN.md            # Chinese Guide
│   │   └── 📄 DEPLOY_EN.md            # English Guide
│   ├── 🔧 setup_env.bat               # Setup Python environment (first time)
│   ├── 🔧 install_run.bat             # Install dependencies + start
│   └── 🔧 run.bat                     # Quick start (after setup)
│
├── 📂 mcp-server/                      # 🔌 MCP Protocol Server (Recommended!)
│   ├── 🐍 memos_mcp_server.py         # Main MCP server (8 tools)
│   ├── 🔧 run_mcp.sh                  # WSL wrapper script
│   ├── 🐍 install.py                  # Auto-configure Claude Code
│   ├── 🐍 test_server.py              # Test server functionality
│   ├── 📄 pyproject.toml              # Package configuration
│   └── 📄 README.md                   # MCP server documentation
│
├── 📂 project-memory/                  # 🧠 Claude Code Skill
│   ├── 📄 SKILL.md                    # MCP usage guide (v0.3.2+)
│   ├── 📄 README.md                   # English Docs
│   ├── 📄 README_CN.md                # Chinese Docs
│   │
│   └── 📂 scripts/
│       ├── 🐍 memos_utils.py          # Utility functions
│       └── 📂 legacy/                 # Archived (use MCP instead)
│           ├── 📄 README.md
│           ├── 🐍 memos_save.py
│           ├── 🐍 memos_search.py
│           └── 🐍 memos_init_project.py
│
├── 📂 docs/                            # 📖 Documentation
│   ├── 📄 CHANGELOG.md                # Version history
│   └── 📄 MCP_GUIDE.md                # MCP Server guide (EN/中文)
│
├── 📄 README.md                        # This file
├── 📄 pyproject.toml                   # Python package config
└── 📄 LICENSE
```

---

## 🛠️ Tools (MCP Recommended)

### MCP Tools (Recommended ✅)

With MCP configured, AI uses these tools **automatically**:

| Tool | Function | Auto-Trigger |
|------|----------|--------------|
| `memos_search` | Search memories | Error encountered, user says "previously" |
| `memos_save` | Save memories | Bug fixed, decision made, task completed |
| `memos_list` | List all memories | Check project status |
| `memos_list_v2` | List memories (enhanced) | Grouped by type with better formatting |
| `memos_get_stats` | Memory statistics | Overview of memory distribution |
| `memos_suggest` | Get search hints | Unsure what to search |
| `memos_get_graph` | Query knowledge graph | User asks "why failed", "dependencies" |
| `memos_trace_path` | Trace path between nodes | Find relationships between two memories |
| `memos_search_context` | Context-aware search | Search with conversation history analysis |
| `memos_export_schema` | Export graph schema | Get graph structure, health metrics |
| `memos_delete` | Delete memories | Cleanup test data (requires safety switch) |

```
No manual commands needed - AI handles everything!
```

### Legacy CLI Tools (Optional)

> **Note**: These scripts are archived in `scripts/legacy/`. Use MCP instead.

<details>
<summary>Click to see legacy CLI commands</summary>

```bash
# Initialize (now auto-handled by MCP)
python scripts/legacy/memos_init_project.py -p my-project

# Save (use memos_save MCP tool instead)
python scripts/legacy/memos_save.py "content" -t MILESTONE

# Search (use memos_search MCP tool instead)
python scripts/legacy/memos_search.py "keyword"
```

</details>

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description | Path Example (Windows) |
|----------|---------|-------------|------------------------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API URL | `http://localhost:18000` |
| `MEMOS_USER` | `dev_user` | Default user ID | `dev_user` |
| `MEMOS_DEFAULT_CUBE` | `dev_cube` | Default memory cube | `dev_cube` |
| `MEMOS_CUBES_DIR` | `./data/memos_cubes` | Cube storage directory | `G:/test/MemOS/data/memos_cubes` |
| `PYTHON_EXE` | - | Python executable path | `G:/test/MemOS/conda_venv/python.exe` |
| `CONDA_VENV` | - | Environment directory | `G:/test/MemOS/conda_venv` |

> **Note**: For Windows paths in `.env` or settings, use forward slashes `/` or double backslashes `\\` to avoid escape character issues.

### Memory Format

```markdown
[BUGFIX] Project: my-project | Date: 2026-01-26

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

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| **Python** | 3.10+ | 3.11+ | Required |
| **MemOS** | - | localhost:18000 | Required |
| **Ollama** | - | nomic-embed-text | Required for embedding |
| **Qdrant** | - | Cloud free tier | Required for vectors |
| **Neo4j** | - | Community Edition | Optional: for `tree_text` mode |
| **Memory** | 4GB | 8GB+ | - |

---

## 📖 Documentation

### Quick Navigation

| Document | Description | Language |
|----------|-------------|----------|
| [**CLAUDE.md**](CLAUDE.md) | Project context for Claude Code | English |
| [**Changelog**](docs/CHANGELOG.md) | Project updates and fixes | English |
| [**🔌 MCP Server Guide**](docs/MCP_GUIDE.md) | Proactive memory integration | EN/中文 |
| [**Deployment Guide**](memos-deploy/docs/DEPLOY_EN.md) | Full setup: environment, database, embedding, LLM | English |
| [**部署指南**](memos-deploy/docs/DEPLOY_CN.md) | 完整部署：环境、数据库、嵌入模型、LLM | 中文 |
| [**Skill README**](project-memory/README.md) | Claude Code skill usage | English |
| [**技能说明**](project-memory/README_CN.md) | Claude Code 技能使用说明 | 中文 |
| [**Memory Examples**](project-memory/references/examples.md) | Memory format templates | English |

---

## 🔗 Repository

- **Main Repo**: [https://github.com/lsg1103275794/MemOSLocal-SM](https://github.com/lsg1103275794/MemOSLocal-SM)
- **Original Project**: [BAI-LAB/MemoryOS](https://github.com/BAI-LAB/MemoryOS)

---

<div align="center">

**MemOSLocal-SM** • Privacy-First Persistent Memory for AI

Copyright © 2026 lsg1103275794. Licensed under the [MIT License](LICENSE).

</div>

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
<a href="https://neo4j.com">
<img src="https://img.shields.io/badge/Neo4j-Graph%20DB-blue?style=for-the-badge" alt="Neo4j"/>
</a>
<br/>Knowledge Graph
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

| 问题 | 症状 | MemOSLocal-SM 解决方案 |
|------|------|---------------------|
| **📝 文档臃肿** | AI 到处写 NOTES.md、TODO.md，项目越来越乱 | 统一存储到向量数据库，项目保持整洁 |
| **🧠 记忆断层** | 新对话就忘光，"之前为什么选 Redis？" | 语义搜索自动召回相关决策记忆 |
| **🔁 重蹈覆辙** | 同样的 Bug 修了三遍，AI 记吃不记打 | ERROR_PATTERN 自动匹配，主动提醒解决方案 |

### 这是什么？

MemOSLocal-SM 是一套完整的 **AI 项目记忆解决方案**：

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
| 🧠 **知识图谱模式** | Neo4j + LLM 提炼，智能记忆管理 |

### 🧠 知识图谱记忆模式 (v0.4.0 预览)

| 特性 | `general_text` (扁平) | `tree_text` (知识图谱) |
|------|----------------------|------------------------|
| **存储** | 仅 Qdrant 向量 | Neo4j 图 + Qdrant 向量 |
| **结构** | 原始文本 | LLM 提炼: key, tags, background |
| **记忆层级** | 单层 | WorkingMemory + LongTermMemory |
| **置信度** | 无 | 自动评分 (0.0 - 1.0) |
| **关系检测** | 无 | CAUSE / RELATE / CONFLICT / CONDITION |
| **可视化** | 无 | Neo4j Browser 图谱查看 |

```env
# 启用知识图谱模式
MOS_TEXT_MEM_TYPE=tree_text
MOS_ENABLE_REORGANIZE=true
NEO4J_URI=bolt://localhost:7687
```

#### 🔗 自动依赖关系检测

当 `MOS_ENABLE_REORGANIZE=true` 时，MemOS 自动检测记忆之间的关系：

| 关系类型 | 含义 | 示例 |
|----------|------|------|
| **CAUSE** | A 导致 B | 缺少Java → Neo4j启动失败 |
| **CONDITION** | A 是 B 的前提 | Java 17 → Neo4j可运行 |
| **RELATE** | A 和 B 相关 | 同一功能的不同记录 |
| **CONFLICT** | A 和 B 矛盾 | 旧配置 ↔ 新配置 |

**示例：自动检测的因果链**
```
[Neo4j需要Java 17+]
    ──CAUSE──>
[Neo4j启动失败, JAVA_HOME not set]
```

**使用 MCP 查询关系：**
```python
memos_get_graph(query="Neo4j")  # 返回所有与Neo4j相关的 CAUSE/RELATE/CONFLICT
```

### 🔒 隐私优先架构

> **为什么叫 "local"？** 你的敏感数据永远不会离开你的电脑。

```
+-------------------------------------------------------------------+
|  [LOCAL] Your Machine                                             |
|                                                                   |
|    Original text: "Fix login bug in auth.py"                      |
|                            |                                      |
|                            v                                      |
|    Ollama local embedding: [0.23, -0.87, 0.45, 0.12, ...]         |
|                            |                                      |
|                            v                                      |
|    * Text stays local  ->  [CLOUD] Only vectors uploaded          |
|                                                                   |
+-------------------------------------------------------------------+
```

| 🏠 本地保留 | ☁️ 上传云端 |
|-------------|-------------|
| ✅ 原始文本内容 | ⭕ 仅数值向量 |
| ✅ 代码片段 | ⭕ 记忆 ID |
| ✅ API 密钥等敏感信息 | ❌ **无可读文本** |
| ✅ Embedding 计算过程 | ❌ **无源代码** |

> 向量无法反向还原为原始文本，你的隐私得到保护！

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
| `memos_list_v2` | 列出记忆(增强) | 按类型分组显示 |
| `memos_get_stats` | 记忆统计 | 查看记忆分布概况 |
| `memos_suggest` | 搜索建议 | 不确定搜什么 |
| `memos_get_graph` | 查询知识图谱 | 用户问"为什么失败"、"依赖关系" |
| `memos_trace_path` | 追踪节点路径 | 查找两个记忆之间的关系路径 |
| `memos_search_context` | 上下文感知搜索 | 带对话历史分析的智能搜索 |
| `memos_export_schema` | 导出图谱Schema | 获取图谱结构和健康度指标 |
| `memos_delete` | 删除记忆 | 清理测试数据（需启用安全开关） |

### 💡 部署 Claude 技能 (Skills)

如果你在 Claude 环境中使用，可以将 `project-memory/SKILL.md` 复制到项目的 `.claude/skills/project-memory/SKILL.md`。

**优势**:
- **智能感知**: Claude 会自动识别 `project-memory` 技能。
- **核心意识**: 它会意识到自己拥有“持久化记忆”，并主动记录项目架构、决策和进度。
- **自动隔离**: 根据项目目录自动推导 `cube_id`，实现零配置的项目记忆隔离。

### MCP 配置示例

本部分展示了适用于通用 IDE (如 Claude Desktop, Cursor, VS Code 等) 的标准 MCP 服务器配置。

**通用 MCP 客户端配置示例** (如各项IDE的 `mcp.json`):

```json
{
  "mcpServers": {
    "memos": {
      "command": "C:/path/to/MemOS/conda_venv/python.exe",
      "args": [
        "-u",
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
        "MEMOS_ENABLE_DELETE": "true",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

> **📸 演示效果**: 本项目提供的截图 (如 Cherry Studio 系列) 展示了在 **Cherry Studio** 客户端中使用 **GLM-4.7** 模型调用 MemOS MCP 工具的实际演示效果。MemOS 具有极佳的跨客户端适配性，支持所有遵循 MCP 协议的 AI 助手。

### 🚀 使用 CLAUDE.md 增强 (推荐)

在项目根目录创建 `CLAUDE.md` 提供项目上下文：

```markdown
# 我的项目指南

## 记忆配置
- Cube ID: `my_project_cube`
- 记忆模式: `tree_text`

## 关键文件
- `src/config.py` - 主配置
```

**好处**: Claude 会在对话开始时读取，提供项目特定上下文。

👉 [MCP 配置指南](docs/MCP_GUIDE.md) | [完整中文文档](project-memory/README_CN.md)

</details>

---

## 🤝 Contributing

Contributions welcome! Please check out our [Contributing Guide](CONTRIBUTING.md).

---

<div align="center">

**Making AI Remember Every Project Decision** 🧠

*让 AI 记住你的每一个项目决策*

[![Star](https://img.shields.io/github/stars/lsg1103275794/MemOSLocal-SM?style=social)](https://github.com/lsg1103275794/MemOSLocal-SM)

</div>
