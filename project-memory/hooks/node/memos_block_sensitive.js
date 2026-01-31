#!/usr/bin/env node
/**
 * MemOS Hook: PreToolUse - Block Sensitive Files (Cross-platform Node.js)
 * Warns when editing sensitive files like .env, credentials, etc.
 */

let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const filePath = data.tool_input?.file_path || '';

    // Sensitive patterns
    const sensitivePatterns = [
      '.env',
      'credentials',
      'secrets',
      'password',
      '.pem',
      '.key',
      'id_rsa',
      'private',
      'token'
    ];

    // Check if file matches sensitive pattern
    const isSensitive = sensitivePatterns.some(pattern =>
      filePath.toLowerCase().includes(pattern)
    );

    if (isSensitive) {
      console.log(JSON.stringify({
        continue: true,
        suppressOutput: false,
        message: `⚠️ Warning: Editing sensitive file: ${filePath}`
      }));
    } else {
      console.log(JSON.stringify({
        continue: true,
        suppressOutput: true
      }));
    }
  } catch (e) {
    console.log(JSON.stringify({
      continue: true,
      suppressOutput: true
    }));
  }
});
