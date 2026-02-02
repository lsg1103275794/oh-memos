#!/usr/bin/env node
// MemOS Hook: PostToolUse (Bash)
// Log executed commands for potential memory saving

const fs = require('fs');
const path = require('path');

let data = '';
process.stdin.on('data', chunk => data += chunk);
process.stdin.on('end', () => {
  try {
    const input = JSON.parse(data);
    const command = input.tool_input?.command || '';
    const toolName = input.tool_name || '';

    // Only log Bash commands
    if (toolName === 'Bash' && command) {
      const logDir = process.env.HOME + '/.claude/hooks';
      const logFile = path.join(logDir, 'command_history.log');
      const timestamp = new Date().toISOString().replace('T', ' ').substr(0, 19);
      const logEntry = `[${timestamp}] ${command}\n`;

      try {
        fs.appendFileSync(logFile, logEntry);
      } catch (e) {
        // Silently ignore logging errors
      }
    }

    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
  } catch (e) {
    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
  }
});
