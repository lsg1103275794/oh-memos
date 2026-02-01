#!/usr/bin/env node
/**
 * MemOS Hook: PostToolUse - Notify Milestone (Cross-platform Node.js)
 * Suggests saving milestones when editing important files
 */

let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const filePath = data.tool_input?.file_path || '';

    // Files that indicate milestone completion
    const milestoneFiles = [
      'README.md',
      'CHANGELOG.md',
      'package.json',
      'pyproject.toml',
      'config.json',
      'Cargo.toml',
      'go.mod',
      'pom.xml'
    ];

    // Check if edited file is a milestone indicator
    const isMilestone = milestoneFiles.some(mf => filePath.endsWith(mf));

    if (isMilestone) {
      console.log(JSON.stringify({
        continue: true,
        suppressOutput: false,
        message: '💡 Consider saving this as a MILESTONE if it\'s a significant change'
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
