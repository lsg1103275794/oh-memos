#!/usr/bin/env node
// MemOS Hook: UserPromptSubmit
// Triggered when user submits a prompt

let data = '';
process.stdin.on('data', chunk => data += chunk);
process.stdin.on('end', () => {
  // Just return success - let MCP handle the actual memory operations
  console.log(JSON.stringify({
    continue: true,
    suppressOutput: false
  }));
});
