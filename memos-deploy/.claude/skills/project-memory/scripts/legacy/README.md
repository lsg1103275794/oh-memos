# Legacy Scripts (Archived)

These scripts have been **superseded by MCP Server** (v0.3.0+).

## Why Archived?

The MCP Server now provides all functionality:

| Legacy Script | MCP Replacement |
|---------------|-----------------|
| `memos_init_project.py` | Auto-registration in MCP |
| `memos_save.py` | `memos_save` tool |
| `memos_search.py` | `memos_search` tool |

## When to Use These?

Only if:
1. MCP is not configured
2. You need command-line access without Claude Code
3. Debugging MCP issues

## Usage (if needed)

```bash
# These still work but MCP is preferred
python legacy/memos_init_project.py -p my-project
python legacy/memos_save.py "content" -t MILESTONE
python legacy/memos_search.py "query"
```

## Recommended Approach

Use MCP tools instead - they're faster, auto-register cubes, and integrate seamlessly with Claude Code.
