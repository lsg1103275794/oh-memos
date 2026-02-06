#!/usr/bin/env python3
"""
MemOS MCP Server Tools Registry Module

Contains all MCP tool definitions.
"""

from config import MEMOS_DEFAULT_CUBE, MEMOS_ENABLE_DELETE, MEMOS_USER, logger
from mcp.types import Tool


def get_tools() -> list[Tool]:
    """Return list of all available MCP tools."""
    tools = [
        Tool(
            name="memos_search",
            description="""Search project memories for relevant context.

USE THIS TOOL PROACTIVELY when:
- You encounter an error or exception (search for ERROR_PATTERN)
- User mentions "之前", "上次", "previously", "last time"
- You need to understand past decisions (search for DECISION)
- You're about to modify code that might have gotchas (search for GOTCHA)
- You see similar code patterns (search for CODE_PATTERN)
- Working with configuration files (search for CONFIG)

Results are automatically compacted when exceeding threshold (15+ items).
Use memos_get(memory_id) to retrieve full details of specific memories.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query. Can be natural language or prefixed with memory type (e.g., 'ERROR_PATTERN ModuleNotFoundError', 'DECISION authentication')"
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'. Example: /mnt/g/test/MemOS → 'memos_cube', ~/my-app → 'my_app_cube'",
                        "default": MEMOS_DEFAULT_CUBE
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    },
                    "compact": {
                        "type": "boolean",
                        "description": "Enable context compression for large results (default: true). Set to false to get full results.",
                        "default": True
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="memos_search_context",
            description="""Context-aware memory search with LLM intent analysis.

USE THIS TOOL when you need smarter search that understands:
- The broader conversation context (what you've been discussing)
- Implied entities and concepts that aren't explicitly mentioned
- The type of information the user is really looking for

This tool analyzes the query + recent conversation to:
1. Determine search intent (factual lookup, relationship query, causal question, etc.)
2. Extract explicit AND implied entities
3. Expand the query with related terms for better recall
4. Apply smart filters based on intent

Example: If you've been discussing "login errors" and user asks "what was the solution?",
this tool understands they mean "login error solution" even without explicit mention.

Best used when:
- Query is ambiguous or refers to earlier conversation
- You want better recall through query expansion
- You need to find related concepts, not just exact matches""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - can be brief since context helps clarify intent"
                    },
                    "context": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["user", "assistant"]},
                                "content": {"type": "string"}
                            }
                        },
                        "description": "Recent conversation messages for context (last 5-10 turns)"
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path.",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="memos_save",
            description="""Save important information to project memory.

🚨 **MUST: 显式指定 memory_type 参数** - 不要依赖自动检测！

USE THIS TOOL when:
- You've solved a bug or error → **MUST use BUGFIX or ERROR_PATTERN**
- A significant decision was made → **MUST use DECISION** with rationale
- You've completed a major task → **MUST use MILESTONE**
- You discovered a non-obvious gotcha → **MUST use GOTCHA**
- You created a reusable code pattern → **MUST use CODE_PATTERN**
- Configuration was changed → **MUST use CONFIG**

Memory types (按优先级选择，PROGRESS 仅用于纯进度汇报):
- ERROR_PATTERN: Error signature + solution (有通用复用价值)
- BUGFIX: Bug fix with cause and solution (一次性修复)
- DECISION: Architectural or design choice with rationale
- GOTCHA: Non-obvious issue or workaround
- CODE_PATTERN: Reusable code template
- CONFIG: Environment or configuration change
- FEATURE: New functionality added
- MILESTONE: Significant project achievement
- PROGRESS: **仅用于纯进度更新，禁止包含错误解决方案、技术决策、陷阱警告**

❌ 错误: memos_save(content="修复了模型路径问题") → 默认 PROGRESS
✅ 正确: memos_save(content="修复了模型路径问题...", memory_type="BUGFIX")""",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Memory content to save. Be detailed - include context, rationale, and relevant code/commands."
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "**REQUIRED** - Type of memory. Decision tree: Bug fix → BUGFIX/ERROR_PATTERN, Technical decision → DECISION, Gotcha → GOTCHA, Code template → CODE_PATTERN, Config change → CONFIG, New feature → FEATURE, Achievement → MILESTONE, Pure progress update → PROGRESS",
                        "enum": ["ERROR_PATTERN", "DECISION", "MILESTONE", "BUGFIX",
                                "FEATURE", "CONFIG", "CODE_PATTERN", "GOTCHA", "PROGRESS"]
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'. Example: /mnt/g/test/MemOS → 'memos_cube', ~/my-app → 'my_app_cube'",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": ["content", "memory_type"]
            }
        ),
        Tool(
            name="memos_list_v2",
            description="""List memories from a memory cube with context compression.

Results are automatically compacted when exceeding threshold (15+ items) to save context window.
Use memos_get(memory_id) to retrieve full details of specific memories.

Set compact=false to disable compression and get full results.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'. Example: /mnt/g/test/MemOS → 'memos_cube', ~/my-app → 'my_app_cube'",
                        "default": MEMOS_DEFAULT_CUBE
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memories to return.",
                        "default": 20
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Optional: Filter by memory type (e.g., DECISION, ERROR_PATTERN).",
                        "enum": ["ERROR_PATTERN", "DECISION", "MILESTONE", "BUGFIX", "FEATURE", "CONFIG", "CODE_PATTERN", "GOTCHA", "PROGRESS"]
                    },
                    "compact": {
                        "type": "boolean",
                        "description": "Enable context compression for large results (default: true). Set to false to get full results.",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memos_get",
            description="""Get full details of a single memory by ID.

Use this after memos_search or memos_list_v2 returns compacted results.
Retrieves complete memory content, metadata, background, and relations.

Example: memos_get(memory_id="abc123-def456-...")""",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The full memory ID to retrieve (from memos_search or memos_list_v2 results)"
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path.",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": ["memory_id"]
            }
        ),
        Tool(
            name="memos_suggest",
            description="""Get smart suggestions for memory searches based on current context.

Use this when you're unsure what to search for. Provide the current context
(error message, code snippet, user question) and get relevant search suggestions.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "context": {
                        "type": "string",
                        "description": "Current context (error message, code, user question)"
                    }
                },
                "required": ["context"]
            }
        ),
        Tool(
            name="memos_list_cubes",
            description="""List all available memory cubes in the system.

USE THIS TOOL when:
- You encounter "cube not found" errors
- User asks which cubes are available
- You need to verify a cube exists before using it
- Starting a new project and want to see existing cubes

Returns:
- List of available cube IDs with their paths
- Registration status for each cube
- Helpful guidance if no cubes are found""",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_status": {
                        "type": "boolean",
                        "description": "Include registration status for each cube (requires API call)",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memos_get_stats",
            description="""Get statistics about memories in a project cube.

Use this to see how many memories of each type (DECISION, ERROR_PATTERN, etc.) are stored.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID (project name)",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                }
            }
        ),
        Tool(
            name="memos_trace_path",
            description="""Trace reasoning paths between two memory nodes.

USE THIS TOOL when you need to understand:
- How two concepts or events are connected
- The chain of causality or dependencies between memories
- Indirect relationships that span multiple hops

This is powerful for AI reasoning:
- "How did decision A lead to outcome B?"
- "What's the connection between error X and configuration Y?"
- "Trace the path from this bug to its root cause"

Returns:
- Whether a path exists between the two nodes
- Full path details with all intermediate nodes and edges
- The relationship types along the path (CAUSE, RELATE, CONDITION, etc.)

Example: Tracing from "Java not installed" to "API timeout error" might reveal:
  [Java not installed] ──CAUSE──> [Neo4j failed] ──CAUSE──> [DB connection lost] ──CAUSE──> [API timeout]""",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "ID of the source memory node to start from. Get this from memos_search or memos_get_graph."
                    },
                    "target_id": {
                        "type": "string",
                        "description": "ID of the target memory node to find path to. Get this from memos_search or memos_get_graph."
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum path length (hops). Default 3, max 10.",
                        "default": 3
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path.",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": ["source_id", "target_id"]
            }
        ),
        Tool(
            name="memos_get_graph",
            description="""Get memory knowledge graph with relationships.

USE THIS TOOL when you need to understand:
- How memories are connected (dependencies, causality)
- What caused a particular issue (CAUSE relationships)
- Related context around a topic (RELATE relationships)
- Conflicting information (CONFLICT relationships)

Returns:
- Memory nodes matching the query
- Relationships between memories: CAUSE, RELATE, CONFLICT, CONDITION

Example: If you search "Neo4j startup failure", you might see:
  [Java not installed] ──CAUSE──> [Neo4j failed to start]

This helps you understand the full context and dependencies.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find related memories and their relationships"
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'. Example: /mnt/g/test/MemOS → 'memos_cube', ~/my-app → 'my_app_cube'",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="memos_export_schema",
            description="""Export knowledge graph schema and statistics.

USE THIS TOOL when you need to understand:
- The overall structure of the project's memory graph
- What types of relationships exist in the knowledge base
- How well-connected the memories are
- The most common tags and memory types
- Time range of stored knowledge

This helps AI understand:
- What kind of information has been stored
- How memories relate to each other
- Whether there are gaps in the knowledge (orphan nodes)
- The overall health of the knowledge graph

Returns comprehensive statistics including:
- Total nodes and edges
- Relationship type distribution (CAUSE, RELATE, CONFLICT, etc.)
- Memory type distribution (LongTermMemory, WorkingMemory, etc.)
- Top 20 most frequent tags
- Average and max connections per node
- Number of orphan (unconnected) nodes
- Time range of data""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path.",
                        "default": MEMOS_DEFAULT_CUBE
                    },
                    "sample_size": {
                        "type": "integer",
                        "description": "Number of nodes to sample for analysis (10-1000). Default 100.",
                        "default": 100
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memos_register_cube",
            description="""Register a memory cube with the MemOS API.

USE THIS TOOL when you encounter:
- "MemCube 'xxx' is not loaded" error
- "Cube not registered" error
- After API restart when cubes need re-registration

This is the FALLBACK mechanism when auto-registration fails.

Steps to register:
1. First use memos_list_cubes() to find available cubes
2. Call this tool with the cube_id you want to register
3. Retry the original operation

The tool will:
1. Find the cube's full path from the cubes directory
2. Send registration request to MemOS API
3. Return success or detailed error message""",
            inputSchema={
                "type": "object",
                "properties": {
                    "cube_id": {
                        "type": "string",
                        "description": "ID of the cube to register (e.g., 'dev_cube', 'my_project_cube')"
                    },
                    "cube_path": {
                        "type": "string",
                        "description": "Optional: Full path to cube directory. If not provided, will be auto-detected from MEMOS_CUBES_DIR."
                    }
                },
                "required": ["cube_id"]
            }
        ),
        Tool(
            name="memos_create_user",
            description="""Create a user in MemOS.

USE THIS TOOL when you encounter:
- "User 'xxx' does not exist" error
- "User not found" error

This creates the user account needed to store and retrieve memories.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to create (e.g., 'dev_user')",
                        "default": MEMOS_USER
                    },
                    "user_name": {
                        "type": "string",
                        "description": "Display name for the user. Defaults to user_id if not provided."
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memos_validate_cubes",
            description="""Validate all cube configurations and fix namespace mismatches.

USE THIS TOOL to:
- Check if cube configs have correct user_name (should match cube_id)
- Auto-fix mismatched user_name in configs
- Detect cubes that may write to wrong namespace

This prevents the issue where memories are saved to wrong namespace
(e.g., saving to 'dev_user' instead of 'my_project_cube').

Returns:
- List of all cubes with their validation status
- Any fixes that were applied
- Warnings for potential issues""",
            inputSchema={
                "type": "object",
                "properties": {
                    "fix": {
                        "type": "boolean",
                        "description": "If true, automatically fix mismatched configs. Default: true",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="memos_calendar",
            description="""View student learning notes in calendar format.

USE THIS TOOL for student mode to:
- View notes by semester (Spring/Fall/Summer)
- Filter by specific course
- Browse by week number
- Get calendar overview of learning progress

Perfect for:
- "Show me this semester's notes"
- "What did I learn in week 3?"
- "List all notes for Math 101"

Views:
- list: Simple chronological list
- week: Day-by-day view with weekday headers
- month: Summary with note counts per day""",
            inputSchema={
                "type": "object",
                "properties": {
                    "semester": {
                        "type": "string",
                        "description": "Semester to view. Format: 'YYYY-Season' (e.g., '2026-Spring', '2025-Fall') or 'current' for auto-detect",
                        "default": "current"
                    },
                    "course": {
                        "type": "string",
                        "description": "Optional: Filter by course name or tag"
                    },
                    "week": {
                        "type": "integer",
                        "description": "Optional: Specific week number in semester (1-18)"
                    },
                    "view": {
                        "type": "string",
                        "description": "View format: 'list' (chronological), 'week' (by day), 'month' (summary)",
                        "enum": ["list", "week", "month"],
                        "default": "list"
                    },
                    "cube_id": {
                        "type": "string",
                        "description": "Memory cube ID. AUTO-DERIVE from project path.",
                        "default": MEMOS_DEFAULT_CUBE
                    }
                },
                "required": []
            }
        )
    ]

    # Conditionally add delete tool if enabled (dangerous operation, disabled by default)
    if MEMOS_ENABLE_DELETE:
        tools.append(
            Tool(
                name="memos_delete",
                description="""⚠️ DELETE memories from project memory. USE WITH CAUTION!

This tool is DISABLED by default. User must explicitly enable it via MEMOS_ENABLE_DELETE=true.

ONLY use this tool when the user EXPLICITLY requests deletion.
NEVER use this tool proactively or without user confirmation.

Operations:
- Delete a single memory by ID
- Delete multiple memories by IDs
- Delete ALL memories in a cube (requires delete_all=true)

Before deleting, always:
1. Confirm with the user what will be deleted
2. Show the memory content that will be deleted
3. Get explicit user approval""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "ID of the specific memory to delete. Get this from memos_search or memos_list."
                        },
                        "memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of memory IDs to delete in batch."
                        },
                        "cube_id": {
                            "type": "string",
                            "description": "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'",
                            "default": MEMOS_DEFAULT_CUBE
                        },
                        "delete_all": {
                            "type": "boolean",
                            "description": "Set to true to delete ALL memories in the cube. DANGEROUS! Requires explicit user confirmation.",
                            "default": False
                        }
                    },
                    "required": []
                }
            )
        )
        logger.debug("Delete tool enabled (MEMOS_ENABLE_DELETE=true)")

    return tools
