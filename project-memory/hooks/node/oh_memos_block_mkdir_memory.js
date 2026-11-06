#!/usr/bin/env node
/**
 * MemOS Hook: PreToolUse - Block mkdir for memory directories
 *
 * Prevents the model from creating memory directories manually.
 * After context compaction, models sometimes try to mkdir memory folders
 * instead of using MCP memos tools.
 *
 * Hook type: PreToolUse
 * Matcher:   Bash|PowerShell  (on Windows, Claude Code runs shell commands
 *            through the PowerShell tool; its input has the same `command`)
 *
 * NOTE: the matcher must be the bare tool name. `matcher` is evaluated against
 * the TOOL NAME only — a value containing characters outside
 * [A-Za-z0-9_-, |*] is treated as an unanchored regex, so an expression like
 * `tool == "Bash" && tool_input.command matches "mkdir.*memory"` never matches
 * and the hook silently never fires. The mkdir/memory condition is checked in
 * this script instead. See README "matcher 语法陷阱".
 *
 * Exit codes: 2 blocks the call. 1 does NOT block — it is a non-blocking error.
 */

/**
 * A command segment creates something under a `memory` directory when it starts
 * with mkdir (Bash, or the PowerShell alias) or New-Item and one of its arguments
 * has a path segment that is exactly `memory`. Checking only the start of each
 * segment lets through commands that merely mention the words, such as a commit
 * message or a path to this script.
 */
const CREATE = /^\s*(?:sudo\s+)?(?:mkdir|new-item)\b/i;
const MEMORY_SEGMENT = /(?:^|[\s\/\\"'=])memory(?=$|[\s\/\\"'])/i;

function createsMemoryPath(command) {
  return String(command)
    .split(/&&|\|\||[;|\n]/)
    .some(seg => CREATE.test(seg) && MEMORY_SEGMENT.test(seg.replace(CREATE, '')));
}

let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);

    if (createsMemoryPath(data.tool_input?.command || '')) {
      const cwd = data.cwd || process.cwd();
      console.error('[oh-memos] BLOCKED: Do not create memory directories or files from the shell.');
      console.error('[oh-memos] Use the oh-memos MCP tools instead: memos_save, memos_search, memos_list_v2');
      console.error(`[oh-memos] Pass project_path for correct cube routing, e.g. project_path="${cwd}"`);
      process.exit(2);
    }

    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
  } catch (e) {
    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
  }
});
