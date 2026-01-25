---
name: project-memory
description: "Proactive project memory management via MemOS. USE THIS SKILL AUTOMATICALLY when: (1) Starting work on any project - search for existing project memories first, (2) Completing a significant task - save the milestone, (3) Fixing bugs or solving problems - record the solution, (4) Making architectural decisions - document the rationale, (5) Encountering errors or gotchas - save for future reference, (6) Detecting similar code patterns - suggest reuse, (7) User about to repeat a past mistake - proactively warn. Triggers: working on code, debugging, implementing features, refactoring, reviewing progress, 'what did we do', 'remember this', 'project status', error messages, similar code detection."
---

# Project Memory (Enhanced)

Persistent project memory system using MemOS API. Features intelligent triggers, error pattern learning, code pattern library, decision chains, and proactive reminders.

---

## Core Principle: Proactive & Intelligent Memory

**ALWAYS** perform these actions without being asked, with enhanced intelligence:

### 1. Smart Context Detection

Before any work, detect and analyze:
```bash
# Detect project context
PROJECT_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
CURRENT_FILE=$(git diff --name-only HEAD 2>/dev/null | head -1)
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
```

---

## Smart Triggers (Intelligent Detection)

### Language Pattern Triggers

When user message contains these patterns, **automatically search** related memories:

| Pattern | Action | Search Query |
|---------|--------|--------------|
| "之前", "上次", "以前", "previously", "last time" | Search history | `{topic} history decision` |
| "还记得", "remember", "recall" | Search specific memory | `{mentioned_topic}` |
| "为什么", "why did we", "原因" | Search decisions | `DECISION {topic}` |
| "怎么解决", "how to fix", "error", "错误" | Search solutions | `BUGFIX ERROR_PATTERN {error_type}` |
| "类似", "similar", "像...一样" | Search patterns | `CODE_PATTERN {pattern_type}` |
| "进度", "status", "progress" | Search milestones | `MILESTONE PROGRESS {project}` |

### Code Context Triggers

| Context | Auto Action |
|---------|-------------|
| Opening a file for editing | Search memories related to that file/module |
| Error message appears | Search `ERROR_PATTERN {error_signature}` |
| Creating new file | Search similar file patterns in project |
| Modifying config file | Search `CONFIG {filename}` history |
| Writing similar code | Detect and suggest existing `CODE_PATTERN` |

### Proactive Search Example
```bash
# When user asks about an error
ERROR_MSG="ModuleNotFoundError: No module named 'xxx'"
ERROR_TYPE=$(echo "$ERROR_MSG" | cut -d: -f1)

curl -s -X POST http://localhost:18000/search \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"dev_user\", \"query\": \"ERROR_PATTERN $ERROR_TYPE solution\", \"install_cube_ids\": [\"$PROJECT_NAME\"]}"
```

---

## Enhanced Memory Types

### Standard Types
| Type | Usage |
|------|-------|
| `[MILESTONE]` | Significant project achievement |
| `[BUGFIX]` | Problem solved with solution |
| `[FEATURE]` | New functionality added |
| `[DECISION]` | Architectural or design choice |
| `[GOTCHA]` | Non-obvious issue or workaround |
| `[CONFIG]` | Environment or configuration change |
| `[PROGRESS]` | Status update or checkpoint |

### New Enhanced Types

| Type | Usage |
|------|-------|
| `[ERROR_PATTERN]` | Reusable error signature and solution |
| `[CODE_PATTERN]` | Reusable code template/snippet |
| `[DECISION_CHAIN]` | Linked decision evolution |
| `[KNOWLEDGE]` | General project knowledge |

---

## Error Pattern Learning

When encountering and solving errors, save them in a structured format for future detection:

### Error Pattern Format
```markdown
[ERROR_PATTERN] Project: {project} | Date: {date}

## Error Signature
- Type: {ErrorType}
- Message: {Full error message}
- Context: {When/where this occurs}

## Environment
- OS: {Windows/Linux/macOS}
- Python: {version}
- Key packages: {relevant packages}

## Root Cause
{Why this error happens}

## Solution
1. {Step 1}
2. {Step 2}
3. {Step 3}

## Verification
{How to verify the fix works}

## Prevention
{How to prevent this in the future}

Tags: error, {error_type}, {category}
```

### Example Error Pattern
```markdown
[ERROR_PATTERN] Project: my-api | Date: 2025-01-25

## Error Signature
- Type: ModuleNotFoundError
- Message: ModuleNotFoundError: No module named 'uvicorn'
- Context: Running `python -m uvicorn` in Windows portable environment

## Environment
- OS: Windows 10
- Python: 3.11 (conda portable)
- Key packages: FastAPI

## Root Cause
Portable conda environment PATH not set correctly. The conda_venv/Scripts folder needs to be in PATH.

## Solution
1. Check if using correct Python: `where python`
2. Activate environment: set PATH=%CD%\conda_venv;%CD%\conda_venv\Scripts;%PATH%
3. Reinstall if needed: pip install uvicorn

## Verification
`python -c "import uvicorn; print(uvicorn.__version__)"`

## Prevention
Always use run.bat which sets PATH correctly. Add PATH check to startup scripts.

Tags: error, ModuleNotFoundError, environment, PATH, windows
```

### Auto-Detection Logic
When an error occurs:
1. Extract error type and message
2. Search for matching `[ERROR_PATTERN]`
3. If found → Show solution immediately
4. If not found & solved → Prompt to save new pattern

---

## Code Pattern Library

Save reusable code patterns for consistency across the project:

### Code Pattern Format
```markdown
[CODE_PATTERN] Project: {project} | Pattern: {pattern_name}

## Purpose
{What this pattern does}

## Usage Context
{When to use this pattern}

## Template
```{language}
{code template with placeholders}
```

## Parameters
- `{param1}`: {description}
- `{param2}`: {description}

## Example Usage
```{language}
{concrete example}
```

## Used In
- {file1}:{line}
- {file2}:{line}

## Notes
{Any important notes}

Tags: pattern, {category}, {language}
```

### Example Code Pattern
```markdown
[CODE_PATTERN] Project: my-api | Pattern: API Error Handler

## Purpose
Unified error handling decorator for FastAPI endpoints

## Usage Context
Wrap all API endpoint functions for consistent error responses

## Template
```python
from functools import wraps
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

def handle_api_error(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise  # Re-raise HTTP exceptions as-is
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    return wrapper
```

## Parameters
- None (decorator pattern)

## Example Usage
```python
@router.get("/users/{user_id}")
@handle_api_error
async def get_user(user_id: int):
    return await user_service.get(user_id)
```

## Used In
- src/api/users.py:15
- src/api/projects.py:22
- src/api/memories.py:18

## Notes
- Always place after route decorator
- HTTP exceptions pass through unchanged
- Logs all unexpected errors

Tags: pattern, error-handling, fastapi, python, decorator
```

### Pattern Detection Logic
When user writes code:
1. Analyze code structure
2. Compare with saved `[CODE_PATTERN]` entries
3. If similarity > 70% → Suggest: "Detected similar pattern. Use [PATTERN_NAME]?"
4. If new reusable pattern identified → Prompt to save

---

## Decision Chain Tracking

Track how decisions evolve over time with linked references:

### Decision Chain Format
```markdown
[DECISION_CHAIN] Project: {project} | Topic: {topic}

## Current Decision
{Current approach/choice}

## Evolution Timeline
| Date | Decision | Rationale | Supersedes |
|------|----------|-----------|------------|
| {date1} | {decision1} | {why1} | - |
| {date2} | {decision2} | {why2} | {decision1} |
| {date3} | {decision3} | {why3} | {decision2} |

## Context
{Background and constraints}

## Alternatives Considered
1. **{Option A}**: {pros/cons}
2. **{Option B}**: {pros/cons}
3. **{Option C}** (chosen): {pros/cons}

## Impact
- Affected files: {list}
- Dependencies: {list}
- Migration needed: {yes/no}

## Links
- Previous: [DECISION-{id}]
- Related: [DECISION-{id}], [DECISION-{id}]

Tags: decision, {topic}, architecture
```

### Example Decision Chain
```markdown
[DECISION_CHAIN] Project: my-api | Topic: Authentication Method

## Current Decision
JWT with Refresh Token (implemented 2025-01-25)

## Evolution Timeline
| Date | Decision | Rationale | Supersedes |
|------|----------|-----------|------------|
| 2025-01-10 | Session-based auth | Simple, familiar | - |
| 2025-01-15 | JWT only | Stateless, scalable | Session-based |
| 2025-01-20 | JWT + short expiry (15min) | Security improvement | JWT only |
| 2025-01-25 | JWT + Refresh Token | Balance security & UX | JWT short expiry |

## Context
API needs to support multiple clients (web, mobile, CLI) with different security requirements.

## Alternatives Considered
1. **Session-based**: Simple but requires sticky sessions, doesn't scale
2. **JWT only (long expiry)**: Scalable but security risk if token leaked
3. **JWT + Refresh Token** (chosen): Best balance - short-lived access, long-lived refresh

## Impact
- Affected files: src/auth/*, src/api/middleware.py
- Dependencies: python-jose, passlib
- Migration needed: Yes, added refresh_tokens table

## Links
- Previous: [DECISION-AUTH-003]
- Related: [DECISION-DB-001], [CONFIG-ENV-002]

Tags: decision, authentication, jwt, security, architecture
```

---

## Proactive Reminder System

### When to Proactively Remind

#### 1. Similar Code Detection
```
Trigger: User writing code similar to existing pattern
Action:
  "I noticed you're writing code similar to [CODE_PATTERN: API Error Handler].
   Would you like to use the existing pattern for consistency?"
```

#### 2. Gotcha Warning
```
Trigger: User about to do something that caused issues before
Action:
  "Heads up: Last time we modified {file}, we encountered {issue}.
   Remember to {prevention_step}."
```

#### 3. Decision Context
```
Trigger: User working on area with relevant decisions
Action:
  "FYI: This area has a decision history [DECISION_CHAIN: {topic}].
   Current approach: {current_decision}. Want me to show the rationale?"
```

#### 4. Error Prevention
```
Trigger: User's action matches known error pattern trigger
Action:
  "Warning: This configuration commonly causes {ERROR_PATTERN: {type}}.
   Recommended: {prevention_tip}"
```

#### 5. Progress Checkpoint
```
Trigger: After completing 3+ significant tasks
Action:
  "You've completed several tasks. Want me to save a progress checkpoint?
   - {task1}
   - {task2}
   - {task3}"
```

### Reminder Priority Levels

| Priority | Type | When to Show |
|----------|------|--------------|
| High | Gotcha/Error Prevention | Immediately, before user proceeds |
| Medium | Similar Code/Pattern | After user pauses or asks |
| Low | Progress Checkpoint | At natural break points |

---

## Knowledge Graph Concepts

Maintain relationships between memories:

```
PROJECT
├── FEATURES
│   ├── feature-1 ──relates──> CONFIG-1
│   └── feature-2 ──depends──> DECISION-1
├── BUGS
│   ├── bug-1 ──caused_by──> CONFIG-2
│   └── bug-2 ──similar_to──> ERROR_PATTERN-1
├── DECISIONS
│   ├── decision-1 ──supersedes──> decision-0
│   └── decision-2 ──impacts──> feature-2
└── PATTERNS
    ├── pattern-1 ──used_in──> [file1, file2]
    └── pattern-2 ──variant_of──> pattern-1
```

### Link Format in Memories
```markdown
## Related Memories
- Relates to: [FEATURE-001], [CONFIG-002]
- Caused by: [DECISION-003]
- Similar to: [ERROR_PATTERN-005]
- Supersedes: [DECISION-002]
```

---

## MemOS API Reference

**Base URL**: `http://localhost:18000`

### Save Memory
```bash
curl -s -X POST http://localhost:18000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "dev_user",
    "mem_cube_id": "PROJECT_NAME",
    "memory_content": "MEMORY_CONTENT"
  }'
```

### Search Memories
```bash
curl -s -X POST http://localhost:18000/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "dev_user",
    "query": "SEARCH_QUERY",
    "install_cube_ids": ["PROJECT_NAME"]
  }'
```

### Get All Memories
```bash
curl -s -X GET "http://localhost:18000/memories?mem_cube_id=PROJECT_NAME&user_id=dev_user"
```

### Chat with Memory Context
```bash
curl -s -X POST http://localhost:18000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "dev_user", "query": "QUESTION"}'
```

---

## Workflow Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROJECT MEMORY WORKFLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  USER ACTION          SMART TRIGGER           AI ACTION          │
│  ───────────          ─────────────           ─────────          │
│                                                                  │
│  Start working   ───> Detect project    ───> Search memories     │
│                                              Show relevant context│
│                                                                  │
│  Write code      ───> Detect pattern    ───> Suggest CODE_PATTERN│
│                                              or save new pattern │
│                                                                  │
│  Hit error       ───> Match signature   ───> Show ERROR_PATTERN  │
│                                              solution instantly  │
│                                                                  │
│  Make decision   ───> Find related      ───> Show DECISION_CHAIN │
│                       decisions              context             │
│                                                                  │
│  Risky action    ───> Match GOTCHA      ───> Proactive warning   │
│                                                                  │
│  Complete task   ───> Significance      ───> Prompt to save      │
│                       check                  appropriate type    │
│                                                                  │
│  Ask "why/how"   ───> Language pattern  ───> Search & explain    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## CLI Scripts Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMOS_URL` | `http://localhost:18000` | MemOS API URL |
| `MEMOS_USER` | `dev_user` | Default user ID |
| `MEMOS_CUBES_DIR` | `~/.memos_cubes` | Memory cube storage |

### memos-init (Initialize Project)

```bash
# Initialize current project (auto-detect from git)
python scripts/memos_init_project.py

# Initialize specific project
python scripts/memos_init_project.py -p my-project

# Check API health
python scripts/memos_init_project.py --check

# Force overwrite existing config
python scripts/memos_init_project.py -p my-project --force
```

**Arguments:**
- `-p, --project` - Project name (auto-detected from git)
- `-u, --user` - User ID (default: dev_user)
- `--cubes-dir` - Directory for cube configs
- `-f, --force` - Overwrite existing config
- `--check` - Check API health only
- `-v, --verbose` - Verbose output

### memos-save (Save Memory)

```bash
# Save with auto-detected project
python scripts/memos_save.py "Fixed login redirect bug" -t BUGFIX

# Save to specific project
python scripts/memos_save.py "Auth system complete" -t MILESTONE -p my-api

# Save with custom tags
python scripts/memos_save.py "ModuleNotFoundError fix" -t ERROR_PATTERN --tags error python windows

# Save with verbose output
python scripts/memos_save.py "Decision rationale..." -t DECISION -v
```

**Arguments:**
- `content` - Memory content (required)
- `-t, --type` - Memory type (default: PROGRESS)
- `-p, --project` - Project name
- `-u, --user` - User ID
- `--tags` - Additional tags (space-separated)
- `-v, --verbose` - Verbose output
- `--json` - Output raw JSON
- `--no-auto-register` - Disable auto cube registration

**Memory Types:**
- Standard: `MILESTONE`, `BUGFIX`, `FEATURE`, `DECISION`, `GOTCHA`, `CONFIG`, `PROGRESS`
- Enhanced: `ERROR_PATTERN`, `CODE_PATTERN`, `DECISION_CHAIN`, `KNOWLEDGE`

### memos-search (Search Memories)

```bash
# Search current project
python scripts/memos_search.py "authentication"

# Search specific project
python scripts/memos_search.py "redis config" -p my-api

# Search all projects
python scripts/memos_search.py "error connection" --all

# Filter by type
python scripts/memos_search.py "pattern" -t ERROR_PATTERN

# Compact output (first line only)
python scripts/memos_search.py "decision" -c

# JSON output
python scripts/memos_search.py "milestone" --json
```

**Arguments:**
- `query` - Search query (required)
- `-p, --project` - Project name
- `-u, --user` - User ID
- `-t, --type` - Filter by memory type
- `--all` - Search all projects
- `-c, --compact` - Compact output
- `-v, --verbose` - Verbose output
- `--json` - Output raw JSON
- `--no-auto-register` - Disable auto cube registration

### Cross-Platform Support

Scripts automatically handle path conversion:

| Environment | Path Format |
|-------------|-------------|
| Windows | `C:\Users\...` |
| Linux/macOS | `/home/user/...` |
| WSL | `/mnt/c/...` → `C:/...` (auto-converted for Windows API) |

The `memos_utils.py` module provides:
- Environment detection (Windows/Linux/macOS/WSL)
- Path normalization for API calls
- Auto cube registration
- API health checks

---

## Best Practices

1. **Be Specific**: Include file paths, function names, error messages
2. **Include Why**: Don't just record what, explain the reasoning
3. **Tag Consistently**: Use standard tags for searchability
4. **Link Related**: Connect memories with relationship links
5. **Search First**: Before saving, check if similar memory exists
6. **Update Chains**: When decisions evolve, update DECISION_CHAIN
7. **Save Patterns**: When code is reusable, save as CODE_PATTERN
8. **Record Errors**: Every solved error is a future time-saver

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Cube ID Format Issue

**Problem:** API returns `422 Unprocessable Entity` or `User does not have access to cube`

**Root Cause:** The MemOS API uses full paths as `cube_id` internally, not just project names.

**Solution:**
- After initialization, the cube ID is the full path (e.g., `G:/test/MemOS/data/memos_cubes/dev_cube`)
- The scripts now auto-resolve cube names to full paths using a cache (`~/.memos_cube_cache.json`)
- If issues persist, run `memos-init` again to refresh the cache

```bash
# Check cached cube IDs
cat ~/.memos_cube_cache.json

# Re-initialize to refresh cache
python scripts/memos_init_project.py -p my-project --force
```

#### 2. WSL Path Not Recognized

**Problem:** Paths like `/home/user/.memos_cubes/` fail when MemOS API runs on Windows

**Root Cause:** Windows cannot directly access WSL filesystem paths using Linux format.

**Solutions:**
1. **Use mounted Windows paths**: `/mnt/c/Users/...` instead of `/home/user/...`
2. **For pure WSL paths**: The system will convert to UNC format (`\\wsl$\Ubuntu\home\...`)
3. **Best practice**: Store cube configs in Windows-accessible locations

```bash
# Recommended: Use Windows-mounted path
export MEMOS_CUBES_DIR="/mnt/g/test/MemOS/data/memos_cubes"

# Not recommended (may have issues)
export MEMOS_CUBES_DIR="/home/user/.memos_cubes"
```

#### 3. API Connection Errors

**Problem:** `Connection refused` or `timeout` errors

**Checklist:**
1. Check if MemOS API is running:
   ```bash
   curl http://localhost:18000/users
   ```
2. Verify `MEMOS_URL` environment variable
3. Check if port 18000 is blocked by firewall
4. For WSL: Ensure Windows allows network connections from WSL

#### 4. HuggingFace Clone Errors

**Problem:** `git clone https://huggingface.co/datasets/...` fails unexpectedly

**Root Cause (Historical):** Old versions of MemOS would blindly try to clone any non-existent path as a HuggingFace repo.

**Fixed in MemOS:** Now validates HuggingFace repo format (`username/repo-name`) before attempting clone.

**If you see this:**
1. Update MemOS to latest version
2. Use valid formats:
   - Local path: `/mnt/g/test/project` or `C:\test\project`
   - HuggingFace: `username/repository-name`

#### 5. Qdrant Connection Priority

**Problem:** Using cloud Qdrant but connecting to localhost

**Root Cause:** Having both `QDRANT_HOST=localhost` and `QDRANT_URL=https://...` in `.env`

**Solution:** Comment out local settings when using cloud:
```env
# Local (comment out when using cloud)
# QDRANT_HOST=localhost
# QDRANT_PORT=6333

# Cloud (uncomment for cloud)
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-api-key
```

#### 6. Memory Save Failed

**Problem:** Memory save returns error even though cube is registered

**Troubleshooting Steps:**
```bash
# 1. Check API health
python scripts/memos_init_project.py --check -v

# 2. Verify cube is registered
curl -s -X POST http://localhost:18000/search \
  -H "Content-Type: application/json" \
  -d '{"user_id": "dev_user", "query": "*"}' | python -m json.tool

# 3. Try with verbose output
python scripts/memos_save.py "test memory" -t PROGRESS -v --json

# 4. Check cube cache
cat ~/.memos_cube_cache.json
```

### Debug Mode

Enable verbose output for all scripts:

```bash
# All scripts support -v/--verbose
python scripts/memos_init_project.py -v
python scripts/memos_save.py "content" -t PROGRESS -v
python scripts/memos_search.py "query" -v

# For JSON debugging
python scripts/memos_save.py "content" -t PROGRESS --json
python scripts/memos_search.py "query" --json
```

### Environment Verification

```bash
# Check current environment
python scripts/memos_utils.py

# Expected output:
# Environment: wsl (or linux/windows/macos)
# MEMOS_URL: http://localhost:18000
# CUBES_DIR: /home/user/.memos_cubes
# API Health: API is running
```

