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

| Platform | Scripts | Config |
|----------|---------|--------|
| **Cross-platform (Recommended)** | `*.js` (Node.js) | `settings.crossplatform.json` |
| **Linux/macOS/WSL** | `*.sh` (bash) | `settings.json` |
| **Windows** | `*.ps1` (PowerShell) | `settings.windows.json` |

## Installation

### Option 1: Cross-platform (Recommended)

Works in **both Windows and WSL** without changes:

```bash
# Copy to your project
cp settings.crossplatform.json /your/project/.claude/settings.json
cp memos_*.js /your/project/.claude/hooks/
```

The Node.js scripts auto-detect the platform:
```javascript
process.platform === 'win32'
  ? 'G:/path/to/script.js'    // Windows
  : '/mnt/g/path/to/script.js' // WSL/Linux
```

### Option 2: Linux / macOS / WSL

Copy `settings.json` to your project `.claude/` folder:

```bash
cp settings.json /your/project/.claude/settings.json
```

### Option 3: Windows (PowerShell)

Copy `settings.windows.json` to `.claude/settings.json`:

```powershell
Copy-Item settings.windows.json ..\..\..\.claude\settings.json
```

## File Structure

```
project-memory/hooks/
├── README.md                     # This file
├── settings.crossplatform.json   # Cross-platform config (Node.js)
├── settings.windows.json         # Windows-only config (PowerShell)
│
├── Cross-platform (Node.js):
│   ├── memos_user_prompt.js
│   ├── memos_block_sensitive.js
│   ├── memos_log_commands.js
│   └── memos_notify_milestone.js
│
├── Linux/macOS/WSL (bash):
│   ├── memos_user_prompt.sh
│   ├── memos_block_sensitive.sh
│   ├── memos_log_commands.sh
│   └── memos_notify_milestone.sh
│
└── Windows (PowerShell):
    ├── memos_user_prompt.ps1
    ├── memos_user_prompt.cmd
    ├── memos_block_sensitive.ps1
    ├── memos_log_commands.ps1
    └── memos_notify_milestone.ps1
```

## Hook Descriptions

### memos_user_prompt
- **Trigger**: Every user message
- **Action**: Returns success to confirm memory system is active
- **Output**: Silent (suppressed)

### memos_block_sensitive
- **Trigger**: Before Edit/Write operations
- **Action**: Warns when editing sensitive files (.env, credentials, keys)
- **Output**: Warning message for sensitive files

### memos_log_commands
- **Trigger**: After Bash commands
- **Action**: Logs command to `~/.claude/hooks/command_history.log`
- **Output**: Silent

### memos_notify_milestone
- **Trigger**: After Edit/Write operations
- **Action**: Suggests saving milestone for important files
- **Files**: README.md, CHANGELOG.md, package.json, pyproject.toml, config.json

## Customization

### Node.js (Cross-platform)

Edit `memos_block_sensitive.js`:
```javascript
const sensitivePatterns = [
  '.env',
  'credentials',
  'your_custom_pattern'  // Add here
];
```

### Bash

Edit `memos_block_sensitive.sh`:
```bash
sensitive_patterns=(
    ".env"
    "credentials"
    "your_custom_pattern"
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
