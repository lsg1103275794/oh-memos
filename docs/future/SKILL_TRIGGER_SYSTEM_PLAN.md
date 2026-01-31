# Skill Intelligent Triggering System

> Plan Version: 1.0
> Created: 2026-01-31
> Status: Draft

---

## Overview

Intelligent skill triggering system that automatically recommends and invokes Claude Code skills based on user intent, context, and historical patterns.

### Core Vision

Transform the static skill library (200+ skills) into an **adaptive, context-aware recommendation system** that:

- ✅ Understands user intent from natural language
- ✅ Recommends relevant skills before manual invocation
- ✅ Learns from user interactions to improve accuracy
- ✅ Supports skill orchestration (multi-skill workflows)
- ✅ Adapts to individual user preferences

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                     User Input                          │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│            UserPromptSubmit Hook                        │
│  1. Extract keywords from user input                    │
│  2. Analyze conversation context                        │
│  3. Query memory system for matching skills             │
│  4. Rank and filter recommendations                     │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│        Context-Aware Memory Search                      │
│  - memos_search_context(query, conversation_history)    │
│  - Returns skill matches with confidence scores         │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│            Skill Knowledge Graph                        │
│  - 200+ skills indexed with metadata                    │
│  - Trigger keywords, use cases, dependencies            │
│  - Historical usage patterns                            │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│           Recommendation Engine                         │
│  - Weight-based ranking                                 │
│  - Confidence threshold filtering                       │
│  - Skill conflict resolution                            │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              User Response                              │
│  - Display recommendations (top 3-5)                    │
│  - Accept / Ignore / Modify suggestion                  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│            PostToolUse Hook                             │
│  - Record user action (accepted/ignored)                │
│  - Update skill weights in memory                       │
│  - Learn from feedback loop                             │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Roadmap

### Phase 1: Knowledge Base Construction (MVP)
**Duration:** 1-2 days
**Target Accuracy:** 70%

#### 1.1 Skill Metadata Extraction

**Task:** Extract structured metadata from all 200+ SKILL.md files

**Input:**
```
.claude/skills/<skill-name>/SKILL.md
```

**Extracted Fields:**
```python
SkillMetadata:
  - name: str                  # Skill identifier (e.g., "tdd-guide")
  - description: str           # Short description
  - trigger_keywords: List[str]  # Keywords that indicate this skill
  - use_cases: List[str]       # When to use this skill
  - related_tools: List[str]   # Tools used by this skill
  - prerequisites: List[str]   # Skills that must be used first
  - conflicts_with: List[str]  # Skills that should not be used together
```

**Output:** Batch save to memory system as `CODE_PATTERN` type

```python
# Example memory entry
[
CODE_PATTERN]
Skill: tdd-guide
Description: Enforce test-driven development workflow
Trigger Keywords: [test, testing, tdd, unit test, integration test, coverage]
Use Cases: [bug fix, new feature, feature implementation]
Related Tools: [Bash, Task, Read, Write, Grep, Glob]
Prerequisites: []
Conflicts: []
```

#### 1.2 Manual Annotation (Critical Skills)

**Task:** Manually annotate trigger patterns for top 30 high-frequency skills

**Priority Skills:**
1. `tdd-guide` - Test-driven development
2. `code-review` - Code review
3. `commit` - Git commit creation
4. `plan` - Implementation planning
5. `refactor-clean` - Dead code cleanup
6. `e2e` - End-to-end testing
7. `security-review` - Security analysis
8. `build-fix` - Build error resolution
9. `doc-updater` - Documentation updates
10. `checkpoint` - Create checkpoints
11. `test-coverage` - Test coverage analysis
12. `verify` - Verification command
13. `learn` - Extract reusable patterns
14. `memos` - Project memory management
15. `orchestrate` - Multi-agent orchestration

**Annotation Template:**
```markdown
## Trigger Patterns
- "Write tests for X"
- "Create a test for X"
- "I need to add tests"
- "TDD approach"
- "Test coverage for X"

## Negative Triggers (False Positives)
- "Run existing tests" (use test-runner, not tdd-guide)
- "Debug test failure" (use debugger, not tdd-guide)

## Context Requirements
- Must be implementing NEW code (not debugging)
- Should come BEFORE implementation starts
```

#### 1.3 Initial Indexing

**Script:** `scripts/future/build_skill_index.py`

```python
#!/usr/bin/env python3
"""
Build skill knowledge index from SKILL.md files
"""
import glob
import json
from pathlib import Path
from mcp import memos_save

def extract_skill_metadata(skill_path: str) -> dict:
    """Extract metadata from SKILL.md"""
    # Implementation details...

def build_skill_index():
    """Build complete index and save to memory"""
    skills_dir = Path(".claude/skills")

    for skill_dir in skills_dir.iterdir():
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        metadata = extract_skill_metadata(str(skill_md))

        # Save to memory as CODE_PATTERN
        memos_save(
            content=json.dumps(metadata, indent=2),
            memory_type="CODE_PATTERN"
        )

if __name__ == "__main__":
    build_skill_index()
```

**Expected Output:** 200+ skill entries in memory system

---

### Phase 2: Trigger System Implementation
**Duration:** 1-2 days
**Target Accuracy:** 75%

#### 2.1 UserPromptSubmit Hook

**Location:** `.claude/hooks/bash/user-prompt-submit.sh` (and PowerShell/Node equivalents)

**Implementation:**

```bash
#!/bin/bash
# UserPromptSubmit Hook for Skill Recommendation

USER_INPUT="$1"
CUBE_ID="dev_cube"

# Step 1: Extract keywords and context
QUERY=$(echo "$USER_INPUT" | tr '[:upper:]' '[:lower:]')

# Step 2: Get conversation history (last 5 turns)
# (Implementation depends on Claude Code API)

# Step 3: Search memory for matching skills
RESULT=$(memos_search_context \
  --cube-id "$CUBE_ID" \
  --query "$QUERY" \
  --context "$CONVERSATION_HISTORY" \
  --top-k 5
)

# Step 4: Parse results and filter by confidence
SKILLS=$(echo "$RESULT" | jq -r '.skills[] | select(.confidence > 0.6)')

# Step 5: Display recommendations
if [ -n "$SKILLS" ]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "💡 Recommended Skills:"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "$SKILLS" | jq -r '.name + ": " + .description'
  echo ""
  echo "Use /<skill-name> to invoke"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
```

**PowerShell Version:** `.claude/hooks/powershell/UserPromptSubmit.ps1`

#### 2.2 PostToolUse Hook (Learning System)

**Location:** `.claude/hooks/bash/post-tool-use.sh`

**Implementation:**

```bash
#!/bin/bash
# PostToolUse Hook for Skill Weight Learning

TOOL_NAME="$1"
WAS_SUCCESSFUL="$2"  # true/false from exit code
CUBE_ID="dev_cube"

# Only record Skill tool usage
if [[ "$TOOL_NAME" == "Skill" ]]; then
  SKILL_NAME="$3"  # Which skill was invoked
  USER_ACCEPTED="$4"  # Did user accept recommendation?

  # Update skill weight in memory
  if [ "$USER_ACCEPTED" = "true" ]; then
    WEIGHT_CHANGE=+0.1
  else
    WEIGHT_CHANGE=-0.05
  fi

  # Save learning data
  memos_save(
    content="[LEARNING_PATTERN] Skill: $SKILL_NAME | Weight change: $WEIGHT_CHANGE | Trigger: $LAST_USER_INPUT",
    memory_type="CODE_PATTERN"
  )
fi
```

#### 2.3 Configuration Management

**Location:** `.claude/config/skill-trigger-config.json`

```json
{
  "enabled": true,
  "confidence_threshold": 0.6,
  "max_recommendations": 5,
  "auto_trigger": false,
  "learning_mode": true,
  "user_preferences": {
    "show_recommendations": true,
    "show_explanation": true,
    "show_confidence": false
  }
}
```

---

### Phase 3: Context-Aware Search Enhancement
**Duration:** 3-5 days
**Target Accuracy:** 85%

#### 3.1 Conversation Context Integration

**Enhanced Search Logic:**

```python
def analyze_user_intent(user_input: str, conversation_history: List[dict]) -> Intent:
    """
    Analyze user intent with conversation context

    Example:
      User: "I need to add tests for the login module"
      Assistant: "Okay, let me help with that."
      User: "Start with the authentication function"

    → Intent: tdd-guide (not just generic "test")
    """
    intent = Intent(
        primary_skill=None,
        secondary_skills=[],
        context_stage="initial",  # initial/planning/implementation/refactoring
        confidence=0.0
    )

    # Analyze sequence of requests
    for turn in conversation_history[-3:]:
        if "test" in turn["user_input"]:
            intent.context_stage = "testing"

    # Match with skills based on full context
    matched_skills = memos_search_context(
        query=user_input,
        context=conversation_history,
        cube_id="dev_cube"
    )

    return matched_skills
```

#### 3.2 Skill Orchestration Support

**Example: Multi-Skill Workflow**

```python
# When user says "Create a secure PR for this feature"
# Should recommend: security-reviewer + code-reviewer

SkillOrchestration:
  - name: "Security PR Workflow"
    sequence: [security-reviewer, code-reviewer]
    trigger_keywords: [secure, security, audit, compliance]
```

**Memory Entry:**
```python
[
CODE_PATTERN]
Orchestration: Security PR Workflow
Sequence: [security-reviewer, code-reviewer]
Trigger Keywords: [secure, security, audit, compliance]
Use Cases: [PR creation, code review, security audit]
```

#### 3.3 Adaptive Threshold System

```python
def get_adaptive_threshold(user_id: str, skill: str) -> float:
    """
    Get personalized threshold based on user history

    - Users who frequently accept recommendations: Lower threshold (0.5)
    - Users who rarely accept recommendations: Higher threshold (0.75)
    - High-confidence skills (tdd-guide): Lower threshold (0.55)
    - Low-confidence skills (generic): Higher threshold (0.7)
    """
    base_threshold = 0.6

    # Adjust based on user acceptance rate
    acceptance_rate = get_user_acceptance_rate(user_id)
    if acceptance_rate > 0.8:
        base_threshold -= 0.1
    elif acceptance_rate < 0.3:
        base_threshold += 0.1

    # Adjust based on skill specificity
    if is_high_confidence_skill(skill):
        base_threshold -= 0.05

    return max(0.5, min(0.8, base_threshold))
```

---

### Phase 4: Advanced Features
**Duration:** 2-3 weeks
**Target Accuracy:** 90%+

#### 4.1 Cross-Project Knowledge Sharing

**Feature:** Share skill patterns across projects

```json
{
  "shared_knowledge": {
    "enabled": true,
    "sync_interval": 86400,  # 24 hours
    "projects": [
      {
        "name": "common-patterns",
        "cube_id": "shared_patterns",
        "priority": "high"
      }
    ]
  }
}
```

#### 4.2 Dependency Inference

**Auto-discover skill dependencies:**

```python
def infer_skill_dependencies(skill_name: str) -> List[str]:
    """
    Analyze skill usage history to find patterns

    Example: If users frequently run tdd-guide before code-reviewer,
    infer dependency: code-reviewer → tdd-guide
    """
    usage_history = get_skill_usage_history(skill_name)

    # Find skills that are commonly used BEFORE this skill
    prerequisites = find_prerequisite_patterns(usage_history)

    # Find skills that are commonly used AFTER this skill
    next_steps = find_next_step_patterns(usage_history)

    return prerequisites, next_steps
```

#### 4.3 Feedback Loop Optimization

**User Feedback Collection:**

```python
# When user accepts/ignores recommendation
def record_feedback(skill_name: str, action: str, user_input: str):
    """
    action: "accepted", "ignored", "modified"

    Learning:
    - "accepted": Increase weight for this trigger pattern
    - "ignored": Decrease weight, analyze why
    - "modified": Create new pattern variant
    """

    feedback_entry = {
        "skill": skill_name,
        "action": action,
        "trigger": user_input,
        "timestamp": datetime.now(),
        "context": get_conversation_context()
    }

    memos_save(
        content=json.dumps(feedback_entry),
        memory_type="LEARNING_PATTERN"
    )
```

---

## Technical Specifications

### Memory Schema

#### Skill Entry (CODE_PATTERN)
```json
{
  "skill_name": "tdd-guide",
  "description": "Enforce test-driven development workflow",
  "trigger_keywords": ["test", "testing", "tdd"],
  "use_cases": ["bug fix", "new feature"],
  "related_tools": ["Bash", "Task", "Read", "Write"],
  "prerequisites": [],
  "conflicts": [],
  "weight": 1.0,
  "total_usage": 0,
  "acceptance_rate": 0.0,
  "last_updated": "2026-01-31T00:00:00Z"
}
```

#### Learning Pattern (LEARNING_PATTERN)
```json
{
  "pattern_type": "trigger_success",
  "skill_name": "tdd-guide",
  "trigger": "I need to add tests for the login function",
  "user_action": "accepted",
  "confidence": 0.85,
  "context_stage": "initial",
  "timestamp": "2026-01-31T10:30:00Z"
}
```

#### Skill Orchestration (CODE_PATTERN)
```json
{
  "orchestration_name": "Security PR Workflow",
  "sequence": ["security-reviewer", "code-reviewer"],
  "trigger_keywords": ["secure", "security", "audit"],
  "use_cases": ["PR creation", "security review"],
  "estimated_duration": "15-30 minutes"
}
```

---

## API Integration

### MCP Server Enhancements

**New Endpoint:** `POST /product/skills/recommend`

```python
# src/memos/api/handlers/skill_recommend_handler.py

@router.post("/recommend")
async def recommend_skills(request: SkillRecommendRequest):
    """
    Recommend skills based on user input and context

    Returns:
    - List of recommended skills with confidence scores
    - Explanations for each recommendation
    - Suggested orchestration workflows
    """
    # Implementation...
```

**Request Schema:**
```python
class SkillRecommendRequest(BaseModel):
    user_id: str
    user_input: str
    conversation_history: List[dict]
    max_recommendations: int = 5
    min_confidence: float = 0.6
```

**Response Schema:**
```python
class SkillRecommendResponse(BaseModel):
    recommendations: List[SkillRecommendation]
    orchestration_suggestions: List[OrchestrationWorkflow]
    explanation: str

class SkillRecommendation(BaseModel):
    skill_name: str
    confidence: float
    description: str
    reason: str
```

---

## Performance Considerations

### Latency Targets

| Operation | Target Latency |
|-----------|----------------|
| Hook execution | < 200ms   |
| Memory search | < 100ms        |
| Total recommendation | < 300ms |

### Optimization Strategies

1. **Local Caching**
   - Cache frequently accessed skill metadata
   - Pre-load top 50 skills into memory

2. **Async Queries**
   - Non-blocking memory queries in hooks
   - Background learning updates

3. **Batch Processing**
   - Batch save learning patterns
   - Defer weight recalculation

4. **Index Optimization**
   - Build inverted index on trigger keywords
   - Use Neo4j relationship queries for skill dependencies

---

## Testing Strategy

### Unit Tests
```python
def test_skill_metadata_extraction():
    metadata = extract_skill_metadata("tdd-guide")
    assert metadata["name"] == "tdd-guide"
    assert "test" in metadata["trigger_keywords"]

def test_recommendation_ranking():
    recommendations = recommend_skills("I need to write tests")
    assert len(recommendations) > 0
    assert all(r.confidence > 0.6 for r in recommendations)
```

### Integration Tests
```python
def test_hook_integration():
    # Simulate user input
    result = execute_hook("user-prompt-submit", "Write tests for login")
    assert "tdd-guide" in result["recommendations"]
```

### Acceptance Tests
- Manual testing with real user workflows
- Measure accuracy over 100+ interactions
- Monitor false positive/negative rates

---

## Metrics and Monitoring

### Key Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Recommendation Accuracy | 85%+ | User accepts recommendation |
| False Positive Rate | < 15% | Recommendations shown but ignored |
| Hook Latency | < 300ms | Time from input to recommendation |
| User Satisfaction | 4/5+ stars | Subjective feedback |
| Learning Rate | 5% improvement/month | Accuracy improvement over time |

### Monitoring

```python
# Track usage patterns
def track_metrics():
    metrics = {
        "total_recommendations": get_total_recommendations(),
        "acceptance_rate": get_acceptance_rate(),
        "avg_confidence": get_avg_confidence(),
        "top_skills": get_top_used_skills()
    }

    # Save to memory as PROGRESS
    memos_save(
        content=json.dumps(metrics),
        memory_type="PROGRESS"
    )
```

---

## Risk Mitigation

### Identified Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hook latency affects UX | High | Local caching, async queries |
| False positives annoy users | Medium | Configurable thresholds |
| Learning system bias | Low | Diversity in training data |
| Cross-project sync conflicts | Medium | Conflict resolution strategy |
| Skill metadata drift | Medium | Periodic validation |

---

## Success Criteria

### MVP (Phase 1-2)
- ✅ 200+ skills indexed in memory
- ✅ Hook system functional
- ✅ 70%+ recommendation accuracy
- ✅ < 500ms response time
- ✅ User can enable/disable

### Full Release (Phase 3-4)
- ✅ 85%+ recommendation accuracy
- ✅ Context-aware search
- ✅ Learning system operational
- ✅ Skill orchestration supported
- ✅ Cross-project knowledge sharing

---

## Timeline Summary

| Phase | Duration | Milestones |
|-------|----------|------------|
| **Phase 1** | 1-2 days | Knowledge base built, 30 skills annotated |
| **Phase 2** | 1-2 days | Hooks functional, basic triggering works |
| **Phase 3** | 3-5 days | Context-aware search, 85% accuracy |
| **Phase 4** | 2-3 weeks | Advanced features, 90%+ accuracy |
| **Total** | 3-4 weeks | Production-ready system |

---

## Next Steps

1. **Immediate (This Week)**
   - [ ] Create `scripts/future/build_skill_index.py`
   - [ ] Manually annotate top 30 skills
   - [ ] Implement basic UserPromptSubmit hook
   - [ ] Test with 50+ interactions

2. **Short-term (Next 2 Weeks)**
   - [ ] Implement PostToolUse learning hook
   - [ ] Add context-aware search
   - [ ] Deploy to test environment
   - [ ] Collect user feedback

3. **Long-term (Next Month)**
   - [ ] Implement skill orchestration
   - [ ] Add cross-project sharing
   - [ ] Optimize performance
   - [ ] Production release

---

## Appendix

### A. Skill Annotation Template

See `docs/future/skill_annotation_template.md`

### B. Hook Reference

See `docs/future/hook_reference.md`

### C. MCP API Extensions

See `docs/future/mcp_extensions.md`

---

**Document Status:** 📋 Draft
**Next Review:** 2026-02-07
**Owner:** Development Team
