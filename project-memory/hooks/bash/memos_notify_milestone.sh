#!/usr/bin/env node
// MemOS Hook: PostToolUse (Write/Edit)
// Detect potential milestones based on file changes

const milestoneFiles = [
  "README.md",
  "CHANGELOG.md",
  "package.json",
  "pyproject.toml",
  "config.json"
];

let data = '';
process.stdin.on('data', chunk => data += chunk);
process.stdin.on('end', () => {
  try {
    const input = JSON.parse(data);
    const filePath = input.tool_input?.file_path || '';

    // Check if edited file is a milestone indicator
    const isMilestone = milestoneFiles.some(mf => filePath.endsWith(mf));

    console.log(JSON.stringify({
      continue: true,
      suppressOutput: !isMilestone
    }));
  } catch (e) {
    console.log(JSON.stringify({ continue: true, suppressOutput: true }));
  }
});
