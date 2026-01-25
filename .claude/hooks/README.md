# MemOS Hooks

Claude Code hooks for enhanced memory integration.

## Available Hooks

| Script | Event | Purpose |
|--------|-------|---------|
| `memos_user_prompt` | UserPromptSubmit | Confirm memory system active |
| `memos_block_sensitive` | PreToolUse | Warn on sensitive file edits |
| `memos_log_commands` | PostToolUse | Log bash commands |
| `memos_notify_milestone` | PostToolUse | Suggest saving milestones |

## Platform Support

| Platform | Scripts | Config Example |
|----------|---------|----------------|
| **Linux/macOS/WSL** | `*.sh` (bash) | `settings.json` |
| **Windows** | `*.ps1` (PowerShell) | `settings.windows.json` |

## Installation

### Option 1: Linux / macOS / WSL

Copy `settings.json` to your project `.claude/` folder:

```bash
cp .claude/settings.json /your/project/.claude/settings.json
```

Or add to `~/.claude/settings.json` for global use.

### Option 2: Windows (PowerShell)

Copy `settings.windows.json` to `.claude/settings.json`:

```powershell
Copy-Item .claude\hooks\settings.windows.json .claude\settings.json
```

**Or manually configure** `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "powershell -ExecutionPolicy Bypass -File \"$CLAUDE_PROJECT_DIR\\.claude\\hooks\\memos_user_prompt.ps1\""
          }
        ]
      }
    ]
  }
}
```

## File Structure

```
.claude/hooks/
├── README.md                    # This file
├── settings.windows.json        # Windows config example
│
├── Linux/macOS/WSL (bash):
│   ├── memos_user_prompt.sh
│   ├── memos_block_sensitive.sh
│   ├── memos_log_commands.sh
│   └── memos_notify_milestone.sh
│
└── Windows (PowerShell):
    ├── memos_user_prompt.ps1
    ├── memos_user_prompt.cmd     # Simple batch version
    ├── memos_block_sensitive.ps1
    ├── memos_log_commands.ps1
    └── memos_notify_milestone.ps1
```

## Hook Descriptions

### memos_user_prompt.sh
- **Trigger**: Every user message
- **Action**: Returns success to confirm memory system is active
- **Output**: Silent (suppressed)

### memos_block_sensitive.sh
- **Trigger**: Before Edit/Write operations
- **Action**: Warns when editing sensitive files (.env, credentials, keys)
- **Output**: Warning message for sensitive files

### memos_log_commands.sh
- **Trigger**: After Bash commands
- **Action**: Logs command to `command_history.log`
- **Output**: Silent

### memos_notify_milestone.sh
- **Trigger**: After Edit/Write operations
- **Action**: Suggests saving milestone for important files
- **Files**: README.md, CHANGELOG.md, package.json, pyproject.toml, config.json

## Customization

Edit the scripts to customize behavior:

```bash
# Add more sensitive patterns
sensitive_patterns=(
    ".env"
    "credentials"
    "your_custom_pattern"
)

# Add more milestone files
milestone_files=(
    "README.md"
    "your_important_file.md"
)
```

## Debugging

Run Claude Code with debug flag:
```bash
claude --debug
```

## Related

- [MCP Guide](../../docs/MCP_GUIDE.md) - Proactive memory via MCP
- [CLAUDE.md](../../CLAUDE.md) - Project context
