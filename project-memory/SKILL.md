---
name: project-memory
description: "Proactive project memory management via MemOS. USE THIS SKILL AUTOMATICALLY when: (1) Starting work on any project - search for existing project memories first, (2) Completing a significant task - save the milestone, (3) Fixing bugs or solving problems - record the solution, (4) Making architectural decisions - document the rationale, (5) Encountering errors or gotchas - save for future reference. Triggers: working on code, debugging, implementing features, refactoring, reviewing progress, 'what did we do', 'remember this', 'project status'."
---

# Project Memory

Persistent project memory system using MemOS API. Automatically remember project milestones, search historical context, and track progress.

## Core Principle: Proactive Memory Management

**ALWAYS** perform these actions without being asked:

### On Project Start (Before Writing Code)
```bash
# 1. Detect project context
PROJECT_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")

# 2. Search existing memories for this project
curl -s -X POST http://localhost:18000/search \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"$PROJECT_NAME project\", \"user_id\": \"dev_user\"}"
```

Review search results before proceeding. This provides:
- Previous decisions and their rationale
- Known issues and workarounds
- Completed milestones and current progress

### On Task Completion (After Significant Work)
Save memories for:
- Bug fixes (cause, solution, affected files)
- New features (what, why, how)
- Refactoring (before/after, motivation)
- Configuration changes (what changed, why)
- Architectural decisions (options considered, chosen approach, rationale)

## MemOS API Reference

**Base URL**: `http://localhost:18000`

### Register Project Cube (First Time Only)
```bash
# Create project cube config
PROJECT_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
CUBE_PATH="$HOME/.memos_cubes/${PROJECT_NAME}"
mkdir -p "$CUBE_PATH"

cat > "$CUBE_PATH/config.json" << EOF
{
  "model_schema": "memos.configs.mem_cube.GeneralMemCubeConfig",
  "user_id": "dev_user",
  "cube_id": "${PROJECT_NAME}",
  "config_filename": "config.json",
  "text_mem": {
    "backend": "general_text",
    "config": {
      "cube_id": "${PROJECT_NAME}",
      "memory_filename": "textual_memory.json"
    }
  }
}
EOF

# Register cube
curl -s -X POST http://localhost:18000/mem_cubes \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"dev_user\", \"mem_cube_name_or_path\": \"$CUBE_PATH\", \"mem_cube_id\": \"$PROJECT_NAME\"}"
```

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

## Memory Content Format

Structure memories for maximum searchability and usefulness:

```
[TYPE] Project: PROJECT_NAME | Date: YYYY-MM-DD

## Summary
One-line description of what was done

## Context
- Why this was needed
- Related files/components

## Details
- Specific changes made
- Key code snippets if relevant
- Configuration values

## Outcome
- Result of the change
- Any follow-up needed

## Tags
feature, bugfix, refactor, config, architecture, gotcha, milestone
```

**Memory Types**:
- `[MILESTONE]` - Significant project achievement
- `[BUGFIX]` - Problem solved with solution
- `[FEATURE]` - New functionality added
- `[DECISION]` - Architectural or design choice
- `[GOTCHA]` - Non-obvious issue or workaround
- `[CONFIG]` - Environment or configuration change
- `[PROGRESS]` - Status update or checkpoint

## Workflow Triggers

### Automatic Save Triggers
Save a memory when any of these occur:

1. **Task Completed**: Feature implemented, bug fixed, refactor done
2. **Problem Solved**: After debugging, especially tricky issues
3. **Decision Made**: Chose between alternatives with reasoning
4. **Error Encountered**: Discovered gotcha or non-obvious behavior
5. **Configuration Changed**: Environment, deps, or settings modified
6. **Milestone Reached**: Significant project checkpoint

### Automatic Search Triggers
Search memories when:

1. **Starting Related Work**: Before working on a feature/module
2. **Debugging**: Search for similar past issues
3. **Reviewing Progress**: Check what's been done
4. **Making Decisions**: Find previous rationale
5. **User Asks**: "What did we do?", "Project status?", "History of X?"

## Progress Comparison

To compare current state with historical records:

```bash
# 1. Get all project memories
curl -s -X GET "http://localhost:18000/memories?mem_cube_id=PROJECT_NAME&user_id=dev_user"

# 2. Search for milestones
curl -s -X POST http://localhost:18000/search \
  -H "Content-Type: application/json" \
  -d '{"user_id": "dev_user", "query": "MILESTONE progress status", "install_cube_ids": ["PROJECT_NAME"]}'

# 3. Compare with current git status
git log --oneline -10
git status
```

Then synthesize:
- What milestones were recorded vs current state
- What issues were solved that might recur
- What decisions were made that affect current work

## Scripts

Use bundled scripts for common operations:

- `scripts/memos_save.py` - Save memory with proper formatting
- `scripts/memos_search.py` - Search with result formatting
- `scripts/memos_init_project.py` - Initialize project cube

## Best Practices

1. **Be Specific**: Include file paths, function names, error messages
2. **Include Why**: Don't just record what, explain the reasoning
3. **Tag Consistently**: Use standard tags for searchability
4. **Update Don't Duplicate**: If updating a previous decision, reference it
5. **Search First**: Before saving, check if similar memory exists
