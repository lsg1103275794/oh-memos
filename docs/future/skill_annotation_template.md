# Skill Annotation Template

> Use this template to manually annotate skill trigger patterns

---

## Skill Metadata

**Skill Name:** `tdd-guide`

**Short Description:** Enforce test-driven development workflow

---

## Trigger Patterns (Positive Triggers)

When should this skill be recommended?

### Direct Triggers
- "Write tests for X"
- "Create a test for X"
- "I need to add tests"
- "TDD approach"
- "Test coverage for X"
- "Unit tests for X"
- "Integration tests for X"

### Contextual Triggers
- User says "implement" + mentions "test"
- User says "feature" + mentions "test"
- User says "bug fix" + mentions "test"

### Intent-Based Triggers
- User wants to implement NEW code (not debug existing)
- User mentions "test first" or "testing first"
- User mentions "test-driven" or "TDD"

---

## Negative Triggers (False Positives)

When should this skill NOT be recommended?

### Direct Exclusions
- "Run existing tests" → Use test-runner or e2e-runner
- "Debug test failure" → Use debugger or bug-analyzer
- "Fix failing test" → Use bug-analyzer or build-error-resolver
- "View test results" → Use test-runner
- "Check test coverage" → Use test-coverage

### Contextual Exclusions
- User is debugging (not implementing)
- User is fixing build errors (use build-error-resolver)
- User is analyzing test failures (use bug-analyzer)

---

## Use Cases

| Use Case | Description | Priority |
|----------|-------------|----------|
| New Feature | Implementing new functionality | High |
| Bug Fix | Fixing bugs with test coverage | High |
| Feature Implementation | Adding features to existing code | High |
| Refactoring | Refactoring with test safety | Medium |
| Legacy Code | Adding tests to legacy code | Low |

---

## Related Tools

List of tools commonly used by this skill:

- `Bash` - Run test commands
- `Task` - Launch test agents
- `Read` - Read test files
- `Write` - Write test files
- `Grep` - Search test patterns
- `Glob` - Find test files

---

## Prerequisites

Skills that should be used BEFORE this skill:

- None (tdd-guide is typically the first step)

---

## Conflicts

Skills that should NOT be used together with this skill:

- `test-runner` - tdd-guide creates tests, test-runner runs them
- `e2e-runner` - different testing approach

---

## Skill Orchestration

When should this skill be combined with others?

### Common Sequences

1. **Standard TDD Workflow**
   - Sequence: `tdd-guide` → `code-review` → `commit`
   - Use Case: New feature implementation

2. **Security-First Development**
   - Sequence: `tdd-guide` → `security-review` → `code-review`
   - Use Case: Security-sensitive features

3. **Full Development Cycle**
   - Sequence: `plan` → `tdd-guide` → `code-review` → `e2e` → `commit`
   - Use Case: Complete feature development

---

## Context Requirements

What context is needed to recommend this skill?

### Required Context
- User is implementing NEW code
- User has NOT already written tests
- User is NOT in debug mode

### Preferred Context
- User mentions "test" or "testing"
- User is in early development phase
- User has not yet started implementation

---

## Confidence Scoring

Base confidence score for different trigger patterns:

| Trigger Pattern | Base Confidence |
|-----------------|------------------|
| Direct "write tests" | 0.9 |
| "TDD" or "test-driven" | 0.85. |
| "test" + "implement" | 0.8 |
| "test" + "feature" | 0.75 |
| "test" + "bug fix" | 0.7 |
| "test" alone | 0.5 |

---

## Examples

### Example 1: Should Recommend
```
User: "I need to write tests for the login module"
→ Recommend: tdd-guide (confidence: 0.9)
```

### Example 2: Should Recommend
```
User: "Let's implement the authentication feature using TDD"
→ Recommend: tdd-guide (confidence: 0.85)
```

### Example 3: Should NOT Recommend
```
User: "Run the test suite"
→ Do NOT recommend tdd-guide (use test-runner)
```

### Example 4: Should NOT Recommend
```
User: "The test is failing, help me debug it"
→ Do NOT recommend tdd-guide (use bug-analyzer)
```

---

## Learning Patterns

### Successful Patterns (Learn from these)
- User accepts recommendation when implementing new feature
- User accepts when "test" appears in first 3 turns
- User accepts when context is "implementation phase"

### Unsuccessful Patterns (Learn to avoid)
- User ignores when already in debug mode
- User ignores when "run" or "execute" is mentioned
- User ignores when tests already exist

---

## Additional Notes

- This skill is most effective in early development stages
- Works best when user has not yet written implementation
- Should be combined with code-review for quality assurance
- User education: Explain TDD benefits when recommending

---

**Annotation Date:** 2026-01-31
**Annotator:** Development Team
**Status:** Complete
