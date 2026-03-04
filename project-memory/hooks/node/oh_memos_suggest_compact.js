#!/usr/bin/env node
/**
 * Context Usage Monitor + Memory Save Reminder
 *
 * Tracks tool call count as a proxy for context usage.
 * At ~70% usage: gentle reminder to save memories
 * At ~90% usage: urgent reminder to save NOW
 *
 * Install: Copy to ~/.claude/hooks/scripts/suggest-compact.js
 * Config: Add to settings.json PreToolUse hooks (matcher: "Edit|Write")
 *
 * Env vars:
 *   COMPACT_WARN=40      Tool calls before gentle reminder
 *   COMPACT_CRITICAL=60  Tool calls before urgent reminder
 */

const path = require('path');
const fs = require('fs');
const os = require('os');

function readFile(p) { try { return fs.readFileSync(p, 'utf8'); } catch { return null; } }
function writeFile(p, c) { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, c, 'utf8'); }
function log(msg) { console.error(msg); }

const sessionId = process.env.CLAUDE_SESSION_ID || process.ppid || 'default';
const counterFile = path.join(os.tmpdir(), `claude-tool-count-${sessionId}`);
const WARN = parseInt(process.env.COMPACT_WARN || '40', 10);
const CRITICAL = parseInt(process.env.COMPACT_CRITICAL || '60', 10);

let count = 1;
const existing = readFile(counterFile);
if (existing) count = parseInt(existing.trim(), 10) + 1;
writeFile(counterFile, String(count));

if (count === WARN) {
  log('');
  log(`[Memory] → ${count} tool calls → context window filling up`);
  log('[Memory] Consider saving important findings:');
  log('[Memory]   oh_memos_save(content=..., memory_type="PROGRESS", project_path="<cwd>")');
  log('');
}

if (count === CRITICAL) {
  log('');
  log('====================================================');
  log('  🚨 CONTEXT NEARLY FULL — SAVE MEMORIES NOW');
  log('====================================================');
  log('  Call oh_memos_save for any unsaved key context:');
  log('  - Current task progress (PROGRESS)');
  log('  - Bugs found/fixed (BUGFIX)');
  log('  - Decisions made (DECISION)');
  log('  - Gotchas discovered (GOTCHA)');
  log('');
  log('  After compaction, call:');
  log('  oh_memos_context_resume(project_path="<cwd>")');
  log('====================================================');
  log('');
}

if (count > CRITICAL && count % 10 === 0) {
  log(`[Memory] ⚠️ ${count} tool calls → compaction likely soon. Save key memories via oh_memos_save.`);
}

process.exit(0);
