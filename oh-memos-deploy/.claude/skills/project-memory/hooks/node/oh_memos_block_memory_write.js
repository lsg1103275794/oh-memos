#!/usr/bin/env node
/**
 * oh-memos Hook: PreToolUse - Block built-in file-based memory writes
 *
 * Claude Code 2.x ships a built-in file-based memory feature. Its system prompt
 * tells the agent to Write markdown straight into:
 *
 *     ~/.claude/projects/<encoded-project>/memory/*.md
 *
 * complete with `name` / `description` / `metadata.type` frontmatter and a
 * MEMORY.md index. That instruction lives in the system prompt, which outranks
 * CLAUDE.md — so a project rule saying "all memory goes through MCP oh-memos"
 * loses on its own. The agent is not misbehaving; it is following a higher
 * priority instruction.
 *
 * This hook closes that gap. It does not merely block: it names the replacement
 * tool on stderr so the agent switches to memos_save instead of retrying the
 * same Write and burning turns.
 *
 * Scope is deliberately narrow — ONLY the built-in memory directory. A project's
 * own project-memory/, docs/memory-wiki/ or any other memory/*.md is untouched.
 *
 * Hook type: PreToolUse
 * Matcher:   Write|Edit|MultiEdit|NotebookEdit
 *
 * Exit codes: 2 blocks the call (1 does NOT — see README "matcher 语法陷阱").
 */

let input = '';
process.stdin.on('data', chunk => (input += chunk));
process.stdin.on('end', () => {
  const allow = () => {
    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
    process.exit(0);
  };

  try {
    const data = JSON.parse(input);
    const filePath = data.tool_input?.file_path || '';
    if (!filePath) return allow();

    // Normalise Windows backslashes so one pattern covers every platform.
    const normalised = filePath.replace(/\\/g, '/');

    const isBuiltinMemory =
      /\.claude\/projects\/[^/]+\/memory\//i.test(normalised) &&
      /\.md$/i.test(normalised);

    if (!isBuiltinMemory) return allow();

    const cwd = data.cwd || process.cwd();

    console.error('[oh-memos] BLOCKED: this is Claude Code built-in file-based memory.');
    console.error('[oh-memos] Project rule: all memory operations go through MCP oh-memos.');
    console.error('[oh-memos]');
    console.error(`[oh-memos] Use instead:  memos_save(content="...", memory_type="...", project_path="${cwd}")`);
    console.error('[oh-memos] memory_type: BUGFIX | ERROR_PATTERN | DECISION | GOTCHA | CODE_PATTERN |');
    console.error('[oh-memos]              CONFIG | MILESTONE | FEATURE | PROGRESS | SYNTHESIS');
    console.error('[oh-memos]');
    console.error('[oh-memos] Do not retry this Write. Do not fall back to Edit or Bash.');
    console.error(`[oh-memos] Blocked path: ${filePath}`);
    process.exit(2);
  } catch (e) {
    // Never block on a parse failure — fail open.
    allow();
  }
});
