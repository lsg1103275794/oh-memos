#!/usr/bin/env node
/**
 * MemOS Hook: PreToolUse - Smart Sensitive File Guard (Cross-platform Node.js)
 *
 * Enhanced detection for:
 * - Credentials and secrets (block with warning)
 * - Config files (allow with save reminder)
 * - Auto-generated files (warn about potential overwrite)
 */

let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const filePath = data.tool_input?.file_path || '';
    const toolName = data.tool_name || '';

    const result = analyzeFile(filePath, toolName);

    if (result.message) {
      console.log(JSON.stringify({
        continue: result.continue,
        suppressOutput: false,
        message: result.message
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
 * Analyze file path for sensitivity level
 * @param {string} filePath - File path being edited
 * @param {string} toolName - Tool being used (Edit/Write)
 * @returns {{continue: boolean, message: string|null}}
 */
function analyzeFile(filePath, toolName) {
  const fp = filePath.toLowerCase();

  // === CRITICAL: Should never edit ===
  const criticalPatterns = [
    { pattern: 'id_rsa', desc: 'SSH private key' },
    { pattern: 'id_ed25519', desc: 'SSH private key' },
    { pattern: '.pem', desc: 'Certificate/Key file' },
    { pattern: '.p12', desc: 'Certificate file' },
    { pattern: '.pfx', desc: 'Certificate file' },
    { pattern: 'aws_credentials', desc: 'AWS credentials' },
    { pattern: 'gcloud/credentials', desc: 'GCP credentials' },
    { pattern: '.npmrc', desc: 'NPM auth token' },
    { pattern: '.pypirc', desc: 'PyPI auth token' },
    { pattern: 'keystore', desc: 'Keystore file' },
    { pattern: 'vault.json', desc: 'Secret vault' },
    { pattern: 'serviceaccount', desc: 'Service account key' }
  ];

  for (const { pattern, desc } of criticalPatterns) {
    if (fp.includes(pattern)) {
      return {
        continue: true, // Still allow but with strong warning
        message: `🚨 CRITICAL: Editing ${desc} file!\n   File: ${filePath}\n   → NEVER commit this file to git!`
      };
    }
  }

  // === HIGH: Secrets and credentials ===
  const highPatterns = [
    { pattern: '.env', desc: 'Environment variables' },
    { pattern: 'credentials', desc: 'Credentials file' },
    { pattern: 'secrets', desc: 'Secrets file' },
    { pattern: 'password', desc: 'Password file' },
    { pattern: 'api_key', desc: 'API key file' },
    { pattern: 'auth.json', desc: 'Auth config' },
    { pattern: 'private', desc: 'Private file' },
    { pattern: '.htpasswd', desc: 'HTTP auth file' }
  ];

  for (const { pattern, desc } of highPatterns) {
    if (fp.includes(pattern)) {
      return {
        continue: true,
        message: `⚠️ Warning: Editing ${desc}\n   File: ${filePath}\n   → Consider: memos_save(..., memory_type="CONFIG") after changes`
      };
    }
  }

  // === MEDIUM: Config files (remind to save) ===
  const configPatterns = [
    'config.json', 'config.yaml', 'config.yml', 'settings.json',
    'docker-compose', 'dockerfile', 'nginx.conf', 'apache.conf',
    '.eslintrc', '.prettierrc', 'tsconfig.json', 'webpack.config',
    'vite.config', 'rollup.config', 'babel.config'
  ];

  if (configPatterns.some(p => fp.includes(p))) {
    // Don't show for .claude/settings.json (our own config)
    if (!fp.includes('.claude/settings.json')) {
      return {
        continue: true,
        message: `⚙️ Config file edit → Remember to save important changes with memos_save(..., memory_type="CONFIG")`
      };
    }
  }

  // === LOW: Auto-generated files (warn about overwrite) ===
  const generatedPatterns = [
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    'poetry.lock', 'cargo.lock', 'composer.lock',
    '.min.js', '.min.css', '.bundle.', '.chunk.',
    'dist/', 'build/', 'node_modules/'
  ];

  if (generatedPatterns.some(p => fp.includes(p))) {
    return {
      continue: true,
      message: `📦 Note: This appears to be an auto-generated file. Manual edits may be overwritten.`
    };
  }

  return { continue: true, message: null };
}
