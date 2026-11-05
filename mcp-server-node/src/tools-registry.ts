/**
 * MemOS MCP Server - Tools Registry
 *
 * Defines all 15 memos_* tool schemas using Zod (graph/admin operations are
 * consolidated behind mode/action parameters to keep the always-on tool
 * surface small).
 */

import { z } from "zod";
import { MEMOS_DEFAULT_CUBE } from "./config.js";

// ============================================================================
// Shared Parameter Schemas
// ============================================================================

const projectPathParam = z
  .string()
  .optional()
  .describe(
    "Project root; the cube_id is derived from it, so this is usually all you need. " +
      "Example: '/mnt/g/Cyber/AudioCraft Studio' → 'audiocraft_studio_cube'",
  );

const cubeIdParam = z
  .string()
  .optional()
  .default(MEMOS_DEFAULT_CUBE)
  .describe(
    "Exact cube id, for when you know it. With neither project_path nor cube_id, " +
      "the server uses the default cube, which may belong to another project.",
  );

// Brief variants for every tool except the hot paths (save/search): the full
// routing story is told once there; repeating it on every tool cost ~1.4k
// tokens of pure duplication on the tool surface.
const projectPathBrief = z
  .string()
  .optional()
  .describe("Project root; cube_id is derived from it (details: memos_search)");
const cubeIdBrief = z
  .string()
  .optional()
  .describe("Explicit cube id; prefer project_path");
const cubeIdBriefDefault = cubeIdBrief.default(MEMOS_DEFAULT_CUBE);

const memoryTypeEnum = z.enum([
  "ERROR_PATTERN",
  "DECISION",
  "MILESTONE",
  "BUGFIX",
  "FEATURE",
  "CONFIG",
  "CODE_PATTERN",
  "GOTCHA",
  "PROGRESS",
  "SYNTHESIS",
]);

// ============================================================================
// Tool Schema Definitions
// ============================================================================

export const toolSchemas = {
  memos_context_resume: {
    description: `Recover project context after context compaction or at session start: returns recent memories (24h) + project state.`,
    inputSchema: z.object({
      project_path: projectPathBrief,
      cube_id: cubeIdBriefDefault,
    }),
  },

  memos_search: {
    description: `Search this project's saved memories by meaning and keywords, ranked by relevance, freshness and source quality. Useful for past decisions, earlier fixes, known gotchas, and when the user refers to earlier work.
A query can start with a type ("DECISION auth"). Pass context (recent turns) when the query depends on the conversation; it enables intent analysis and query expansion.
Large results are compacted; memos_get(memory_id) returns full details. Lite mode caps results and leaves out auto-captured memories by default.`,
    inputSchema: z.object({
      query: z
        .string()
        .describe(
          "Search query. Can be natural language or prefixed with memory type (e.g., 'ERROR_PATTERN ModuleNotFoundError')",
        ),
      context: z
        .array(
          z.object({
            role: z.enum(["user", "assistant"]),
            content: z.string(),
          }),
        )
        .optional()
        .describe(
          "Recent conversation turns (last 5-10); triggers context-aware search",
        ),
      project_path: projectPathParam,
      cube_id: cubeIdParam,
      top_k: z
        .number()
        .int()
        .optional()
        .default(10)
        .describe("Max results (default 10)"),
      compact: z
        .boolean()
        .optional()
        .default(true)
        .describe("Compact large results (default true)"),
    }),
  },

  memos_think: {
    description: `Evidence pack for a question: retrieves memories, flags contradiction/staleness candidates and coverage gaps.
YOU synthesize the answer from it, citing [n]; persist valuable syntheses via memos_save(memory_type="SYNTHESIS") keeping the [n]→id map.`,
    inputSchema: z.object({
      query: z.string().describe("The question to gather evidence for"),
      project_path: projectPathBrief,
      cube_id: cubeIdBriefDefault,
      top_k: z
        .number()
        .int()
        .optional()
        .default(15)
        .describe("Evidence pool size (3-30)"),
      fresh_days: z
        .number()
        .int()
        .optional()
        .default(30)
        .describe("Days before time-sensitive memories count as stale"),
    }),
  },

  memos_export_wiki: {
    description: `Export a cube as an interlinked markdown wiki (page per memory + index.md + graph.md), git-friendly.
Default output <project_path>/docs/memory-wiki; re-export replaces only files it generated, foreign files are kept.`,
    inputSchema: z.object({
      project_path: projectPathBrief,
      cube_id: cubeIdBriefDefault,
      output_dir: z
        .string()
        .optional()
        .describe(
          "Target directory (default: <project_path>/docs/memory-wiki)",
        ),
      include_archived: z
        .boolean()
        .optional()
        .default(false)
        .describe("Also export archived memories"),
    }),
  },

  memos_import_wiki: {
    description: `Import a wiki back into its cube — round-trip for memos_export_wiki: creates missing pages, skips unchanged ones, and can version edited pages.
Use after editing exported pages (fixes, cleanup, migration to a fresh cube). Reads only pages/ with the exporter marker; never deletes; restores type/tags/confidence/status/timestamps, while relation wikilinks remain report-only.`,
    inputSchema: z.object({
      project_path: projectPathBrief,
      cube_id: cubeIdBriefDefault,
      wiki_dir: z
        .string()
        .optional()
        .describe("Wiki directory (default: <project_path>/docs/memory-wiki)"),
      dry_run: z
        .boolean()
        .optional()
        .default(false)
        .describe("Preview the diff without writing (default false)"),
      on_edit: z
        .enum(["skip", "version"])
        .optional()
        .default("skip")
        .describe(
          "Edited pages: skip (default) or save as new version (old memory kept)",
        ),
    }),
  },

  memos_save: {
    description: `Save something worth keeping across sessions: a decision, bug fix, gotcha, config change or milestone. memory_type sets the category; memos_suggest explains each one. Works in Lite mode too.
Later sessions only find what is saved here, not memory files written by hand.`,
    inputSchema: z.object({
      content: z
        .string()
        .describe(
          "Memory content. Be detailed — include context, rationale, relevant code/commands.",
        ),
      memory_type: memoryTypeEnum.describe(
        "**REQUIRED**. bug fix → BUGFIX/ERROR_PATTERN · decision → DECISION · gotcha → GOTCHA · " +
          "template → CODE_PATTERN · config → CONFIG · feature → FEATURE · achievement → MILESTONE · " +
          "status update → PROGRESS · synthesized answer → SYNTHESIS. Full rules: memos_suggest",
      ),
      project_path: projectPathParam,
      cube_id: cubeIdParam,
    }),
  },

  memos_list_v2: {
    description: `List memories from a cube (compacted when large; memos_get for details).`,
    inputSchema: z.object({
      project_path: projectPathBrief,
      cube_id: cubeIdBriefDefault,
      limit: z
        .number()
        .int()
        .optional()
        .default(20)
        .describe("Max memories returned"),
      memory_type: memoryTypeEnum.optional().describe("Filter by type"),
      compact: z
        .boolean()
        .optional()
        .default(true)
        .describe("Compact large results"),
    }),
  },

  memos_get: {
    description: `Get full details of one memory by ID (after compacted memos_search/memos_list_v2 results).`,
    inputSchema: z.object({
      memory_id: z.string().describe("Memory ID from search/list results"),
      project_path: projectPathBrief,
      cube_id: cubeIdBriefDefault,
    }),
  },

  memos_suggest: {
    description: `Suggest search queries for the current context, and return the memory_type decision tree.

Use when: unsure what to search for, or unsure which memory_type \`memos_save\` should use.`,
    inputSchema: z.object({
      context: z
        .string()
        .describe("Current context (error message, code, user question)"),
    }),
  },

  memos_distill_skill: {
    description: `Create an inert, reviewable skill candidate from recurring memories. It writes only under <project_path>/skill-candidates and records source memory IDs; it never installs a skill automatically.`,
    inputSchema: z.object({
      project_path: projectPathBrief,
      title: z.string().describe("Candidate skill title"),
      summary: z.string().describe("Reviewed workflow summary"),
      memory_ids: z
        .array(z.string())
        .min(1)
        .describe("Evidence memory IDs supporting this workflow"),
    }),
  },

  memos_list_skill_candidates: {
    description: `List inert skill candidates under <project_path>/skill-candidates. Does not install or modify them.`,
    inputSchema: z.object({ project_path: projectPathBrief }),
  },

  memos_review_skill_candidate: {
    description: `Approve or reject one skill candidate. This only changes its auditable status; approval does not install it.`,
    inputSchema: z.object({
      project_path: projectPathBrief,
      candidate_id: z.string().describe("Candidate markdown filename"),
      action: z.enum(["approve", "reject"]),
      reviewer: z.string().describe("Human reviewer identity"),
    }),
  },

  memos_install_skill_candidate: {
    description: `Install an approved candidate into <project_path>/.claude/skills/<slug>/SKILL.md. Requires explicit action; refuses overwrite, symlinks, malformed candidates, and unapproved status.`,
    inputSchema: z.object({
      project_path: projectPathBrief,
      candidate_id: z.string(),
    }),
  },

  memos_graph: {
    description: `Knowledge-graph queries; mode selects:
related = nodes+edges around a query · path = trace between two node ids · impact = forward blast radius of one memory · schema = graph structure & statistics · import = validate Graphify node-link JSON (dry-run only).`,
    inputSchema: z.object({
      mode: z
        .enum(["related", "path", "impact", "schema", "import"])
        .describe("Query kind"),
      query: z.string().optional().describe("related: search query"),
      source_id: z.string().optional().describe("path: start node id"),
      target_id: z.string().optional().describe("path: end node id"),
      memory_id: z.string().optional().describe("impact: source memory id"),
      max_depth: z
        .number()
        .int()
        .optional()
        .default(3)
        .describe("path/impact: max hops"),
      sample_size: z
        .number()
        .int()
        .optional()
        .default(100)
        .describe("schema: nodes sampled"),
      graph_json: z
        .string()
        .optional()
        .describe(
          "import: Graphify graph.json contents; validation is dry-run and never writes data",
        ),
      project_key: z
        .string()
        .optional()
        .describe("import: stable project namespace label"),
      project_path: projectPathBrief,
      cube_id: cubeIdBriefDefault,
    }),
  },

  memos_admin: {
    description: `Maintenance & diagnostics; action selects:
list_cubes · register_cube (fix "not loaded") · create_user (fix "user does not exist") · validate_cubes (repair config mismatches) · stats (per-type counts) · calendar (milestone timeline) · capabilities (Full/Lite behavior and unsupported operations).`,
    inputSchema: z.object({
      action: z
        .enum([
          "list_cubes",
          "register_cube",
          "create_user",
          "validate_cubes",
          "stats",
          "calendar",
          "capabilities",
        ])
        .describe("Operation"),
      cube_id: cubeIdBrief,
      project_path: projectPathBrief,
      cube_path: z
        .string()
        .optional()
        .describe("register_cube: cube directory (auto-detected if omitted)"),
      user_id: z.string().optional().describe("create_user: user id"),
      user_name: z.string().optional().describe("create_user: display name"),
      fix: z
        .boolean()
        .optional()
        .default(true)
        .describe("validate_cubes: auto-fix"),
      include_status: z
        .boolean()
        .optional()
        .default(false)
        .describe("list_cubes: check registration"),
      mode: z
        .enum(["project", "student"])
        .optional()
        .describe("calendar: view mode"),
      semester: z
        .string()
        .optional()
        .describe("calendar student: 'YYYY-Season' or 'current'"),
      course: z.string().optional().describe("calendar student: course filter"),
      week: z.number().int().optional().describe("calendar student: week 1-18"),
      view: z
        .enum(["list", "week", "month"])
        .optional()
        .describe("calendar student: format"),
    }),
  },

  memos_canvas: {
    description: `Task canvas — short-term task state that survives context compaction.
action: open (needs goal) · update (append node; node_id edits one) · show · list · delete.
Node ids are greppable (000-N1); ref anchors evidence: mem:<id> / file:<path> / note:<text>.`,
    inputSchema: z.object({
      action: z.enum(["open", "update", "show", "list", "delete"]),
      project_path: projectPathBrief,
      cube_id: cubeIdBrief,
      name: z
        .string()
        .optional()
        .describe("update/show/delete: canvas name (from list)"),
      goal: z.string().optional().describe("open: the task"),
      node_id: z
        .string()
        .optional()
        .describe("update: edit this node, else append"),
      summary: z
        .string()
        .optional()
        .describe("update: step text (required to append)"),
      status: z.enum(["todo", "doing", "done", "blocked"]).optional(),
      ref: z.string().optional().describe("update: evidence anchor"),
      confirm: z
        .boolean()
        .optional()
        .describe(
          "delete: required only when the canvas still has unfinished nodes",
        ),
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
      memory_id: z
        .string()
        .optional()
        .describe(
          "ID of the specific memory to delete. Get this from memos_search or memos_list.",
        ),
      memory_ids: z
        .array(z.string())
        .optional()
        .describe("List of memory IDs to delete in batch."),
      project_path: projectPathBrief,
      cube_id: cubeIdBriefDefault,
      delete_all: z
        .boolean()
        .optional()
        .default(false)
        .describe(
          "Set to true to delete ALL memories in the cube. DANGEROUS! Requires explicit user confirmation.",
        ),
    }),
  },
};

// ============================================================================
// Tool Annotations
// ============================================================================

/**
 * Every tool that changes state. This is the single source of truth: the
 * read-only hints below are derived from it, so a tool can never be described
 * as safe in one place and destructive in another.
 *
 * Getting this wrong is not cosmetic — a client that trusts `readOnlyHint`
 * may auto-approve the call without asking the user, so mislabelling
 * `memos_delete` would hand out silent deletions.
 */
export const WRITE_TOOLS: ReadonlySet<string> = new Set([
  "memos_save",
  "memos_delete",
  "memos_admin", // register_cube / create_user / validate_cubes mutate state
  "memos_export_wiki", // writes: renders wiki .md files into the target project
  "memos_import_wiki", // writes: creates/versions memories from wiki pages
  "memos_canvas", // open/update write a .mmd file under the cube
  "memos_distill_skill", // writes an inert candidate under the project
  "memos_review_skill_candidate", // auditable status transition
  "memos_install_skill_candidate", // explicit local install
]);

/**
 * Tools whose work leaves the local stack: these embed the query or run LLM
 * extraction, so they reach the model relay rather than only Neo4j/Qdrant.
 * Everything else answers from local storage alone.
 */
const REMOTE_TOOLS: ReadonlySet<string> = new Set([
  "memos_save", // LLM extraction + embedding on the way in
  "memos_import_wiki", // embedding on create/version writes
  "memos_search", // embeds the query; with context, adds LLM intent analysis
  "memos_graph", // mode=related goes through /search, so it embeds too
  "memos_think", // evidence retrieval goes through /search, embeds the query
  "memos_distill_skill", // creates a local candidate only
]);

export interface ToolAnnotations {
  readOnlyHint: boolean;
  openWorldHint: boolean;
}

// A name in either set that no longer exists means a tool was renamed and the
// set was not updated — which would silently downgrade a write tool to
// read-only. Fail at import instead: this is authoring error, not user input,
// so it surfaces on the first build rather than in a client's permission prompt.
for (const name of [...WRITE_TOOLS, ...REMOTE_TOOLS]) {
  if (!(name in toolSchemas)) {
    throw new Error(
      `tools-registry: '${name}' is annotated but has no schema — rename out of sync`,
    );
  }
}

export const toolAnnotations: Record<string, ToolAnnotations> =
  Object.fromEntries(
    Object.keys(toolSchemas).map((name) => [
      name,
      {
        readOnlyHint: !WRITE_TOOLS.has(name),
        openWorldHint: REMOTE_TOOLS.has(name),
      },
    ]),
  );
