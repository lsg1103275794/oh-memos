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

/**
 * Analyze tool usage and generate save suggestions
 * @param {string} toolName - Name of the tool (Edit, Write, Bash, etc.)
 * @param {object} toolInput - Tool input parameters
 * @param {string} toolResult - Tool execution result
 * @returns {string|null} Suggestion message or null
 */
function analyzeToolUse(toolName, toolInput, toolResult) {
  const resultLower = (typeof toolResult === 'string' ? toolResult : '').toLowerCase();

  // === Handle Edit/Write operations ===
  if (toolName === 'Edit' || toolName === 'Write') {
    const filePath = (toolInput.file_path || '').toLowerCase();
    return analyzeFileEdit(filePath);
  }

  // === Handle Bash commands ===
  if (toolName === 'Bash') {
    const command = toolInput.command || '';
    return analyzeBashResult(command, resultLower);
  }

  return null;
}

/**
 * Analyze file edit operations
 * @param {string} filePath - Path of edited file (lowercase)
 * @returns {string|null} Suggestion or null
 */
function analyzeFileEdit(filePath) {
  // Config files → CONFIG
  const configPatterns = [
    '.env', 'config.json', 'config.yaml', 'config.yml', 'settings.json',
    '.eslintrc', '.prettierrc', 'tsconfig.json', 'webpack.config',
    'docker-compose', 'dockerfile', '.gitignore', 'nginx.conf'
  ];

  if (configPatterns.some(p => filePath.includes(p))) {
    return '⚙️ Config file modified → Consider: memos_save(..., memory_type="CONFIG")';
  }

  // Important project files → MILESTONE
  const milestoneFiles = [
    'readme.md', 'changelog.md', 'package.json', 'pyproject.toml',
    'cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
    'makefile', 'cmakelists.txt'
  ];

  if (milestoneFiles.some(mf => filePath.endsWith(mf))) {
    return '📌 Project file updated → Consider: memos_save(..., memory_type="MILESTONE")';
  }

  // Test files → might be BUGFIX or FEATURE
  if (filePath.includes('test') || filePath.includes('spec')) {
    return '🧪 Test file modified → If fixing a bug: memos_save(..., memory_type="BUGFIX")';
  }

  // Schema/Migration files → CONFIG or DECISION
  if (filePath.includes('migration') || filePath.includes('schema')) {
    return '🗃️ Schema change → Consider: memos_save(..., memory_type="CONFIG") or "DECISION"';
  }

  return null;
}

/**
 * Analyze Bash command results
 * @param {string} command - The executed command
 * @param {string} result - Command result (lowercase)
 * @returns {string|null} Suggestion or null
 */
function analyzeBashResult(command, result) {
  const cmdLower = command.toLowerCase();

  // === Detect command failures ===
  const failurePatterns = [
    'error:', 'failed', 'exception', 'traceback', 'fatal:',
    'command not found', 'permission denied', 'no such file',
    'cannot', 'unable to', 'refused', 'timeout'
  ];

  const hasFailure = failurePatterns.some(p => result.includes(p));

  if (hasFailure) {
    return '❌ Command failed → Consider: memos_search(query="ERROR_PATTERN <error>") for solutions';
  }

  // === Detect successful fix patterns ===
  // Git commit after fix
  if (cmdLower.includes('git commit') && (
    result.includes('fix') || result.includes('bug') || result.includes('resolve')
  )) {
    return '✅ Fix committed → Consider: memos_save(..., memory_type="BUGFIX")';
  }

  // Successful test run
  if ((cmdLower.includes('pytest') || cmdLower.includes('npm test') ||
       cmdLower.includes('cargo test') || cmdLower.includes('go test')) &&
      (result.includes('passed') || result.includes('ok') || result.includes('success'))) {
    return '✅ Tests passed → If this fixed something: memos_save(..., memory_type="BUGFIX")';
  }

  // Successful build
  if ((cmdLower.includes('npm run build') || cmdLower.includes('cargo build') ||
       cmdLower.includes('make') || cmdLower.includes('go build')) &&
      !hasFailure) {
    // Only suggest on significant builds, not routine ones
    if (result.includes('warning') || result.length > 500) {
      return '🔨 Build completed with notes → Consider saving important observations';
    }
  }

  // Package install
  if ((cmdLower.includes('pip install') || cmdLower.includes('npm install') ||
       cmdLower.includes('cargo add')) && !hasFailure) {
    return '📦 Dependencies changed → Consider: memos_save(..., memory_type="CONFIG")';
  }

  // Database migrations
  if ((cmdLower.includes('migrate') || cmdLower.includes('alembic') ||
       cmdLower.includes('prisma')) && !hasFailure) {
    return '🗃️ Migration executed → Consider: memos_save(..., memory_type="CONFIG")';
  }

  return null;
}
