/**
 * MemOS MCP Server - Tools Registry
 *
 * Defines all 20 memos_* tool schemas using Zod.
 */

import { z } from "zod";
import { MEMOS_DEFAULT_CUBE, MEMOS_USER } from "./config.js";

// ============================================================================
// Shared Parameter Schemas
// ============================================================================

const projectPathParam = z
  .string()
  .optional()
  .describe(
    "Your current working directory (project root). The cube_id will be auto-derived from this path. " +
    "PREFERRED over manually specifying cube_id. Example: '/mnt/g/Cyber/AudioCraft Studio' → 'audiocraft_studio_cube'"
  );

const cubeIdParam = z
  .string()
  .optional()
  .default(MEMOS_DEFAULT_CUBE)
  .describe(
    "Memory cube ID. Only use if you know the exact cube_id. Otherwise, pass project_path and let the server derive it."
  );

const memoryTypeEnum = z.enum([
  "ERROR_PATTERN", "DECISION", "MILESTONE", "BUGFIX",
  "FEATURE", "CONFIG", "CODE_PATTERN", "GOTCHA", "PROGRESS",
]);

// ============================================================================
// Tool Schema Definitions
// ============================================================================

export const toolSchemas = {
  memos_context_resume: {
    description: `Recover project context after context compaction or at session start.

Call this tool when:
- Context was just compacted (you lost conversation history)
- You're unsure what was being worked on
- Starting a new session and need project context

Returns: Recent memories (last 24h), active project summary, and session state.

⚠️ IMPORTANT: After calling this, use MCP memos tools for ALL memory operations.
NEVER use mkdir or Write to create memory files. All memories live in MCP memos.`,
    inputSchema: z.object({
      project_path: projectPathParam,
      cube_id: cubeIdParam,
    }),
  },

  memos_search: {
    description: `Search project memories for relevant context.

USE THIS TOOL PROACTIVELY when:
- You encounter an error or exception (search for ERROR_PATTERN)
- User mentions "之前", "上次", "previously", "last time"
- You need to understand past decisions (search for DECISION)
- You're about to modify code that might have gotchas (search for GOTCHA)
- You see similar code patterns (search for CODE_PATTERN)
- Working with configuration files (search for CONFIG)

Results are automatically compacted when exceeding threshold (15+ items).
Use memos_get(memory_id) to retrieve full details of specific memories.

⚠️ IMPORTANT: After context compaction, call this tool to recover project context.
NEVER use mkdir, Write, or file operations to create memory files — all memories are stored in MCP memos.`,
    inputSchema: z.object({
      query: z.string().describe(
        "Search query. Can be natural language or prefixed with memory type (e.g., 'ERROR_PATTERN ModuleNotFoundError', 'DECISION authentication')"
      ),
      project_path: projectPathParam,
      cube_id: cubeIdParam,
      top_k: z.number().int().optional().default(10).describe("Maximum number of results to return (default: 10)"),
      compact: z.boolean().optional().default(true).describe("Enable context compression for large results (default: true). Set to false to get full results."),
    }),
  },

  memos_search_context: {
    description: `Context-aware memory search with LLM intent analysis.

USE THIS TOOL when you need smarter search that understands:
- The broader conversation context (what you've been discussing)
- Implied entities and concepts that aren't explicitly mentioned
- The type of information the user is really looking for

Example: If you've been discussing "login errors" and user asks "what was the solution?",
this tool understands they mean "login error solution" even without explicit mention.

Best used when:
- Query is ambiguous or refers to earlier conversation
- You want better recall through query expansion
- You need to find related concepts, not just exact matches`,
    inputSchema: z.object({
      query: z.string().describe("Search query - can be brief since context helps clarify intent"),
      context: z.array(z.object({
        role: z.enum(["user", "assistant"]),
        content: z.string(),
      })).optional().describe("Recent conversation messages for context (last 5-10 turns)"),
      cube_id: z.string().optional().default(MEMOS_DEFAULT_CUBE).describe("Memory cube ID. AUTO-DERIVE from project path."),
    }),
  },

  memos_save: {
    description: `Save important information to project memory.

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

⚠️ This is the ONLY way to save memories. NEVER use mkdir or Write tool to create memory directories/files.`,
    inputSchema: z.object({
      content: z.string().describe("Memory content to save. Be detailed - include context, rationale, and relevant code/commands."),
      memory_type: memoryTypeEnum.describe(
        "**REQUIRED** - Type of memory. Decision tree: Bug fix → BUGFIX/ERROR_PATTERN, Technical decision → DECISION, Gotcha → GOTCHA, Code template → CODE_PATTERN, Config change → CONFIG, New feature → FEATURE, Achievement → MILESTONE, Pure progress update → PROGRESS"
      ),
      project_path: projectPathParam,
      cube_id: cubeIdParam,
    }),
  },

  memos_list_v2: {
    description: `List memories from a memory cube with context compression.

Results are automatically compacted when exceeding threshold (15+ items) to save context window.
Use memos_get(memory_id) to retrieve full details of specific memories.

Set compact=false to disable compression and get full results.`,
    inputSchema: z.object({
      project_path: projectPathParam,
      cube_id: cubeIdParam,
      limit: z.number().int().optional().default(20).describe("Maximum number of memories to return."),
      memory_type: memoryTypeEnum.optional().describe("Optional: Filter by memory type (e.g., DECISION, ERROR_PATTERN)."),
      compact: z.boolean().optional().default(true).describe("Enable context compression for large results (default: true). Set to false to get full results."),
    }),
  },

  memos_get: {
    description: `Get full details of a single memory by ID.

Use this after memos_search or memos_list_v2 returns compacted results.
Retrieves complete memory content, metadata, background, and relations.

Example: memos_get(memory_id="abc123-def456-...")`,
    inputSchema: z.object({
      memory_id: z.string().describe("The full memory ID to retrieve (from memos_search or memos_list_v2 results)"),
      cube_id: z.string().optional().default(MEMOS_DEFAULT_CUBE).describe("Memory cube ID. AUTO-DERIVE from project path."),
    }),
  },

  memos_suggest: {
    description: `Get smart suggestions for memory searches based on current context.

Use this when you're unsure what to search for. Provide the current context
(error message, code snippet, user question) and get relevant search suggestions.`,
    inputSchema: z.object({
      context: z.string().describe("Current context (error message, code, user question)"),
    }),
  },

  memos_list_cubes: {
    description: `List all available memory cubes in the system.

USE THIS TOOL when:
- You encounter "cube not found" errors
- User asks which cubes are available
- You need to verify a cube exists before using it
- Starting a new project and want to see existing cubes

Returns:
- List of available cube IDs with their paths
- Registration status for each cube
- Helpful guidance if no cubes are found`,
    inputSchema: z.object({
      include_status: z.boolean().optional().default(false).describe("Include registration status for each cube (requires API call)"),
    }),
  },

  memos_get_stats: {
    description: `Get statistics about memories in a project cube.

Use this to see how many memories of each type (DECISION, ERROR_PATTERN, etc.) are stored.`,
    inputSchema: z.object({
      cube_id: z.string().optional().default(MEMOS_DEFAULT_CUBE).describe("Memory cube ID (project name)"),
    }),
  },

  memos_trace_path: {
    description: `Trace reasoning paths between two memory nodes.

USE THIS TOOL when you need to understand:
- How two concepts or events are connected
- The chain of causality or dependencies between memories
- Indirect relationships that span multiple hops

Returns:
- Whether a path exists between the two nodes
- Full path details with all intermediate nodes and edges
- The relationship types along the path (CAUSE, RELATE, CONDITION, etc.)

Example: Tracing from "Java not installed" to "API timeout error" might reveal:
  [Java not installed] ──CAUSE──> [Neo4j failed] ──CAUSE──> [DB connection lost] ──CAUSE──> [API timeout]`,
    inputSchema: z.object({
      source_id: z.string().describe("ID of the source memory node to start from. Get this from memos_search or memos_get_graph."),
      target_id: z.string().describe("ID of the target memory node to find path to. Get this from memos_search or memos_get_graph."),
      max_depth: z.number().int().optional().default(3).describe("Maximum path length (hops). Default 3, max 10."),
      cube_id: z.string().optional().default(MEMOS_DEFAULT_CUBE).describe("Memory cube ID. AUTO-DERIVE from project path."),
    }),
  },

  memos_get_graph: {
    description: `Get memory knowledge graph with relationships.

USE THIS TOOL when you need to understand:
- How memories are connected (dependencies, causality)
- What caused a particular issue (CAUSE relationships)
- Related context around a topic (RELATE relationships)
- Conflicting information (CONFLICT relationships)

Returns:
- Memory nodes matching the query
- Relationships between memories: CAUSE, RELATE, CONFLICT, CONDITION

Example: If you search "Neo4j startup failure", you might see:
  [Java not installed] ──CAUSE──> [Neo4j failed to start]`,
    inputSchema: z.object({
      query: z.string().describe("Search query to find related memories and their relationships"),
      cube_id: z.string().optional().default(MEMOS_DEFAULT_CUBE).describe(
        "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'. Example: /mnt/g/test/MemOS → 'memos_cube', ~/my-app → 'my_app_cube'"
      ),
    }),
  },

  memos_export_schema: {
    description: `Export knowledge graph schema and statistics.

USE THIS TOOL when you need to understand:
- The overall structure of the project's memory graph
- What types of relationships exist in the knowledge base
- How well-connected the memories are
- The most common tags and memory types
- Time range of stored knowledge

Returns comprehensive statistics including:
- Total nodes and edges
- Relationship type distribution (CAUSE, RELATE, CONFLICT, etc.)
- Memory type distribution (LongTermMemory, WorkingMemory, etc.)
- Top 20 most frequent tags
- Average and max connections per node
- Number of orphan (unconnected) nodes
- Time range of data`,
    inputSchema: z.object({
      cube_id: z.string().optional().default(MEMOS_DEFAULT_CUBE).describe("Memory cube ID. AUTO-DERIVE from project path."),
      sample_size: z.number().int().optional().default(100).describe("Number of nodes to sample for analysis (10-1000). Default 100."),
    }),
  },

  memos_register_cube: {
    description: `Register a memory cube with the MemOS API.

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
3. Return success or detailed error message`,
    inputSchema: z.object({
      cube_id: z.string().describe("ID of the cube to register (e.g., 'dev_cube', 'my_project_cube')"),
      cube_path: z.string().optional().describe("Optional: Full path to cube directory. If not provided, will be auto-detected from MEMOS_CUBES_DIR."),
    }),
  },

  memos_create_user: {
    description: `Create a user in MemOS.

USE THIS TOOL when you encounter:
- "User 'xxx' does not exist" error
- "User not found" error

This creates the user account needed to store and retrieve memories.`,
    inputSchema: z.object({
      user_id: z.string().optional().default(MEMOS_USER).describe("User ID to create (e.g., 'dev_user')"),
      user_name: z.string().optional().describe("Display name for the user. Defaults to user_id if not provided."),
    }),
  },

  memos_validate_cubes: {
    description: `Validate all cube configurations and fix namespace mismatches.

USE THIS TOOL to:
- Check if cube configs have correct user_name (should match cube_id)
- Auto-fix mismatched user_name in configs
- Detect cubes that may write to wrong namespace

This prevents the issue where memories are saved to wrong namespace
(e.g., saving to 'dev_user' instead of 'my_project_cube').

Returns:
- List of all cubes with their validation status
- Any fixes that were applied
- Warnings for potential issues`,
    inputSchema: z.object({
      fix: z.boolean().optional().default(true).describe("If true, automatically fix mismatched configs. Default: true"),
    }),
  },

  memos_impact: {
    description:
      "Analyze the forward impact of a memory — what events, decisions, " +
      "or milestones were caused or followed by this memory. " +
      "Returns a grouped 'blast radius' view (direct → indirect hops). " +
      "Use after memos_search or memos_get_graph to get a memory_id.",
    inputSchema: z.object({
      memory_id: z.string().describe("ID of the source memory to analyze impact from"),
      cube_id: cubeIdParam,
      project_path: projectPathParam,
      max_depth: z.number().int().optional().default(3).describe("Maximum hops to trace forward (default: 3, max: 6)"),
    }),
  },

  memos_calendar: {
    description: `View memories in calendar format. Supports two modes:

PROJECT MODE (mode="project"):
- Shows milestone timeline grouped by month
- Filters MILESTONE, DECISION, FEATURE, BUGFIX, GOTCHA types
- Perfect for: "Show project timeline", "What milestones this month?"

STUDENT MODE (mode="student", default):
- View notes by semester (Spring/Fall/Summer)
- Filter by specific course
- Browse by week number

Views (student mode): list, week, month`,
    inputSchema: z.object({
      mode: z.enum(["project", "student"]).optional().default("student").describe(
        "Mode: 'project' for milestone timeline, 'student' for learning notes calendar"
      ),
      semester: z.string().optional().default("current").describe("Semester to view (student mode). Format: 'YYYY-Season' or 'current'"),
      course: z.string().optional().describe("Optional: Filter by course name or tag (student mode)"),
      week: z.number().int().optional().describe("Optional: Specific week number in semester 1-18 (student mode)"),
      view: z.enum(["list", "week", "month"]).optional().default("list").describe("View format (student mode): 'list', 'week', 'month'"),
      cube_id: z.string().optional().default(MEMOS_DEFAULT_CUBE).describe("Memory cube ID. AUTO-DERIVE from project path."),
    }),
  },

  // Delete tool schema (registered conditionally)
  memos_delete: {
    description: `⚠️ DELETE memories from project memory. USE WITH CAUTION!

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
3. Get explicit user approval`,
    inputSchema: z.object({
      memory_id: z.string().optional().describe("ID of the specific memory to delete. Get this from memos_search or memos_list."),
      memory_ids: z.array(z.string()).optional().describe("List of memory IDs to delete in batch."),
      cube_id: z.string().optional().default(MEMOS_DEFAULT_CUBE).describe(
        "Memory cube ID. AUTO-DERIVE from project path: extract folder name, lowercase, replace -/./space with _, append '_cube'"
      ),
      delete_all: z.boolean().optional().default(false).describe("Set to true to delete ALL memories in the cube. DANGEROUS! Requires explicit user confirmation."),
    }),
  },
};
