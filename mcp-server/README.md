# MemOS MCP Server

MCP (Model Context Protocol) Server for MemOS, enabling Claude Code to **proactively** search and save project memories.

## Features

### Core Tools
- 🔍 **memos_search** - Search project memories with intelligent context
- 🔍 **memos_search_context** - Context-aware search with conversation history
- 💾 **memos_save** - Save important decisions, errors, patterns
- 📋 **memos_list** / **memos_list_v2** - List all memories in a project
- 💡 **memos_suggest** - Get smart search suggestions
- 📊 **memos_get_stats** - Get memory statistics by type

### Knowledge Graph Tools
- 🧠 **memos_get_graph** - Query knowledge graph with relationships (CAUSE/RELATE/CONFLICT)
- 🔗 **memos_trace_path** - Trace reasoning paths between two memory nodes
- 📈 **memos_export_schema** - Export knowledge graph schema and statistics

### Admin Tools
- 📦 **memos_list_cubes** - List all available memory cubes
- ✅ **memos_register_cube** - Manually register a cube with the API
- 👤 **memos_create_user** - Create a user in MemOS
- 🔧 **memos_validate_cubes** - Validate and fix cube configurations
- 🗑️ **memos_delete** - Delete memories (disabled by default)

## Architecture

The MCP server is organized into modular components:

```
mcp-server/
├── memos_mcp_server.py   # Entry point (~100 lines)
├── config.py             # Configuration, CLI args, constants
├── api_client.py         # HTTP client, retry logic
├── cube_manager.py       # Cube discovery, registration, validation
├── formatters.py         # Display formatting for memories/graphs
├── memory_analysis.py    # Type detection, suggestions
├── query_processing.py   # Keyword extraction, reranking, filtering
├── tools_registry.py     # All 15 MCP tool definitions
├── handlers/             # Tool handlers by category
│   ├── __init__.py       # Dispatcher and registry
│   ├── utils.py          # Shared utilities
│   ├── search.py         # Search tools
│   ├── memory.py         # Memory CRUD tools
│   ├── graph.py          # Knowledge graph tools
│   └── admin.py          # Admin/management tools
├── keyword_enhancer.py   # Enhanced keyword matching
└── test_server.py        # Test suite
```

## Installation

### 1. Install dependencies

```bash
# Option 1: Install from mcp-server directory
cd mcp-server
pip install -e .

# Option 2: Direct pip install
pip install mcp httpx pydantic python-dotenv

# Option 3: Using project optional dependencies
pip install MemoryOS[mcp-server]
```

### 2. Configure Claude Code

Claude Code MCP config is stored in `~/.claude.json` under the `projects` field.

#### WSL Environment (Recommended)

In WSL, use the bash wrapper script to handle path translation:

Add to `~/.claude.json` under your project's `mcpServers`:

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

The wrapper script (`run_mcp.sh`) handles WSL/Windows path translation:
- Uses WSL path to invoke Windows Python: `/mnt/g/.../python.exe`
- Passes Windows-format path to Python: `G:/test/.../script.py`

#### Pure Windows (Non-WSL)

```json
{
  "mcpServers": {
    "memos": {
      "type": "stdio",
      "command": "G:/test/MemOS/.venv/Scripts/python.exe",
      "args": ["G:/test/MemOS/mcp-server/memos_mcp_server.py"],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube"
      }
    }
  }
}
```

#### Linux / macOS

```json
{
  "mcpServers": {
    "memos": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/MemOS/mcp-server/memos_mcp_server.py"],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube"
      }
    }
  }
}
```

### 3. Restart Claude Code

The tools will be automatically available.

## Tools

### memos_search

Search project memories. Claude will use this **proactively** when:

- Encountering errors → searches for `ERROR_PATTERN`
- User mentions "之前", "上次" → searches history
- Modifying code → searches for `GOTCHA` and `CODE_PATTERN`
- Working with config → searches for `CONFIG`

### memos_search_context

Context-aware search that analyzes conversation history to understand intent:

```python
# Example: After discussing "login errors", searching "what was the solution?"
# will understand you mean "login error solution"
```

### memos_save

Save memories with explicit type specification:

```python
# ✅ Correct - explicit type
memos_save(content="Fixed path issue...", memory_type="BUGFIX")

# ❌ Avoid - relies on auto-detection
memos_save(content="Fixed path issue...")  # defaults to PROGRESS
```

### memos_trace_path

Trace reasoning paths between memory nodes:

```
[Java not installed] ──CAUSE──> [Neo4j failed] ──CAUSE──> [API timeout]
```

### Memory Types

| Type | Usage |
|------|-------|
| `ERROR_PATTERN` | Error + solution for future reference |
| `DECISION` | Architectural choice with rationale |
| `MILESTONE` | Significant achievement |
| `BUGFIX` | Bug fix details |
| `FEATURE` | New functionality |
| `CONFIG` | Configuration change |
| `CODE_PATTERN` | Reusable code template |
| `GOTCHA` | Non-obvious issue |
| `PROGRESS` | General update (use sparingly) |

**Best Practice**: Always explicitly specify `memory_type` to enable richer knowledge graph relationships.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMOS_URL` | (required) | MemOS API URL |
| `MEMOS_USER` | (required) | Default user ID |
| `MEMOS_DEFAULT_CUBE` | (required) | Default memory cube |
| `MEMOS_CUBES_DIR` | (required) | Cube storage directory |
| `MEMOS_TIMEOUT_TOOL` | `120.0` | Tool call timeout (seconds) |
| `MEMOS_TIMEOUT_STARTUP` | `30.0` | Startup cube registration timeout |
| `MEMOS_TIMEOUT_HEALTH` | `5.0` | Health check timeout |
| `MEMOS_API_WAIT_MAX` | `60.0` | Max wait time for API ready |
| `MEMOS_ENABLE_DELETE` | `false` | Enable delete functionality |
| `NEO4J_HTTP_URL` | (optional) | Neo4j HTTP endpoint for graph queries |
| `NEO4J_USER` | (optional) | Neo4j username |
| `NEO4J_PASSWORD` | (optional) | Neo4j password |

## Safety: Delete Functionality

The `memos_delete` tool is **DISABLED by default** to prevent accidental data loss.

To enable deletion, explicitly set in your MCP config:

```json
"env": {
  "MEMOS_ENABLE_DELETE": "true"
}
```

**Safety features:**
- Tool is hidden from AI when disabled
- Requires explicit user confirmation
- Supports single memory or bulk deletion
- AI is instructed to always confirm before deleting

## Auto-Registration & Auto-Creation

The MCP server automatically handles cube management for new projects:

### Auto-Creation (New in v2.0)

When you start using MCP in a new project, the server automatically:

1. **Derives cube_id from project folder** (e.g., `my-project` → `my_project_cube`)
2. **Checks if cube exists** in the cubes directory
3. **Auto-creates cube** by cloning config from `dev_cube` template
4. **Registers with MemOS API** for immediate use

```
First call to memos_search/save/list
        ↓
Cube not found? Auto-create from template (dev_cube)
        ↓
Auto-register via /mem_cubes API
        ↓
Continue with original operation
```

**Requirements:**
- `dev_cube` must exist as template (or any cube in `MEMOS_CUBES_DIR`)
- Cubes directory must be writable

### Auto-Registration

If cube directory exists but not registered:

```
First call to memos_search/save/list
        ↓
Check if cube is registered
        ↓ (not registered)
Auto-register via /mem_cubes API
        ↓
Continue with original operation
```

If auto-registration fails, use `memos_list_cubes` to see available cubes and `memos_register_cube` to manually register.

## Cube Configuration Validation

Use `memos_validate_cubes` to check and fix configuration issues:

```python
# Check all cubes and auto-fix mismatches
memos_validate_cubes(fix=True)
```

This prevents issues where memories are saved to the wrong namespace.

## Testing

```bash
# Test the server directly
cd mcp-server
python test_server.py

# Test module imports
python -c "from handlers import dispatch_tool; print('OK')"

# Via MCP inspector
npx @anthropic-ai/mcp-inspector python memos_mcp_server.py
```

## Development

### Adding a New Tool

1. Add tool definition in `tools_registry.py`
2. Create handler in appropriate `handlers/*.py` file
3. Register handler in `handlers/__init__.py` HANDLER_REGISTRY
4. Test with `python -m py_compile` on all modified files

### Module Dependencies

```
memos_mcp_server.py
    ├── config.py (constants, server instance)
    ├── api_client.py (HTTP client)
    ├── cube_manager.py (cube operations)
    ├── tools_registry.py (tool definitions)
    └── handlers/ (tool implementations)
            ├── formatters.py
            ├── memory_analysis.py
            └── query_processing.py
```
