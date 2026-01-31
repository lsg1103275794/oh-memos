#!/usr/bin/env node
/**
 * MemOS Hook: PostToolUse - Log Commands (Cross-platform Node.js)
 * Logs executed bash commands for potential memory saving
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const command = data.tool_input?.command;
    const toolName = data.tool_name;

    // Only log Bash commands
    if (toolName === 'Bash' && command) {
      // Use cross-platform home directory
      const logFile = path.join(os.homedir(), '.claude', 'hooks', 'command_history.log');
      const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19);
      const logEntry = `[${timestamp}] ${command}\n`;

      try {
        // Ensure directory exists
        const logDir = path.dirname(logFile);
        if (!fs.existsSync(logDir)) {
          fs.mkdirSync(logDir, { recursive: true });
        }
        fs.appendFileSync(logFile, logEntry);
      } catch (e) {
        // Silently ignore logging errors
      }
    }
  } catch (e) {
    // Silently ignore parse errors
  }

  console.log(JSON.stringify({
    continue: true,
    suppressOutput: true
  }));
});
