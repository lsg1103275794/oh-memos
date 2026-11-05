#!/usr/bin/env node
/**
 * MemOS Hook: PreToolUse - Auto Memory Context Injection
 *
 * Intercepts Grep/Glob/Read/Edit/Write tool calls, extracts a keyword,
 * searches MemOS for related memories, and injects them as additionalContext.
 * This enables zero-explicit-oh_memos_search context awareness.
 *
 * Hook type: PreToolUse
 * Matcher: Grep|Glob|Read|Edit|Write
 *
 * Input (stdin JSON):
 *   { tool_name, tool_input, cwd }
 *
 * Env: MEMOS_URL (default http://localhost:18000), MEMOS_USER (default dev_user).
 *
 * Output (stdout JSON), only when memories are found:
 *   { hookSpecificOutput: { hookEventName: "PreToolUse", additionalContext: "..." } }
 * Nothing is printed when there is no match or on any error.
 */

const http = require('http');
const https = require('https');
const path = require('path');

const DEFAULT_API_URL = 'http://localhost:18000';
const DEFAULT_USER = 'dev_user';
const TOP_K = 3;
const TIMEOUT_MS = 4000;
const MAX_CONTEXT_CHARS = 800;
const MIN_KEYWORD_LENGTH = 3;

async function main(input) {
  const data = JSON.parse(input);
  const toolName = data.tool_name || '';
  const toolInput = data.tool_input || {};
  const cwd = data.cwd || '';

  const keyword = extractKeyword(toolName, toolInput);
  if (!keyword || keyword.length < MIN_KEYWORD_LENGTH || !cwd) return;

  const api = new URL(process.env.MEMOS_URL || DEFAULT_API_URL);
  const user = process.env.MEMOS_USER || DEFAULT_USER;
  const memories = await searchMemOS(api, user, keyword, deriveCubeId(cwd));
  const context = memories && memories.length ? formatContext(memories, keyword) : '';
  if (!context) return;

  // Only hookSpecificOutput.additionalContext reaches the model. Claude Code
  // does not read a top-level additionalContext field.
  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: data.hook_event_name || 'PreToolUse',
      additionalContext: context,
    },
  }));
}

if (require.main === module) {
  let input = '';
  process.stdin.on('data', chunk => input += chunk);
  // Fail open: any error means no injected context, never a blocked tool call.
  process.stdin.on('end', () => { main(input).catch(() => {}); });
}

/**
 * Extract a meaningful search keyword from tool_input based on tool type.
 */
function extractKeyword(toolName, toolInput) {
  switch (toolName) {
    case 'Grep':
      return cleanPattern(toolInput.pattern || '');

    case 'Glob': {
      const pattern = toolInput.pattern || '';
      return extractGlobKeyword(pattern);
    }

    case 'Read':
    case 'Edit':
    case 'Write': {
      const filePath = toolInput.file_path || '';
      return extractFilenameKeyword(filePath);
    }

    default:
      return '';
  }
}

/**
 * Clean a regex/grep pattern to extract a meaningful keyword.
 * Strips regex metacharacters and returns the core text.
 */
function cleanPattern(pattern) {
  if (!pattern) return '';
  // Remove common regex metacharacters and anchors
  let cleaned = pattern
    .replace(/[\^\$\.\*\+\?\(\)\[\]\{\}\|\\]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  // Take the longest word as the keyword
  const words = cleaned.split(' ').filter(w => w.length >= MIN_KEYWORD_LENGTH);
  if (words.length === 0) return '';
  // Return all meaningful words joined, but cap at a reasonable length
  return words.join(' ').substring(0, 60);
}

/**
 * Extract a meaningful keyword from a glob pattern.
 * Skips pure extension patterns like "*.js", "**\/*.tsx".
 */
function extractGlobKeyword(pattern) {
  if (!pattern) return '';
  // Remove glob directory prefixes
  const basename = pattern.replace(/.*\//, '');
  // Skip pure extension globs: *.ext, *.{ext1,ext2}
  if (/^\*\.[\w{},]+$/.test(basename)) return '';
  // Extract meaningful part: "WebSocket*" -> "WebSocket", "oh_memos_*.js" -> "memos"
  const meaningful = basename
    .replace(/\*+/g, ' ')
    .replace(/\.\w+$/, '')  // strip extension
    .replace(/[_\-]+/g, ' ')
    .trim();
  const words = meaningful.split(' ').filter(w => w.length >= MIN_KEYWORD_LENGTH);
  return words.join(' ').substring(0, 60);
}

/**
 * Extract a keyword from a file path.
 * Uses the filename without extension, replacing separators with spaces.
 */
function extractFilenameKeyword(filePath) {
  if (!filePath) return '';
  const basename = path.basename(filePath);
  // Remove extension
  const name = basename.replace(/\.\w+$/, '');
  // Replace separators with spaces
  const keyword = name.replace(/[-_]+/g, ' ').trim();
  if (keyword.length < MIN_KEYWORD_LENGTH) return '';
  return keyword.substring(0, 60);
}

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

/**
 * Search MemOS API for memories matching the keyword.
 * Returns a promise that resolves to an array of memory objects, or null on error.
 */
function searchMemOS(api, user, keyword, cubeId) {
  return new Promise((resolve) => {
    const payload = JSON.stringify({
      user_id: user,
      query: keyword,
      install_cube_ids: [cubeId],
      top_k: TOP_K
    });

    const client = api.protocol === 'https:' ? https : http;
    const options = {
      hostname: api.hostname,
      port: api.port || (api.protocol === 'https:' ? 443 : 80),
      path: `${api.pathname.replace(/\/$/, '')}/search`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      },
      timeout: TIMEOUT_MS
    };

    const req = client.request(options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        try {
          const result = JSON.parse(body);
          if (result.message !== 'Search completed successfully') {
            return resolve(null);
          }
          const memories = extractMemories(result.data || {});
          resolve(memories);
        } catch {
          resolve(null);
        }
      });
    });

    req.on('error', () => resolve(null));
    req.on('timeout', () => {
      req.destroy();
      resolve(null);
    });

    req.write(payload);
    req.end();
  });
}

/**
 * Extract flat list of memories from MemOS search response data.
 * Handles both tree_text mode (nodes) and flat list mode.
 */
function extractMemories(data) {
  const memories = [];
  const textMems = data.text_mem || [];

  for (const cubeData of textMems) {
    const memoriesData = cubeData.memories;
    if (!memoriesData) continue;

    // tree_text mode: { nodes: [...] }
    if (memoriesData.nodes && Array.isArray(memoriesData.nodes)) {
      memories.push(...memoriesData.nodes);
    }
    // flat list mode: [...]
    else if (Array.isArray(memoriesData)) {
      memories.push(...memoriesData);
    }
  }

  return memories;
}

/**
 * Format memories into a concise additionalContext string.
 * Caps total length at MAX_CONTEXT_CHARS.
 */
function formatContext(memories, keyword) {
  const lines = [`[MemOS] Related memories for "${keyword}":`];
  let totalLen = lines[0].length;

  for (let i = 0; i < memories.length && i < TOP_K; i++) {
    const mem = memories[i];
    const key = (mem.metadata && mem.metadata.key) || mem.key || '';
    const content = mem.memory || mem.content || '';
    // Build a concise one-liner: key + truncated content
    let summary = key ? `${key}: ` : '';
    const remaining = MAX_CONTEXT_CHARS - totalLen - summary.length - 10; // 10 for prefix/newline
    if (remaining <= 20) break;
    const contentPreview = content.substring(0, Math.min(remaining, 150)).split('\n')[0];
    summary += contentPreview;
    const line = `  ${i + 1}. ${summary}`;
    if (totalLen + line.length + 1 > MAX_CONTEXT_CHARS) break;
    lines.push(line);
    totalLen += line.length + 1;
  }

  // Only return if we have at least one memory line
  if (lines.length <= 1) return '';
  return lines.join('\n');
}

module.exports = { deriveCubeId, extractKeyword, formatContext };
