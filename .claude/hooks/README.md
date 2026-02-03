# MemOS Hooks

Claude Code hooks for enhanced memory integration.

## Available Hooks

| Script | Event | Purpose |
|--------|-------|---------|
| `memos_user_prompt` | UserPromptSubmit | **Smart intent detection** - suggests memory actions |
| `memos_block_sensitive` | PreToolUse | **Tiered sensitivity guard** - warns on sensitive edits |
| `memos_log_commands` | PostToolUse | Log bash commands |
| `memos_auto_save` | PostToolUse | **Smart save suggestions** - context-aware reminders |
| `memos_notify_milestone` | PostToolUse | Suggest saving milestones |

## Smart Intent Detection (memos_user_prompt)

The enhanced `memos_user_prompt` hook analyzes user prompts and suggests relevant memory actions:

| Intent | Trigger Keywords | Suggestion |
|--------|------------------|------------|
| **History Query** | 之前, 上次, previously, how did we | `memos_search` for past work |
| **Error Report** | error, 错误, failed, bug, traceback | `memos_search(ERROR_PATTERN)` |
| **Decision Making** | 应该用, should we use, vs, 方案 | Save as `DECISION` |
| **Task Completion** | 完成了, fixed, implemented | Save as `MILESTONE/BUGFIX/FEATURE` |
| **Relationship Query** | 为什么失败, what caused, 依赖 | `memos_get_graph` |
| **Status Query** | 进度, progress, 总结 | `memos_list` |
| **Config Topic** | 配置, config, 环境变量 | Save as `CONFIG` |

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

### memos_user_prompt (Enhanced)
- **Trigger**: Every user message
- **Action**: Analyzes prompt for intent patterns
- **Detects**: 7 intent types (history, error, decision, completion, relationship, status, config)
- **Output**: Memory hints when relevant patterns detected (max 2 suggestions)
- **Example Output**:
  ```
  🧠 Memory hints:
  → Consider: memos_search(query="ERROR_PATTERN ...") for past solutions
  → Consider saving: MILESTONE (big feature) / BUGFIX (fix) / FEATURE (new)
  ```

### memos_block_sensitive (Enhanced)
- **Trigger**: Before Edit/Write operations
- **Action**: Smart sensitivity detection with tiered warnings
- **Levels**:
  - 🚨 CRITICAL: SSH keys, certificates, cloud credentials → strong warning
  - ⚠️ HIGH: .env, passwords, secrets → warning + save reminder
  - ⚙️ MEDIUM: Config files → save reminder
  - 📦 LOW: Generated files (lock files, dist/) → overwrite warning
- **Example Output**:
  ```
  🚨 CRITICAL: Editing SSH private key file!
     File: ~/.ssh/id_rsa
     → NEVER commit this file to git!
  ```

### memos_log_commands
- **Trigger**: After Bash commands
- **Action**: Logs command to `~/.claude/hooks/command_history.log`
- **Output**: Silent

### memos_notify_milestone
- **Trigger**: After Edit/Write operations
- **Action**: Suggests saving milestone for important files
- **Files**: README.md, CHANGELOG.md, package.json, pyproject.toml, config.json

### memos_auto_save (New)
- **Trigger**: After Bash/Edit/Write operations
- **Action**: Smart context analysis with save suggestions
- **Detects**:
  - Config file edits → suggest `CONFIG`
  - Project file edits (README, package.json) → suggest `MILESTONE`
  - Test file edits → suggest `BUGFIX` if fixing
  - Command failures → suggest `memos_search(ERROR_PATTERN)`
  - Successful fixes/tests → suggest `BUGFIX`
  - Package installs → suggest `CONFIG`
- **Example Output**:
  ```
  ❌ Command failed → Consider: memos_search(query="ERROR_PATTERN <error>") for solutions
  ✅ Tests passed → If this fixed something: memos_save(..., memory_type="BUGFIX")
  ```

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
