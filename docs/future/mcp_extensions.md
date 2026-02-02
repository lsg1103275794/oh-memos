# MCP API Extensions

> Extensions to MemOS MCP server for skill triggering system

---

## Overview

The skill triggering system requires several new MCP tools and API endpoints to support:

1. **Skill Recommendation API** - Context-aware skill matching
2. **Learning Pattern Storage** - Record user interactions
3. **Weight Management** - Update skill weights
4. **Orchestration Support** - Multi-skill workflows

---

## New MCP Tools

### 1. `memos_recommend_skills`

**Purpose:** Recommend skills based on user input and conversation context

**Parameters:**
```python
{
    "query": str,              # User input text
    "conversation_history": List[dict],  # Recent conversation turns
    "cube_id": str = "dev_cube",        # Memory cube ID
    "max_recommendations": int = 5,     # Max skills to return
    "min_confidence": float = 0.6,      # Minimum confidence threshold
    "include_orchestration": bool = True  # Include skill sequences
}
```

**Returns:**
```python
{
    "recommendations": [
        {
            "skill_name": str,
            "confidence": float,
            "description": str,
            "reason": str,
            "trigger_keywords": List[str]
        }
    ],
    "orchestration_suggestions": [
        {
            "name": str,
            "sequence": List[str],
            "confidence": float,
            "description": str
        }
    ],
    "explanation": str
}
```

**Implementation:**
```python
# src/memos/api/handlers/skill_recommend_handler.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json

router = APIRouter()

class SkillRecommendRequest(BaseModel):
    user_id: str
    query: str
    conversation_history: List[dict] = []
    cube_id: str = "dev_cube"
    max_recommendations: int = 5
    min_confidence: float = 0.6
    include_orchestration: bool = True

class SkillRecommendation(BaseModel):
    skill_name: str
    confidence: float
    description: str
    reason: str
    trigger_keywords: List[str]

class OrchestrationSuggestion(BaseModel):
    name: str
    sequence: List[str]
    confidence: float
    description: str

class SkillRecommendResponse(BaseModel):
    recommendations: List[SkillRecommendation]
    orchestration_suggestions: List[OrchestrationSuggestion]
    explanation: str

@router.post("/recommend", response_model=SkillRecommendResponse)
async def recommend_skills(request: SkillRecommendRequest):
    """
    Recommend skills based on user input and context

    Algorithm:
    1. Analyze user intent from query
    2. Search memory for matching skills
    3. Apply confidence threshold
    4. Rank by weight and relevance
    5. Find orchestration patterns if enabled
    """
    try:
        # Step 1: Search for skill patterns
        search_result = await search_skill_patterns(
            query=request.query,
            context=request.conversation_history,
            cube_id=request.cube_id,
            top_k=request.max_recommendations * 2  # Get more, filter later
        )

        # Step 2: Filter and rank recommendations
        recommendations = []
        for item in search_result["items"]:
            if item["confidence"] >= request.min_confidence:
                skill_data = json.loads(item["content"])

                # Calculate adjusted confidence (base confidence * weight)
                adjusted_confidence = item["confidence"] * skill_data.get("weight", 1.0)

                recommendations.append(SkillRecommendation(
                    skill_name=skill_data["skill_name"],
                    confidence=adjusted_confidence,
                    description=skill_data["description"],
                    reason=f"Matched keywords: {', '.join(skill_data['trigger_keywords'][:3])}",
                    trigger_keywords=skill_data["trigger_keywords"]
                ))

        # Sort by confidence
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        recommendations = recommendations[:request.max_recommendations]

        # Step 3: Find orchestration patterns
        orchestration_suggestions = []
        if request.include_orchestration:
            orchestration_suggestions = await find_orchestration_patterns(
                query=request.query,
                recommendations=recommendations,
                cube_id=request.cube_id
            )

        # Step 4: Generate explanation
        explanation = generate_explanation(
            recommendations=recommendations,
            orchestration_suggestions=orchestration_suggestions
        )

        return SkillRecommendResponse(
            recommendations=recommendations,
            orchestration_suggestions=orchestration_suggestions,
            explanation=explanation
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 2. `memos_save_learning_pattern`

**Purpose:** Save learning pattern from user interactions

**Parameters:**
```python
{
    "skill_name": str,
    "trigger": str,           # User input that triggered the skill
    "action": str,            # "accepted_recommendation", "manual_invocation", "ignored"
    "successful": bool,        # Was the skill execution successful?
    "weight_change": float,   # Weight adjustment (+0.10, -0.05, etc.)
    "cube_id": str = "dev_cube"
}
```

**Returns:**
```python
{
    "success": bool,
    "memory_id": str,
    "updated_weight": float
}
```

**Implementation:**
```python
# src/memos/api/handlers/learning_handler.py

class LearningPatternRequest(BaseModel):
    skill_name: str
    trigger: str
    action: str  # "accepted_recommendation", "manual_invocation", "ignored"
    successful: bool
    weight_change: float
    cube_id: str = "dev_cube"

@router.post("/learning/save")
async def save_learning_pattern(request: LearningPatternRequest):
    """
    Save learning pattern and update skill weight

    Learning algorithm:
    1. Create learning pattern entry
    2. Update skill weight in memory
    3. Recalculate acceptance rate
    """
    try:
        # Step 1: Save learning pattern
        learning_entry = f"""
[LEARNING_PATTERN]
Skill: {request.skill_name}
Trigger: {request.trigger}
Action: {request.action}
Successful: {request.successful}
Weight Change: {request.weight_change}
Timestamp: {datetime.utcnow().isoformat()}
"""

        # Save to memory
        from src.memos.api.routers.server_router import save_memory
        memory_result = await save_memory(
            content=learning_entry,
            cube_id=request.cube_id,
            memory_type="LEARNING_PATTERN"
        )

        # Step 2: Update skill weight
        updated_weight = await update_skill_weight(
            skill_name=request.skill_name,
            weight_change=request.weight_change,
            cube_id=request.cube_id
        )

        # Step 3: Recalculate acceptance rate
        await update_acceptance_rate(
            skill_name=request.skill_name,
            cube_id=request.cube_id
        )

        return {
            "success": True,
            "memory_id": memory_result["memory_id"],
            "updated_weight": updated_weight
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def update_skill_weight(skill_name: str, weight_change: float, cube_id: str) -> float:
    """
    Update skill weight in memory

    Weight constraints:
    - Minimum: 0.1 (never zero)
    - Maximum: 2.0 (don't over-amplify)
    """
    # Find skill entry
    search_result = await search_skill_patterns(
        query=f"skill_name:{skill_name}",
        cube_id=cube_id,
        top_k=1
    )

    if not search_result["items"]:
        return 1.0  # Default weight

    skill_data = json.loads(search_result["items"][0]["content"])
    current_weight = skill_data.get("weight", 1.0)

    # Apply weight change
    new_weight = max(0.1, min(2.0, current_weight + weight_change))

    # Update skill entry
    skill_data["weight"] = new_weight
    skill_data["last_updated"] = datetime.utcnow().isoformat()

    # Save updated skill data
    await update_skill_entry(
        skill_name=skill_name,
        skill_data=skill_data,
        cube_id=cube_id
    )

    return new_weight
```

---

### 3. `memos_get_skill_metrics`

**Purpose:** Get usage metrics for a skill

**Parameters:**
```python
{
    "skill_name": str,
    "cube_id": str = "dev_cube"
}
```

**Returns:**
```python
{
    "skill_name": str,
    "total_usage": int,
    "acceptance_rate": float,
    "avg_confidence": float,
    "weight": float,
    "last_used": str,
    "top_triggers": List[str]
}
```

**Implementation:**
```python
# src/memos/api/handlers/metrics_handler.py

@router.get("/skills/{skill_name}/metrics")
async def get_skill_metrics(skill_name: str, cube_id: str = "dev_cube"):
    """
    Get comprehensive metrics for a skill
    """
    try:
        # Search for skill data
        skill_search = await search_skill_patterns(
            query=f"skill_name:{skill_name}",
            cube_id=cube_id,
            top_k=1
        )

        if not skill_search["items"]:
            raise HTTPException(status_code=404, detail="Skill not found")

        skill_data = json.loads(skill_search["items"][0]["content"])

        # Search for learning patterns
        learning_search = await search_learning_patterns(
            query=f"Skill: {skill_name}",
            cube_id=cube_id,
            top_k=100
        )

        # Calculate metrics
        total_usage = len(learning_search["items"])
        accepted_count = sum(
            1 for item in learning_search["items"]
            if "accepted_recommendation" in item["content"]
        )
        acceptance_rate = accepted_count / total_usage if total_usage > 0 else 0.0

        # Calculate average confidence
        confidences = [
            float(item["confidence"])
            for item in learning_search["items"]
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Find top triggers
        triggers = [
            extract_trigger(item["content"])
            for item in learning_search["items"]
        ]
        top_triggers = most_common(triggers, 5)

        return {
            "skill_name": skill_name,
            "total_usage": skill_data.get("total_usage", 0),
            "acceptance_rate": acceptance_rate,
            "avg_confidence": avg_confidence,
            "weight": skill_data.get("weight", 1.0),
            "last_used": skill_data.get("last_updated", ""),
            "top_triggers": top_triggers
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 4. `memos_find_orchestration_patterns`

**Purpose:** Find multi-skill orchestration patterns

**Parameters:**
```python
{
    "query": str,
    "recommendations": List[str],  # Recommended skill names
    "cube_id": str = "dev_cube"
}
```

**Returns:**
```python
{
    "orchestrations": [
        {
            "name": str,
            "sequence": List[str],
            "confidence": float,
            "description": str,
            "estimated_duration": str
        }
    ]
}
```

**Implementation:**
```python
@router.post("/orchestration/find")
async def find_orchestration_patterns(
    query: str,
    recommendations: List[str],
    cube_id: str = "dev_cube"
):
    """
    Find orchestration patterns that match the query

    Orchestration matching:
    1. Search for orchestration entries
    2. Check if recommended skills are in sequence
    3. Calculate confidence based on overlap
    """
    try:
        # Search for orchestration patterns
        search_result = await search_skill_patterns(
            query=query,
            cube_id=cube_id,
            top_k=10
        )

        orchestrations = []
        for item in search_result["items"]:
            content = item["content"]

            # Check if this is an orchestration entry
            if "orchestration_name" not in content:
                continue

            orch_data = json.loads(content)

            # Calculate overlap with recommendations
            sequence = orch_data["sequence"]
            overlap = len(set(sequence) & set(recommendations))
            confidence = overlap / len(sequence) if sequence else 0.0

            if confidence > 0.5:  # Only if >50% overlap
                orchestrations.append({
                    "name": orch_data["orchestration_name"],
                    "sequence": sequence,
                    "confidence": confidence,
                    "description": orch_data.get("description", ""),
                    "estimated_duration": orch_data.get("estimated_duration", "")
                })

        # Sort by confidence
        orchestrations.sort(key=lambda x: x["confidence"], reverse=True)

        return {"orchestrations": orchestrations}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## API Endpoints

### 1. POST `/product/skills/recommend`

**Description:** Recommend skills based on user input

**Request:**
```json
{
  "user_id": "dev_user",
  "query": "I need to write tests for the login module",
  "conversation_history": [
    {"role": "user", "content": "I'm implementing authentication"},
    {"role": "assistant", "content": "Great, let me help with that."}
  ],
  "cube_id": "dev_cube",
  "max_recommendations": 5,
  "min_confidence": 0.6
}
```

**Response:**
```json
{
  "recommendations": [
    {
      "skill_name": "tdd-guide",
      "confidence": 0.92,
      "description": "Enforce test-driven development workflow",
      "reason": "Matched keywords: test, write, implementation",
      "trigger_keywords": ["test", "testing", "tdd", "unit test"]
    }
  ],
  "orchestration_suggestions": [
    {
      "name": "Standard TDD Workflow",
      "sequence": ["tdd-guide", "code-review", "commit"],
      "confidence": 0.85,
      "description": "Complete test-driven development cycle"
    }
  ],
  "explanation": "Based on your request to write tests for the login module, I recommend starting with tdd-guide to ensure proper test coverage before implementation."
}
```

---

### 2. POST `/product/skills/learning/save`

**Description:** Save learning pattern from user interaction

**Request:**
```json
{
  "skill_name": "tdd-guide",
  "trigger": "I need to write tests for the login module",
  "action": "accepted_recommendation",
  "successful": true,
  "weight_change": 0.10,
  "cube_id": "dev_cube"
}
```

**Response:**
```json
{
  "success": true,
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "updated_weight": 1.10
}
```

---

### 3. GET `/product/skills/{skill_name}/metrics`

**Description:** Get usage metrics for a skill

**Response:**
```json
{
  "skill_name": "tdd-guide",
  "total_usage": 150,
  "acceptance_rate": 0.78,
  "avg_confidence": 0.85,
  "weight": 1.10,
  "last_used": "2026-01-31T10:30:00Z",
  "top_triggers": [
    "write tests for",
    "I need to add tests",
    "test coverage for",
    "TDD approach",
    "unit tests for"
  ]
}
```

---

### 4. POST `/product/skills/orchestration/find`

**Description:** Find orchestration patterns

**Request:**
```json
{
  "query": "Create a secure PR for this feature",
  "recommendations": ["security-reviewer", "code-reviewer"],
  "cube_id": "dev_cube"
}
```

**Response:**
```json
{
  "orchestrations": [
    {
      "name": "Security PR Workflow",
      "sequence": ["security-reviewer", "code-reviewer"],
      "confidence": 0.95,
      "description": "Security-focused code review workflow",
      "estimated_duration": "15-30 minutes"
    }
  ]
}
```

---

## Database Schema Extensions

### Neo4j Schema

```cypher
// Skill nodes
CREATE CONSTRAINT skill_name_unique IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE;

// Skill properties
CREATE (s:Skill {
  name: "tdd-guide",
  description: "Enforce test-driven development workflow",
  weight: 1.0,
  total_usage: 0,
  acceptance_rate: 0.0,
  created_at: datetime(),
  updated_at: datetime()
});

// Trigger keyword relationships
CREATE (s:Skill)-[:HAS_TRIGGER]->(:TriggerKeyword {keyword: "test"});
CREATE (s:Skill)-[:HAS_TRIGGER]->(:TriggerKeyword {keyword: "testing"});

// Use case relationships
CREATE (s:Skill)-[:HAS_USE_CASE]->(:UseCase {case: "bug fix"});
CREATE (s:Skill)-[:HAS_USE_CASE]->(:UseCase {case: "new feature"});

// Skill orchestration relationships
CREATE (s1:Skill)-[:FOLLOWS]->(s2:Skill);  // s1 follows s2 in workflow
CREATE (s1:Skill)-[:CONFLICTS_WITH]->(s2:Skill);  // Should not be used together

// Learning pattern nodes
CREATE (l:LearningPattern {
  skill_name: "tdd-guide",
  trigger: "write tests for",
  action: "accepted_recommendation",
  successful: true,
  weight_change: 0.10,
  timestamp: datetime()
});

// Pattern relationships
CREATE (l:LearningPattern)-[:FOR_SKILL]->(s:Skill);
```

---

## Integration with Existing MCP Tools

### Enhanced `memos_search_context`

**Current Implementation:** Already supports context-aware search

**Enhancement for Skills:**

```python
# Add skill-specific filtering to memos_search_context

async def memos_search_context(
    query: str,
    context: List[dict],
    cube_id: str = "dev_cube",
    top_k: int = 10,
    memory_type: Optional[str] = None,  # Filter by memory type
    **kwargs
):
    """
    Enhanced context-aware search with skill filtering

    New features:
    - Filter by memory_type (CODE_PATTERN, LEARNING_PATTERN)
    - Boost skill weights based on learning patterns
    - Apply user preferences
    """
    # ... existing implementation ...

    # New: Filter by memory type
    if memory_type:
        results = [r for r in results if r.get("memory_type") == memory_type]

    # New: Apply skill weight boosting
    results = apply_skill_weight_boosting(results, cube_id)

    return results
```

---

## Performance Optimizations

### 1. Query Caching

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def cached_skill_recommendation(query_hash: str, cube_id: str):
    """Cache skill recommendations to reduce database queries"""
    # Implementation...
    pass

async def recommend_skills_cached(request: SkillRecommendRequest):
    """Wrapper with caching"""
    query_hash = hashlib.md5(request.query.encode()).hexdigest()

    # Check cache
    cached = cached_skill_recommendation(query_hash, request.cube_id)
    if cached:
        return cached

    # Compute recommendation
    result = await recommend_skills(request)

    # Update cache
    cached_skill_recommendation.cache_set(query_hash, request.cube_id, result)

    return result
```

### 2. Async Batch Processing

```python
import asyncio

async def batch_update_skill_weights(updates: List[dict]):
    """
    Batch update multiple skill weights in parallel
    """
    tasks = [
        update_skill_weight(u["skill_name"], u["weight_change"], u["cube_id"])
        for u in updates
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results
```

### 3. Index Optimization

```cypher
// Create indexes for fast skill queries
CREATE INDEX skill_name_index IF NOT EXISTS FOR (s:Skill) ON (s.name);
CREATE INDEX skill_weight_index IF NOT EXISTS FOR (s:Skill) ON (s.weight);
CREATE INDEX learning_pattern_skill_index IF NOT EXISTS FOR (l:LearningPattern) ON (l.skill_name);
CREATE INDEX learning_pattern_timestamp_index IF NOT EXISTS FOR (l:LearningPattern) ON (l.timestamp);
```

---

## Error Handling

### Standard Error Responses

```python
class SkillNotFoundError(HTTPException):
    def __init__(self, skill_name: str):
        super().__init__(
            status_code=404,
            detail=f"Skill '{skill_name}' not found in memory"
        )

class InvalidWeightChangeError(HTTPException):
    def __init__(self, weight_change: float):
        super().__init__(
            status_code=400,
            detail=f"Invalid weight change: {weight_change}. Must be between -0.1 and 0.1"
        )

class MemorySystemError(HTTPException):
    def __init__(self, message: str):
        super().__init__(
            status_code=500,
            detail=f"Memory system error: {message}"
        )
```

---

## Testing

### Unit Tests

```python
# tests/api/test_skill_recommendation.py

import pytest
from fastapi.testclient import TestClient
from src.memos.api.start_api import app

client = TestClient(app)

def test_recommend_skills():
    """Test skill recommendation endpoint"""
    request = {
        "user_id": "dev_user",
        "query": "write tests for login",
        "cube_id": "dev_cube"
    }

    response = client.post("/product/skills/recommend", json=request)

    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0

def test_save_learning_pattern():
    """Test learning pattern saving"""
    request = {
        "skill_name": "tdd-guide",
        "trigger": "write tests",
        "action": "accepted_recommendation",
        "successful": True,
        "weight_change": 0.10,
        "cube_id": "dev_cube"
    }

    response = client.post("/product/skills/learning/save", json=request)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "updated_weight" in data

def test_get_skill_metrics():
    """Test skill metrics retrieval"""
    response = client.get("/product/skills/tdd-guide/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["skill_name"] == "tdd-guide"
    assert "total_usage" in data
    assert "acceptance_rate" in data
```

---

## Migration Guide

### From Old System to New MCP Extensions

1. **Update MCP Server Configuration**

```python
# mcp-server/memos_mcp_server.py

# Add new tools
tools = [
    # ... existing tools ...
    {
        "name": "memos_recommend_skills",
        "description": "Recommend skills based on user input and context",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "conversation_history": {"type": "array"},
                "cube_id": {"type": "string", "default": "dev_cube"},
                "max_recommendations": {"type": "integer", "default": 5},
                "min_confidence": {"type": "number", "default": 0.6}
            },
            "required": ["query"]
        }
    },
    # ... other new tools ...
]
```

2. **Update Hook Scripts**

```bash
# .claude/hooks/bash/user-prompt-submit.sh

# Use new MCP tool instead of direct API call
RECOMMENDATIONS=$(memos_recommend_skills \
  --query "$QUERY" \
  --conversation-history "$CONVERSATION_HISTORY" \
  --cube-id "$CUBE_ID" \
  --max-recommendations 5
)
```

3. **Migrate Existing Data**

```python
# scripts/migrate_skill_data.py

async def migrate_skills():
    """Migrate existing skill data to new format"""
    # Read old skill data
    old_skills = load_old_skill_data()

    # Convert to new format
    for skill in old_skills:
        new_format = {
            "skill_name": skill["name"],
            "description": skill["description"],
            "trigger_keywords": skill["keywords"],
            "weight": 1.0,
            "total_usage": 0,
            "acceptance_rate": 0.0,
            "last_updated": datetime.utcnow().isoformat()
        }

        # Save to memory
        await memos_save(
            content=json.dumps(new_format),
            cube_id="dev_cube",
            memory_type="CODE_PATTERN"
        )
```

---

**Extensions Version:** 1.0
**Last Updated:** 2026-01-31
