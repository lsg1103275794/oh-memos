#!/usr/bin/env node
/**
 * MemOS Hook: SessionStart - Output CWD â†?cube_id mapping
 *
 * When a new session starts, output the derived cube_id for the current
 * project directory so the model knows which cube to use.
 *
 * Hook type: SessionStart
 * Matcher: *
 */

const path = require('path');

const cwd = process.cwd();
const folderName = path.basename(cwd);
const cubeId = folderName
  .toLowerCase()
  .replace(/[-.\s]+/g, '_')
  .replace(/[^a-z0-9_]/g, '')
  .replace(/^(\d)/, '_$1');
const fullCubeId = cubeId.endsWith('_cube') ? cubeId : cubeId + '_cube';

console.error(`[MemOS] Project: ${folderName} â†?cube_id: "${fullCubeId}"`);
console.error(`[MemOS] Use project_path="${cwd}" in oh_memos_save/oh_memos_search for correct cube routing.`);
console.error('[MemOS] NEVER use mkdir or Write to create memory files. Use MCP memos tools only.');
process.exit(0);
