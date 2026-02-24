#!/usr/bin/env node
/**
 * MemOS Hook: PostToolUse - Notify Milestone (Cross-platform Node.js)
 *
 * Suggests saving milestones when editing important files.
 * Reminds to pass project_path for correct cube routing.
 */

let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const filePath = data.tool_input?.file_path || '';

    const milestoneFiles = [
      'README.md', 'CHANGELOG.md', 'package.json', 'pyproject.toml',
      'config.json', 'Cargo.toml', 'go.mod', 'pom.xml'
    ];

    const isMilestone = milestoneFiles.some(mf => filePath.endsWith(mf));

    if (isMilestone) {
      console.log(JSON.stringify({
        continue: true,
        suppressOutput: false,
        message: 'Significant file changed → memos_save(..., memory_type="MILESTONE", project_path="<CWD>")'
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
