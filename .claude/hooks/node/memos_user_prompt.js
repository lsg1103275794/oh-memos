#!/usr/bin/env node
/**
 * MemOS Hook: UserPromptSubmit (Cross-platform Node.js)
 * Triggered when user submits a prompt
 */

// Simply return success - this hook is a passthrough
console.log(JSON.stringify({
  continue: true,
  suppressOutput: true
}));
