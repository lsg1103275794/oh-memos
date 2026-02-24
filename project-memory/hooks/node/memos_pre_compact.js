#!/usr/bin/env node
/**
 * MemOS Hook: PreCompact - Remind about MCP memos before context compaction
 *
 * When context is about to be compressed, output a reminder to stderr
 * so the model knows to use MCP memos tools (not mkdir/Write) after compaction.
 *
 * Hook type: PreCompact
 * Matcher: *
 */

console.error('[PreCompact] REMINDER: After compaction, use MCP memos tools (memos_search, memos_save, memos_list_v2) for ALL memory operations.');
console.error('[PreCompact] DO NOT create memory directories with mkdir. DO NOT write memory files manually.');
console.error('[PreCompact] Pass project_path parameter for correct cube routing.');
process.exit(0);
