# Project Memory Skill

A proactive project memory management skill for Claude Code, powered by [MemOS](https://github.com/MemTech/MemOS).

## Overview

This skill enables AI to automatically remember and recall project-specific information across conversations. It integrates with MemOS API to provide persistent, searchable memory storage.

## Features

- **Automatic Memory Creation**: AI proactively saves important milestones, bug fixes, decisions, and gotchas
- **Context-Aware Search**: Searches relevant memories before starting work on a project
- **Progress Tracking**: Compares current state with historical records
- **Project Isolation**: Each project has its own memory cube
- **Cross-Platform**: Supports Linux, macOS, and Windows

## Directory Structure

```
project-memory/
├── SKILL.md                           # AI skill instructions
├── README.md                          # English documentation
├── README_CN.md                       # Chinese documentation
├── references/
│   └── examples.md                    # Memory content examples
└── scripts/
    ├── memos_init_project.py          # Core Python scripts
    ├── memos_save.py
    ├── memos_search.py
    ├── linux/                         # Linux/macOS
    │   ├── install.sh                 # Installation script
    │   ├── memos-init.sh
    │   ├── memos-save.sh
    │   └── memos-search.sh
    └── windows/                       # Windows
        ├── install.cmd                # CMD installation script
        ├── install.ps1                # PowerShell installation script
        ├── memos-init.cmd
        ├── memos-save.cmd
        └── memos-search.cmd
```

## Prerequisites

- [MemOS](https://github.com/MemTech/MemOS) server running at `http://localhost:18000`
- Python 3.8+
- (Optional) Environment variables for custom configuration

## Quick Start

### Installation

| Platform | Command |
|----------|---------|
| Linux/macOS | `bash ~/.claude/skills/project-memory/scripts/linux/install.sh` |
| Windows CMD | `%USERPROFILE%\.claude\skills\project-memory\scripts\windows\install.cmd` |
| Windows PowerShell | `& "$env:USERPROFILE\.claude\skills\project-memory\scripts\windows\install.ps1"` |

### Commands After Installation

| Command | Description |
|---------|-------------|
| `memos-init` | Initialize project memory cube |
| `memos-save "content" -t TYPE` | Save a memory |
| `memos-search "query"` | Search memories |

## Installation Details

The skill is located in Claude Code's skills directory:

```
~/.claude/skills/project-memory/
```

### Linux / macOS

```bash
# Run the installer
bash ~/.claude/skills/project-memory/scripts/linux/install.sh

# Or manually add to PATH in ~/.bashrc or ~/.zshrc:
export PATH="$HOME/.local/bin:$PATH"
```

After installation:
```bash
memos-init                           # Initialize project
memos-save "content" -t MILESTONE    # Save memory
memos-search "query"                 # Search memories
```

### Windows (CMD)

```cmd
REM Run the installer
%USERPROFILE%\.claude\skills\project-memory\scripts\windows\install.cmd
```

### Windows (PowerShell)

```powershell
# Run the installer (may need: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)
& "$env:USERPROFILE\.claude\skills\project-memory\scripts\windows\install.ps1"
```

After installation, restart your terminal.

## Usage

### Automatic (Recommended)

The AI will automatically use this skill when:

1. **Starting project work** - Searches for existing memories
2. **Completing tasks** - Saves milestones and progress
3. **Fixing bugs** - Records problems and solutions
4. **Making decisions** - Documents rationale

### Manual Commands

Initialize a new project memory cube:
```bash
memos-init
# or
python3 ~/.claude/skills/project-memory/scripts/memos_init_project.py
```

Save a memory:
```bash
memos-save "Your memory content here" -t MILESTONE --tags feature release
# or
python3 ~/.claude/skills/project-memory/scripts/memos_save.py "content" -t MILESTONE
```

Search memories:
```bash
memos-search "search query"
# or
python3 ~/.claude/skills/project-memory/scripts/memos_search.py "query"
```

## Memory Types

| Type | Description | Use Case |
|------|-------------|----------|
| `MILESTONE` | Significant achievement | Feature complete, release ready |
| `BUGFIX` | Problem and solution | Bug resolved with root cause |
| `FEATURE` | New functionality | Feature implementation details |
| `DECISION` | Design choice | Architecture decisions with rationale |
| `GOTCHA` | Non-obvious issue | Tricky problems for future reference |
| `CONFIG` | Configuration change | Environment/settings modifications |
| `PROGRESS` | Status update | Work-in-progress checkpoint |

## Memory Format

```
[TYPE] Project: project-name | Date: YYYY-MM-DD

## Summary
Brief description

## Context
Why this was needed

## Details
Specific changes, code snippets, file paths

## Outcome
Results and next steps

Tags: tag1, tag2, tag3
```

## Scripts Reference

### memos_init_project.py

Initializes a new project memory cube with proper configuration.

```bash
memos-init [-p PROJECT] [-u USER]
```

Options:
- `-p, --project`: Project name (auto-detected from git)
- `-u, --user`: User ID (default: dev_user)

### memos_save.py

Saves a formatted memory to MemOS.

```bash
memos-save CONTENT [-t TYPE] [-p PROJECT] [--tags TAG...]
```

Options:
- `-t, --type`: Memory type (MILESTONE, BUGFIX, FEATURE, etc.)
- `-p, --project`: Project name
- `--tags`: Additional tags for searchability

### memos_search.py

Searches memories with formatted output.

```bash
memos-search QUERY [-p PROJECT] [--all] [--json]
```

Options:
- `-p, --project`: Search in specific project
- `--all`: Search all projects
- `--json`: Output raw JSON

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API base URL |
| `MEMOS_USER` | `dev_user` | Default user ID |
| `MEMOS_CUBES_DIR` | `~/.memos_cubes` | Directory for cube configs |

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mem_cubes` | POST | Register memory cube |
| `/memories` | POST | Save memory |
| `/memories` | GET | Get all memories |
| `/search` | POST | Search memories |

## Example Workflow

1. **Start working on a project**
   ```
   AI: Searching for existing memories about "my-project"...
   Found 3 memories: authentication system complete, rate limiting implemented...
   ```

2. **Complete a feature**
   ```
   AI: Saving milestone - "User dashboard implemented with real-time updates"
   Memory saved successfully.
   ```

3. **Debug an issue**
   ```
   AI: Searching for similar issues...
   Found related memory: "Race condition in connection pool - solved with mutex"
   ```

4. **Resume work later**
   ```
   AI: Retrieving project context...
   Last progress: "Database migration 50% complete"
   Next steps: Complete orders table schema
   ```

## AI Autonomous Behavior

Based on SKILL.md configuration, AI will **proactively** use this skill:

### Auto-Search Triggers
- Before starting work on project code
- When debugging to find similar historical issues
- When user asks about project progress or history

### Auto-Save Triggers
- After completing important features
- After solving complex bugs
- When making architectural decisions
- When discovering gotchas
- After modifying important configurations

### Progress Comparison
When user asks "what have we done?" or "project status?", AI will:
1. Search all MILESTONE and PROGRESS type memories
2. Compare with current git status
3. Synthesize completed and pending work

## Related Projects

- [MemOS](https://github.com/MemTech/MemOS) - The memory operating system backend
- [Claude Code](https://claude.ai/claude-code) - Anthropic's CLI for Claude

## License

MIT License
