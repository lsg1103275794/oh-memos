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

/**
 * Cube id for a project directory. Same rule as detectCubeFromPath in
 * mcp-server-node/src/keyword-enhancer.ts; hook-context.test.ts keeps the
 * copies in the hooks equal to it.
 */
function deriveCubeId(cwd) {
  const segments = String(cwd).replace(/\\/g, '/').replace(/\/$/, '').split('/');
  let folder = segments[segments.length - 1] || '';
  if (/^[A-Za-z]:$/.test(folder)) folder = segments[segments.length - 2] || 'default';
  if (!folder) return 'default_cube';
  let id = folder.toLowerCase().replace(/[-.\s]+/g, '_').replace(/[^a-z0-9_]/g, '');
  if (/^\d/.test(id)) id = '_' + id;
  if (!id.endsWith('_cube')) id += '_cube';
  return id || 'default_cube';
}

function main() {
  const cwd = process.cwd();
  const folderName = path.basename(cwd);
  const fullCubeId = deriveCubeId(cwd);
  console.error(`[MemOS] Project: ${folderName} â†?cube_id: "${fullCubeId}"`);
  console.error(`[MemOS] Use project_path="${cwd}" in oh_memos_save/oh_memos_search for correct cube routing.`);
  console.error('[MemOS] NEVER use mkdir or Write to create memory files. Use MCP memos tools only.');
  process.exit(0);
}

if (require.main === module) main();

module.exports = { deriveCubeId };
