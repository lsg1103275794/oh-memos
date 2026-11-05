/**
 * MemOS MCP Server Configuration Module (TypeScript)
 *
 * Configuration priority: CLI args > environment variables > defaults
 */

import { config as loadDotenv } from "dotenv";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { existsSync } from "fs";
import { parseArgs } from "util";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Load .env with priority:
//   MEMOS_ENV_FILE / --memos-env-file > cwd > package root > dotenv search
//
// The positional fallbacks only work when the server happens to sit next to the
// deployment's .env. Under `npx oh-memos-mcp` the package lives in the npm cache,
// so `pkgEnv` resolves inside _npx/... and every lookup misses: the cube builder
// then fails on the first required variable (MOS_CHAT_MODEL) and registration is
// dead for reasons the client cannot see. MEMOS_ENV_FILE makes the location
// explicit and is the only reliable option for npx-based installs.
const cliEnvFile = (() => {
  const argv = process.argv.slice(2);
  const i = argv.indexOf("--memos-env-file");
  if (i !== -1 && argv[i + 1]) return argv[i + 1];
  const inline = argv.find((a) => a.startsWith("--memos-env-file="));
  return inline ? inline.slice("--memos-env-file=".length) : undefined;
})();

const explicitEnv = (cliEnvFile ?? process.env.MEMOS_ENV_FILE)?.trim();
const cwdEnv = resolve(process.cwd(), ".env");
const pkgRoot = resolve(__dirname, "..", "..");
const pkgEnv = resolve(pkgRoot, ".env");

if (explicitEnv) {
  const explicitPath = resolve(explicitEnv);
  if (existsSync(explicitPath)) {
    loadDotenv({ path: explicitPath, override: true });
  } else {
    // Explicit intent that cannot be honoured: say so on stderr rather than
    // silently falling back and failing later on a missing variable. stdout is
    // the MCP protocol channel and must not be written to.
    process.stderr.write(
      `[oh-memos-mcp] MEMOS_ENV_FILE points at a missing file: ${explicitPath}\n`
    );
  }
} else if (existsSync(cwdEnv)) {
    // Auto-discovered files provide defaults; explicit process env wins.
    loadDotenv({ path: cwdEnv, override: false });
} else if (existsSync(pkgEnv)) {
    // Package fallback is also advisory, never an override of launcher env.
    loadDotenv({ path: pkgEnv, override: false });
} else {
  loadDotenv(); // fallback: search from cwd upward
}

// ============================================================================
// CLI Argument Parsing
// ============================================================================

function parseCliArgs(): Record<string, string | undefined> {
  try {
    const { values } = parseArgs({
      args: process.argv.slice(2),
      options: {
        "memos-url": { type: "string" },
        "memos-user": { type: "string" },
        "memos-default-cube": { type: "string" },
        "memos-cubes-dir": { type: "string" },
        "memos-enable-delete": { type: "string" },
        "memos-timeout-tool": { type: "string" },
        "memos-timeout-startup": { type: "string" },
        "memos-timeout-health": { type: "string" },
        "memos-api-wait-max": { type: "string" },
        // Consumed before this point (see the dotenv block above); declared here
        // so it shows up as a first-class flag rather than an unknown token.
        "memos-env-file": { type: "string" },
      },
      strict: false,
    });
    return values as Record<string, string | undefined>;
  } catch {
    return {};
  }
}

const _args = parseCliArgs();

// ============================================================================
// Logging
// ============================================================================

const _logLevel = process.env.MEMOS_LOG_LEVEL?.toUpperCase() ?? "WARNING";

type LogLevel = "DEBUG" | "INFO" | "WARNING" | "ERROR";

const LOG_LEVELS: Record<LogLevel, number> = {
  DEBUG: 0,
  INFO: 1,
  WARNING: 2,
  ERROR: 3,
};

const _currentLevel = LOG_LEVELS[_logLevel as LogLevel] ?? LOG_LEVELS.WARNING;

export const logger = {
  debug: (msg: string) => {
    if (_currentLevel <= LOG_LEVELS.DEBUG) {
      process.stderr.write(`[DEBUG] ${msg}\n`);
    }
  },
  info: (msg: string) => {
    if (_currentLevel <= LOG_LEVELS.INFO) {
      process.stderr.write(`[INFO] ${msg}\n`);
    }
  },
  warning: (msg: string) => {
    if (_currentLevel <= LOG_LEVELS.WARNING) {
      process.stderr.write(`[WARN] ${msg}\n`);
    }
  },
  error: (msg: string) => {
    if (_currentLevel <= LOG_LEVELS.ERROR) {
      process.stderr.write(`[ERROR] ${msg}\n`);
    }
  },
  exception: (msg: string, err?: unknown) => {
    process.stderr.write(`[ERROR] ${msg}: ${err}\n`);
  },
};

// ============================================================================
// Configuration Helpers
// ============================================================================

function getEnv(key: string, ...alternatives: string[]): string | undefined {
  const val = process.env[key]?.trim();
  if (val) return val;
  for (const alt of alternatives) {
    const altVal = process.env[alt]?.trim();
    if (altVal) return altVal;
  }
  return undefined;
}

function requireEnv(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(`${name} is required (set ${name} in .env)`);
  }
  return value;
}

function parseFloat2(name: string, value: string | undefined, defaultVal: number): number {
  if (!value) return defaultVal;
  const n = parseFloat(value);
  if (isNaN(n)) throw new Error(`${name} must be a float, got: ${value}`);
  return n;
}

// ============================================================================
// Core Configuration (CLI args > env vars > defaults)
// ============================================================================

// -- Feature Flags --
export type MemosMode = "full" | "lite";
const _modeRaw = (process.env.MEMOS_MODE ?? "full").toLowerCase();
export const MEMOS_MODE: MemosMode = _modeRaw === "lite" ? "lite" : "full";
export const MEMOS_PROVIDER = (process.env.MEMOS_PROVIDER ?? (MEMOS_MODE === "lite" ? "local" : "api")).toLowerCase();

// -- API Connection --
export const MEMOS_URL: string = MEMOS_PROVIDER === "local"
  ? (getEnv("MEMOS_URL", "MEMOS_BASE_URL") ?? "")
  : requireEnv("MEMOS_URL", _args["memos-url"] ?? getEnv("MEMOS_URL", "MEMOS_BASE_URL"));

export const MEMOS_USER: string = requireEnv(
  "MEMOS_USER",
  _args["memos-user"] ?? getEnv("MEMOS_USER", "MOS_USER_ID")
);

const _defaultCubeFromEnv =
  _args["memos-default-cube"] != null || process.env["MEMOS_DEFAULT_CUBE"] != null;

export const MEMOS_DEFAULT_CUBE: string = requireEnv(
  "MEMOS_DEFAULT_CUBE",
  _args["memos-default-cube"] ?? getEnv("MEMOS_DEFAULT_CUBE")
);

export const MEMOS_CUBES_DIR: string = requireEnv(
  "MEMOS_CUBES_DIR",
  _args["memos-cubes-dir"] ?? getEnv("MEMOS_CUBES_DIR")
);

// -- Timeouts (seconds) --
export const MEMOS_TIMEOUT_TOOL: number = parseFloat2(
  "MEMOS_TIMEOUT_TOOL",
  _args["memos-timeout-tool"] ?? getEnv("MEMOS_TIMEOUT_TOOL"),
  300.0
);
export const MEMOS_TIMEOUT_STARTUP: number = parseFloat2(
  "MEMOS_TIMEOUT_STARTUP",
  _args["memos-timeout-startup"] ?? getEnv("MEMOS_TIMEOUT_STARTUP"),
  30.0
);
export const MEMOS_TIMEOUT_HEALTH: number = parseFloat2(
  "MEMOS_TIMEOUT_HEALTH",
  _args["memos-timeout-health"] ?? getEnv("MEMOS_TIMEOUT_HEALTH"),
  5.0
);
export const MEMOS_API_WAIT_MAX: number = parseFloat2(
  "MEMOS_API_WAIT_MAX",
  _args["memos-api-wait-max"] ?? getEnv("MEMOS_API_WAIT_MAX"),
  60.0
);

const _enableDeleteRaw =
  _args["memos-enable-delete"] ?? getEnv("MEMOS_ENABLE_DELETE") ?? "false";
export const MEMOS_ENABLE_DELETE: boolean = _enableDeleteRaw.toLowerCase() === "true";

// Server instructions plus memos_save/memos_search loaded up front (see
// server-instructions.ts). On by default; "false" restores deferred loading.
const _alwaysLoadRaw =
  _args["memos-always-load"] ?? getEnv("MEMOS_ALWAYS_LOAD") ?? "true";
export const MEMOS_ALWAYS_LOAD: boolean = _alwaysLoadRaw.toLowerCase() !== "false";

// -- Neo4j (for fallback direct graph queries) --
export const NEO4J_HTTP_URL: string | undefined = getEnv("NEO4J_HTTP_URL");
export const NEO4J_USER: string | undefined = getEnv("NEO4J_USER");
export const NEO4J_PASSWORD: string | undefined = getEnv("NEO4J_PASSWORD");

// ============================================================================
// Cube Registration Tracking
// ============================================================================

export const registeredCubes: Set<string> = new Set();
export const lastRegistrationAttempt: Map<string, number> = new Map();
export const REGISTRATION_RETRY_INTERVAL = 5.0; // seconds

// ============================================================================
// Memory Types
// ============================================================================

export const MEMORY_TYPES = new Set([
  "ERROR_PATTERN",
  "DECISION",
  "MILESTONE",
  "BUGFIX",
  "FEATURE",
  "CONFIG",
  "CODE_PATTERN",
  "GOTCHA",
  "PROGRESS",
  "SYNTHESIS",
]);

// ============================================================================
// Helper
// ============================================================================

export function isDefaultCubeFromEnv(): boolean {
  return _defaultCubeFromEnv;
}
