#!/usr/bin/env node
/**
 * MemOS Hook: PreToolUse - Block mkdir for memory directories
 *
 * Prevents the model from creating memory directories manually.
 * After context compaction, models sometimes try to mkdir memory folders
 * instead of using MCP memos tools.
 *
 * Hook type: PreToolUse
 * Matcher: tool == "Bash" && tool_input.command matches "mkdir.*memory"
 */

let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const command = (data.tool_input?.command || '').toLowerCase();

    if (command.includes('mkdir') && command.includes('memory')) {
      console.error('[MemOS] BLOCKED: Do not create memory directories manually.');
      console.error('[MemOS] Use MCP memos tools instead: oh_memos_save, oh_memos_search, oh_memos_list_v2');
      console.error('[MemOS] Pass project_path parameter for correct cube routing.');
      process.exit(1);
    }

    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
  } catch (e) {
    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
  }
});
