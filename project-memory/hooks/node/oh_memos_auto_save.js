#!/usr/bin/env node
/**
 * MemOS Hook: PostToolUse - Smart Auto-Save Suggestions (Cross-platform Node.js)
 *
 * Analyzes tool results and suggests appropriate memory types:
 * - Edit/Write on config files â†?CONFIG
 * - Edit/Write on important files â†?MILESTONE
 * - Bash command failures â†?ERROR_PATTERN search
 * - Bash successful fixes â†?BUGFIX save
 * - Test commands â†?suggest saving results
 *
 * IMPORTANT: Always reminds to pass project_path for correct cube routing.
 */

let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const toolName = data.tool_name || '';
    const toolInput = data.tool_input || {};
    const toolResult = data.tool_result || '';

    const suggestion = analyzeToolUse(toolName, toolInput, toolResult);

    if (suggestion) {
      console.log(JSON.stringify({
        continue: true,
        suppressOutput: false,
        message: suggestion
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

function analyzeToolUse(toolName, toolInput, toolResult) {
  const resultLower = (typeof toolResult === 'string' ? toolResult : '').toLowerCase();

  if (toolName === 'Edit' || toolName === 'Write') {
    const filePath = (toolInput.file_path || '').toLowerCase();
    return analyzeFileEdit(filePath);
  }

  if (toolName === 'Bash') {
    const command = toolInput.command || '';
    return analyzeBashResult(command, resultLower);
  }

  return null;
}

function analyzeFileEdit(filePath) {
  const configPatterns = [
    '.env', 'config.json', 'config.yaml', 'config.yml', 'settings.json',
    '.eslintrc', '.prettierrc', 'tsconfig.json', 'webpack.config',
    'docker-compose', 'dockerfile', '.gitignore', 'nginx.conf'
  ];
  if (configPatterns.some(p => filePath.includes(p))) {
    return 'Config file modified â†?oh_memos_save(..., memory_type="CONFIG", project_path="<CWD>")';
  }

  const milestoneFiles = [
    'readme.md', 'changelog.md', 'package.json', 'pyproject.toml',
    'cargo.toml', 'go.mod', 'pom.xml', 'build.gradle'
  ];
  if (milestoneFiles.some(mf => filePath.endsWith(mf))) {
    return 'Project file updated â†?oh_memos_save(..., memory_type="MILESTONE", project_path="<CWD>")';
  }

  if (filePath.includes('test') || filePath.includes('spec')) {
    return 'Test file modified â†?If fixing bug: oh_memos_save(..., memory_type="BUGFIX", project_path="<CWD>")';
  }

  if (filePath.includes('migration') || filePath.includes('schema')) {
    return 'Schema change â†?oh_memos_save(..., memory_type="CONFIG", project_path="<CWD>")';
  }

  return null;
}

function analyzeBashResult(command, result) {
  const cmdLower = command.toLowerCase();

  // === Detect command failures ===
  const failurePatterns = [
    'error:', 'failed', 'exception', 'traceback', 'fatal:',
    'command not found', 'permission denied', 'no such file'
  ];
  const hasFailure = failurePatterns.some(p => result.includes(p));

  if (hasFailure) {
    return 'Command failed â†?oh_memos_search(query="ERROR_PATTERN <error>", project_path="<CWD>")';
  }

  // === Detect any successful git commit â†?suggest save ===
  if (cmdLower.includes('git commit') && !hasFailure) {
    // Extract commit message from output: "[branch hash] commit message"
    const commitMatch = result.match(/\[[\w/.-]+ [0-9a-f]+\]\s*(.+)/);
    const commitMsg = commitMatch ? commitMatch[1].trim() : '';
    const msgLower = commitMsg.toLowerCase();

    let memType = 'PROGRESS';
    if (/\b(fix|bug|resolve|repair|patch)\b/.test(msgLower)) {
      memType = 'BUGFIX';
    } else if (/\b(feat|feature|add|implement|new)\b/.test(msgLower)) {
      memType = 'FEATURE';
    } else if (/\b(refactor|clean|improve|optimize|perf)\b/.test(msgLower)) {
      memType = 'DECISION';
    } else if (/\b(release|milestone|version|v\d+\.\d+)\b/.test(msgLower)) {
      memType = 'MILESTONE';
    }

    const hint = commitMsg ? ` ("${commitMsg.slice(0, 60)}")` : '';
    return `Git commit${hint} â†?oh_memos_save(..., memory_type="${memType}", project_path="<CWD>")`;
  }

  // Successful test run
  if ((cmdLower.includes('pytest') || cmdLower.includes('npm test') ||
       cmdLower.includes('cargo test') || cmdLower.includes('go test')) &&
      (result.includes('passed') || result.includes('ok') || result.includes('success'))) {
    return 'Tests passed â†?If fixed something: oh_memos_save(..., memory_type="BUGFIX", project_path="<CWD>")';
  }

  // Package install
  if ((cmdLower.includes('pip install') || cmdLower.includes('npm install') ||
       cmdLower.includes('cargo add')) && !hasFailure) {
    return 'Dependencies changed â†?oh_memos_save(..., memory_type="CONFIG", project_path="<CWD>")';
  }

  // Database migrations
  if ((cmdLower.includes('migrate') || cmdLower.includes('alembic') ||
       cmdLower.includes('prisma')) && !hasFailure) {
    return 'Migration executed â†?oh_memos_save(..., memory_type="CONFIG", project_path="<CWD>")';
  }

  return null;
}
