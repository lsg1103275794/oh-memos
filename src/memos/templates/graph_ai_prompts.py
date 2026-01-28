"""
Graph AI Prompts - LLM prompts for intelligent knowledge graph construction.

This module contains prompts for:
- Triple extraction (entity-relation-entity)
- Search intent analysis
- Graph schema inference
"""

TRIPLE_EXTRACTION_PROMPT = """You are a knowledge graph expert.

Given the following memory text, extract all meaningful knowledge triples in the form of (subject, predicate, object).

Memory Text:
{memory_text}

Instructions:
1. Extract entities (people, places, organizations, events, concepts, dates, etc.)
2. Identify relationships between entities
3. Focus on factual, concrete relationships - avoid vague connections
4. Include temporal relationships when dates/times are mentioned
5. Normalize entity names (e.g., "John Smith" not "John" and "Mr. Smith" separately)

Valid predicate types (use these exact names):
- WORKS_AT: Person works at organization/company
- LOCATED_IN: Entity is located in place
- HAPPENED_ON: Event occurred on date/time
- PARTICIPATED_IN: Person/org participated in event
- KNOWS: Person knows another person
- CREATED: Entity created something
- BELONGS_TO: Entity belongs to category/group
- RELATED_TO: General semantic relationship
- CAUSED: One event/action caused another
- DEPENDS_ON: One thing depends on another
- PART_OF: Entity is part of larger entity
- HAS_PROPERTY: Entity has attribute/property

Language rules:
- Entity names should preserve the original language from the input
- Predicate types must be in English (from the list above)

Return ONLY valid JSON array:
[
  {
    "subject": "<entity name>",
    "predicate": "<relationship type from list>",
    "object": "<entity name>",
    "confidence": <0.0-1.0 float>
  }
]

If no meaningful triples can be extracted, return: []

Example Input:
"John Smith joined Google as a senior engineer in 2023. He works on the AI research team in Mountain View."

Example Output:
[
  {"subject": "John Smith", "predicate": "WORKS_AT", "object": "Google", "confidence": 0.95},
  {"subject": "John Smith", "predicate": "PARTICIPATED_IN", "object": "AI research team", "confidence": 0.9},
  {"subject": "Google AI research team", "predicate": "LOCATED_IN", "object": "Mountain View", "confidence": 0.85},
  {"subject": "John Smith joining Google", "predicate": "HAPPENED_ON", "object": "2023", "confidence": 0.95}
]
"""

SEARCH_INTENT_PROMPT = """You are a search intent analyzer for a knowledge memory system.

Given the user's search query and recent conversation context, analyze the search intent to improve retrieval.

Search Query: {query}

Recent Conversation Context:
{context}

Your task:
1. Identify the core information need
2. Extract key entities mentioned or implied
3. Determine if the query is:
   - Factual lookup (who/what/when/where)
   - Relational query (how does X relate to Y)
   - Temporal query (what happened before/after)
   - Causal query (why did X happen)
   - Exploratory (tell me about X)
4. Suggest query expansions or related concepts

Language rules:
- Analysis should be in the same language as the query

Return ONLY valid JSON:
{
  "intent_type": "<factual|relational|temporal|causal|exploratory>",
  "core_entities": ["<entity1>", "<entity2>"],
  "implied_entities": ["<entity1>"],
  "time_scope": "<specific date/range or null>",
  "expanded_queries": ["<alternative query 1>", "<alternative query 2>"],
  "suggested_filters": {
    "memory_type": "<LongTermMemory|WorkingMemory|null>",
    "date_range": {"start": "<ISO date or null>", "end": "<ISO date or null>"}
  }
}
"""

GRAPH_SCHEMA_INFERENCE_PROMPT = """You are a knowledge graph schema analyst.

Given the following sample of memory nodes and their relationships from a user's knowledge graph, infer and describe the schema pattern.

Sample Nodes:
{nodes_sample}

Sample Relationships:
{edges_sample}

Statistics:
- Total nodes: {total_nodes}
- Total edges: {total_edges}
- Relationship type distribution: {edge_type_dist}

Your task:
1. Identify common entity types in the graph
2. Identify frequent relationship patterns
3. Detect potential schema issues (orphan nodes, missing relationships)
4. Suggest schema improvements

Language rules:
- Analysis should match the predominant language in the sample data
- Technical terms (entity types, relationship types) should be in English

Return ONLY valid JSON:
{
  "entity_types": [
    {"type": "<type name>", "count": <estimated count>, "description": "<brief description>"}
  ],
  "relationship_patterns": [
    {"pattern": "<subject_type> -[<predicate>]-> <object_type>", "frequency": "<high|medium|low>"}
  ],
  "schema_issues": [
    {"issue": "<description>", "severity": "<high|medium|low>", "suggestion": "<fix suggestion>"}
  ],
  "completeness_score": <0.0-1.0>,
  "suggestions": ["<improvement suggestion 1>", "<improvement suggestion 2>"]
}
"""

MEMORY_QUALITY_EVALUATION_PROMPT = """You are a memory quality evaluator.

Given the following memory node, evaluate its quality for knowledge graph storage.

Memory Content:
{memory_content}

Memory Metadata:
{memory_metadata}

Evaluation Criteria:
1. Specificity: Does it contain specific facts vs vague statements?
2. Completeness: Are there missing important details (time, place, people)?
3. Consistency: Is the information internally consistent?
4. Relevance: Is this information worth preserving long-term?
5. Extractability: Can meaningful knowledge triples be extracted?

Return ONLY valid JSON:
{
  "overall_score": <0.0-1.0>,
  "scores": {
    "specificity": <0.0-1.0>,
    "completeness": <0.0-1.0>,
    "consistency": <0.0-1.0>,
    "relevance": <0.0-1.0>,
    "extractability": <0.0-1.0>
  },
  "issues": ["<issue 1>", "<issue 2>"],
  "suggestions": ["<improvement suggestion 1>"],
  "recommended_action": "<keep|enrich|merge|discard>"
}
"""
