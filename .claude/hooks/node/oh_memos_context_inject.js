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
 * Output (stdout JSON):
 *   { continue: true, suppressOutput: false, additionalContext: "..." }  -- if memories found
 *   { continue: true, suppressOutput: true }                             -- if no memories or error
 */

const http = require('http');
const path = require('path');

const oh_memos_API_HOST = 'localhost';
const oh_memos_API_PORT = 18000;
const oh_memos_USER = 'dev_user';
const TOP_K = 3;
const TIMEOUT_MS = 4000;
const MAX_CONTEXT_CHARS = 800;
const MIN_KEYWORD_LENGTH = 3;

let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', async () => {
  try {
    const data = JSON.parse(input);
    const toolName = data.tool_name || '';
    const toolInput = data.tool_input || {};
    const cwd = data.cwd || '';

    // Extract keyword based on tool type
    const keyword = extractKeyword(toolName, toolInput);
    if (!keyword || keyword.length < MIN_KEYWORD_LENGTH) {
      return suppress();
    }

    // Derive cube_id from cwd
    const cubeId = deriveCubeId(cwd);
    if (!cubeId) {
      return suppress();
    }

    // Search MemOS API
    const memories = await searchMemOS(keyword, cubeId);
    if (!memories || memories.length === 0) {
      return suppress();
    }

    // Format results as concise additionalContext
    const context = formatContext(memories, keyword);
    if (!context) {
      return suppress();
    }

    console.log(JSON.stringify({
      continue: true,
      suppressOutput: false,
      additionalContext: context
    }));
  } catch (e) {
    suppress();
  }
});

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
 * Derive cube_id from the current working directory.
 * Rule: basename(cwd) -> lowercase -> replace [-.\s]+ with _ -> append _cube
 */
function deriveCubeId(cwd) {
  if (!cwd) return '';
  const base = path.basename(cwd);
  if (!base) return '';
  return base.toLowerCase().replace(/[-.\s]+/g, '_') + '_cube';
}

/**
 * Search MemOS API for memories matching the keyword.
 * Returns a promise that resolves to an array of memory objects, or null on error.
 */
function searchMemOS(keyword, cubeId) {
  return new Promise((resolve) => {
    const payload = JSON.stringify({
      user_id: oh_memos_USER,
      query: keyword,
      install_cube_ids: [cubeId],
      top_k: TOP_K
    });

    const options = {
      hostname: oh_memos_API_HOST,
      port: oh_memos_API_PORT,
      path: '/search',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      },
      timeout: TIMEOUT_MS
    };

    const req = http.request(options, (res) => {
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

/**
 * Output suppressed (no context) and exit cleanly.
 */
function suppress() {
  console.log(JSON.stringify({ continue: true, suppressOutput: true }));
}
