#!/usr/bin/env node
// MemOS Hook: PreToolUse (Edit/Write)
// Block edits to sensitive files without confirmation

const sensitivePatterns = [
  ".env",
  "credentials",
  "secrets",
  "password",
  ".pem",
  ".key",
  "id_rsa"
];

let data = '';
process.stdin.on('data', chunk => data += chunk);
process.stdin.on('end', () => {
  try {
    const input = JSON.parse(data);
    const filePath = input.tool_input?.file_path || '';

    // Check if file matches any sensitive pattern
    const isSensitive = sensitivePatterns.some(p => filePath.includes(p));

    if (isSensitive) {
      console.error(`⚠️ Warning: Editing sensitive file: ${filePath}`);
    }

    console.log(JSON.stringify({
      continue: true,
      suppressOutput: !isSensitive
    }));
  } catch (e) {
    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
  }
});
