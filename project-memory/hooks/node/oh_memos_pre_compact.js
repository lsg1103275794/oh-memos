#!/usr/bin/env node
/**
 * MemOS Hook: PreCompact
 *
 * Fires BEFORE context compaction. Two responsibilities:
 * 1. Remind the model to save key memories NOW (before context is lost)
 * 2. Tell the model to call oh_memos_context_resume AFTER compaction completes
 *
 * Install: Copy to ~/.claude/hooks/scripts/pre-compact.js
 * Config: Add to settings.json PreCompact hooks
 */

console.error('');
console.error('================================================================');
console.error('  ⚠️  CONTEXT COMPACTION IMMINENT');
console.error('================================================================');
console.error('');
console.error('  BEFORE compaction — save key memories NOW:');
console.error('    oh_memos_save(content=..., memory_type="PROGRESS",');
console.error('                  project_path="<current working dir>")');
console.error('');
console.error('  AFTER compaction — recover context:');
console.error('    oh_memos_context_resume(project_path="<current working dir>")');
console.error('');
console.error('  NEVER use mkdir or Write for memory files.');
console.error('  ALL memory operations via MCP memos tools only.');
console.error('================================================================');
console.error('');
process.exit(0);
