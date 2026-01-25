# MemOS Project Guide

> This file provides project-specific context to Claude Code.

---

## Project Overview

**MemOS** is a persistent project memory solution for AI assistants, featuring:

- **MCP Server**: Proactive memory tools (memos_search, memos_save, memos_list, memos_suggest)
- **Neo4j Knowledge Graph**: Structured memory with relationships (tree_text mode)
- **Qdrant Vector Database**: Semantic similarity search
- **LLM Memory Extraction**: Auto-extract key, tags, background, confidence

---

## Memory System (MCP)

### Automatic Behaviors

The MCP tools are configured to trigger automatically. You should:

| Situation | Action | Example |
|-----------|--------|---------|
| **Encounter error** | Search ERROR_PATTERN | `memos_search("ERROR_PATTERN ModuleNotFoundError")` |
| **User says "之前/上次/previously"** | Search history | `memos_search("authentication history")` |
| **Before modifying critical files** | Search GOTCHA | `memos_search("GOTCHA config.py")` |
| **After fixing bug** | Save ERROR_PATTERN | `memos_save("[ERROR_PATTERN] Fixed...")` |
| **After completing task** | Save MILESTONE | `memos_save("[MILESTONE] Completed...")` |
| **After making decision** | Save DECISION | `memos_save("[DECISION] Chose X because...")` |
| **Discover non-obvious issue** | Save GOTCHA | `memos_save("[GOTCHA] Watch out for...")` |

### Memory Types

| Type | Usage | Example |
|------|-------|---------|
| `ERROR_PATTERN` | Error + solution for future reference | "ModuleNotFoundError: pip install missing-package" |
| `DECISION` | Architecture/design choice with rationale | "Chose JWT over sessions for stateless API" |
| `MILESTONE` | Significant project achievement | "Completed user authentication system" |
| `BUGFIX` | Bug fix with cause and solution | "Fixed login timeout - SESSION_TIMEOUT was 30s" |
| `FEATURE` | New functionality added | "Added dark mode support" |
| `CONFIG` | Environment or configuration change | "Updated .env for Qdrant Cloud" |
| `CODE_PATTERN` | Reusable code template | "Neo4j query pattern for memory search" |
| `GOTCHA` | Non-obvious issue or workaround | "WSL paths need bash wrapper for Windows Python" |

---

## Project Configuration

### Memory Cube
- **Cube ID**: `dev_cube`
- **Storage Path**: `data/memos_cubes/dev_cube`

### Memory Mode
- **Backend**: `tree_text` (Knowledge Graph)
- **Graph DB**: Neo4j Community Edition
- **Vector DB**: Qdrant Cloud

### Neo4j Access
- **URI**: `bolt://localhost:7687`
- **Browser**: http://localhost:7474
- **Useful Queries**:
  ```cypher
  -- View all memories
  MATCH (n:Memory) RETURN n LIMIT 50

  -- Filter by type
  MATCH (n:Memory) WHERE n.memory_type = "MILESTONE" RETURN n

  -- Search by tags
  MATCH (n:Memory) WHERE "auth" IN n.tags RETURN n
  ```

### API Endpoints
- **Base URL**: http://localhost:18000
- **Docs**: http://localhost:18000/docs

---

## Key Files

| File | Purpose |
|------|---------|
| `.env` | Environment configuration (Qdrant, Neo4j, LLM) |
| `mcp-server/memos_mcp_server.py` | MCP server implementation |
| `mcp-server/run_mcp.sh` | WSL wrapper script |
| `data/memos_cubes/dev_cube/config.json` | Cube configuration |
| `src/memos/graph_dbs/neo4j_community.py` | Neo4j Community backend |
| `docs/MCP_GUIDE.md` | MCP configuration guide |
| `docs/CHANGELOG.md` | Version history |

---

## Recent Milestones

> These are automatically tracked. Search with `memos_list()` for full history.

- **2026-01-26**: Neo4j Knowledge Graph mode enabled (tree_text)
- **2026-01-26**: Cross-project memory retrieval verified
- **2026-01-26**: MCP proactive mode working
- **2026-01-26**: README updated with new architecture

---

## Development Notes

### WSL Environment
When working in WSL with Windows Python:
- Use `bash` wrapper script for MCP
- Windows paths need `G:/...` format for Python
- WSL paths need `/mnt/g/...` format for bash

### Memory Best Practices
1. **Be specific** in memory content - include file paths, line numbers
2. **Use tags** for better searchability
3. **Include context** - why, not just what
4. **Save immediately** after significant work

---

## Quick Commands

```bash
# Start MemOS API
cd /mnt/g/test/MemOS && ./run.bat

# Test MCP server
cd mcp-server && python test_server.py

# View Neo4j Browser
open http://localhost:7474

# Check API health
curl http://localhost:18000/users
```

---

*This file is read by Claude Code at conversation start to provide project context.*
