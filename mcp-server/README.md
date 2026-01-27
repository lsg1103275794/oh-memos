# MemOS MCP Server

MCP (Model Context Protocol) Server for MemOS, enabling Claude Code to **proactively** search and save project memories.

## Features

- 🔍 **memos_search** - Search project memories with intelligent context
- 💾 **memos_save** - Save important decisions, errors, patterns
- 📋 **memos_list** - List all memories in a project
- 💡 **memos_suggest** - Get smart search suggestions
- 🧠 **memos_get_graph** - Query knowledge graph with relationships (CAUSE/RELATE/CONFLICT)
- 🗑️ **memos_delete** - Delete memories (⚠️ disabled by default, requires `MEMOS_ENABLE_DELETE=true`)

## Installation

### 1. Install dependencies

```bash
# Option 1: Install from mcp-server directory
cd mcp-server
pip install -e .

# Option 2: Direct pip install
pip install mcp httpx pydantic

# Option 3: Using project optional dependencies
pip install MemoryOS[mcp-server]
```

### 2. Configure Claude Code

Claude Code MCP config is stored in `~/.claude.json` under the `projects` field.

#### WSL Environment (Recommended)

⚠️ **Important**: In WSL, use the bash wrapper script to handle path translation:

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
      "command": "G:/test/MemOS/conda_venv/python.exe",
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

### memos_save

Save memories. Claude will use this when:

- Solving a bug → saves as `ERROR_PATTERN`
- Making decisions → saves as `DECISION`
- Completing tasks → saves as `MILESTONE`

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
| `PROGRESS` | General update |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API URL |
| `MEMOS_USER` | `dev_user` | Default user ID |
| `MEMOS_DEFAULT_CUBE` | `dev_cube` | Default memory cube |
| `MEMOS_CUBES_DIR` | `G:/test/MemOS/data/memos_cubes` | Cube storage directory (for auto-registration) |
| `MEMOS_TIMEOUT_TOOL` | `120.0` | Tool call timeout (seconds) - for large documents with embedding |
| `MEMOS_TIMEOUT_STARTUP` | `30.0` | Startup cube registration timeout (seconds) |
| `MEMOS_TIMEOUT_HEALTH` | `5.0` | Health check timeout (seconds) |
| `MEMOS_API_WAIT_MAX` | `60.0` | Max wait time for API ready (seconds) |
| `MEMOS_ENABLE_DELETE` | `false` | ⚠️ Enable delete functionality (dangerous, disabled by default) |

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

## Auto-Registration

The MCP server automatically registers cubes on first use. No manual setup required!

```
First call to memos_search/save/list
        ↓
Check if cube is registered
        ↓ (not registered)
Auto-register via /mem_cubes API
        ↓
Continue with original operation
```

## Testing

```bash
# Test the server directly
python memos_mcp_server.py

# Or via MCP inspector
npx @anthropic-ai/mcp-inspector python memos_mcp_server.py
```
