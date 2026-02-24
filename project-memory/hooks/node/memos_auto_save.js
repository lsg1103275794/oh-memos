#!/usr/bin/env node
/**
 * MemOS Hook: PostToolUse - Smart Auto-Save Suggestions (Cross-platform Node.js)
 *
 * Analyzes tool results and suggests appropriate memory types:
 * - Edit/Write on config files → CONFIG
 * - Edit/Write on important files → MILESTONE
 * - Bash command failures → ERROR_PATTERN search
 * - Bash successful fixes → BUGFIX save
 * - Test commands → suggest saving results
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
    return 'Config file modified → memos_save(..., memory_type="CONFIG", project_path="<CWD>")';
  }

  const milestoneFiles = [
    'readme.md', 'changelog.md', 'package.json', 'pyproject.toml',
    'cargo.toml', 'go.mod', 'pom.xml', 'build.gradle'
  ];
  if (milestoneFiles.some(mf => filePath.endsWith(mf))) {
    return 'Project file updated → memos_save(..., memory_type="MILESTONE", project_path="<CWD>")';
  }

  if (filePath.includes('test') || filePath.includes('spec')) {
    return 'Test file modified → If fixing bug: memos_save(..., memory_type="BUGFIX", project_path="<CWD>")';
  }

  if (filePath.includes('migration') || filePath.includes('schema')) {
    return 'Schema change → memos_save(..., memory_type="CONFIG", project_path="<CWD>")';
  }

  return null;
}

function analyzeBashResult(command, result) {
  const cmdLower = command.toLowerCase();

  const failurePatterns = [
    'error:', 'failed', 'exception', 'traceback', 'fatal:',
    'command not found', 'permission denied', 'no such file'
  ];
  const hasFailure = failurePatterns.some(p => result.includes(p));

  if (hasFailure) {
    return 'Command failed → memos_search(query="ERROR_PATTERN <error>", project_path="<CWD>")';
  }

  if (cmdLower.includes('git commit') && (
    result.includes('fix') || result.includes('bug') || result.includes('resolve')
  )) {
    return 'Fix committed → memos_save(..., memory_type="BUGFIX", project_path="<CWD>")';
  }

  if ((cmdLower.includes('pytest') || cmdLower.includes('npm test') ||
       cmdLower.includes('cargo test') || cmdLower.includes('go test')) &&
      (result.includes('passed') || result.includes('ok') || result.includes('success'))) {
    return 'Tests passed → If fixed something: memos_save(..., memory_type="BUGFIX", project_path="<CWD>")';
  }

  if ((cmdLower.includes('pip install') || cmdLower.includes('npm install') ||
       cmdLower.includes('cargo add')) && !hasFailure) {
    return 'Dependencies changed → memos_save(..., memory_type="CONFIG", project_path="<CWD>")';
  }

  return null;
}
