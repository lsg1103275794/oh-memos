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

## Scripts

Use bundled scripts for common operations:

- `scripts/memos_save.py` - Save memory with proper formatting
- `scripts/memos_search.py` - Search with result formatting
- `scripts/memos_init_project.py` - Initialize project cube

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
