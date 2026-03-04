/**
 * MemOS MCP Server Cube Management Module
 *
 * Handles cube discovery, config, and registration.
 */

import * as fs from "fs";
import * as path from "path";

import {
  MEMOS_URL,
  MEMOS_USER,
  MEMOS_DEFAULT_CUBE,
  MEMOS_CUBES_DIR,
  MEMOS_TIMEOUT_STARTUP,
  REGISTRATION_RETRY_INTERVAL,
  registeredCubes,
  lastRegistrationAttempt,
  logger,
  isDefaultCubeFromEnv,
} from "./config.js";
import { detectCubeFromPath } from "./keyword-enhancer.js";
import { fetchWithTimeout } from "./api-client.js";
import type { CubeInfo, CubeConfig } from "./types.js";

// ============================================================================
// Windows/WSL Path Conversion
// ============================================================================

/**
 * Convert Windows path to WSL/Linux path for local file access.
 * e.g. "G:\\test\\MemOS\\data" → "/mnt/g/test/MemOS/data"
 */
function toLocalPath(p: string): string {
  // Already a Unix path
  if (p.startsWith("/")) return p;
  // Windows absolute path: "G:\..." or "G:/..."
  const winMatch = p.match(/^([A-Za-z]):[/\\](.*)/);
  if (winMatch) {
    const drive = winMatch[1].toLowerCase();
    const rest = winMatch[2].replace(/\\/g, "/");
    return `/mnt/${drive}/${rest}`;
  }
  return p;
}

// ============================================================================
// Cube Discovery
// ============================================================================

export function getCubesBaseDir(): string {
  const cubesDir = MEMOS_CUBES_DIR;
  if (cubesDir.endsWith(MEMOS_DEFAULT_CUBE)) {
    return path.dirname(cubesDir);
  }
  return cubesDir;
}

export function getLocalCubesBaseDir(): string {
  return toLocalPath(getCubesBaseDir());
}

export function listAvailableCubes(): CubeInfo[] {
  const available: CubeInfo[] = [];
  const cubesDirLocal = getLocalCubesBaseDir();

  if (!fs.existsSync(cubesDirLocal) || !fs.statSync(cubesDirLocal).isDirectory()) {
    logger.warning(`Cubes directory does not exist: ${cubesDirLocal}`);
    return available;
  }

  try {
    const items = fs.readdirSync(cubesDirLocal);
    for (const item of items) {
      const itemPath = path.join(cubesDirLocal, item);
      const configPath = path.join(itemPath, "config.json");
      if (
        fs.existsSync(itemPath) &&
        fs.statSync(itemPath).isDirectory() &&
        fs.existsSync(configPath)
      ) {
        available.push({ id: item, path: itemPath });
      }
    }
  } catch (err) {
    logger.warning(`Error scanning cubes directory: ${err}`);
  }

  return available;
}

export function getCubePath(cubeId: string): string | null {
  const localBase = getLocalCubesBaseDir();

  let cubePath: string;
  if (cubeId === MEMOS_DEFAULT_CUBE) {
    const cubesDirLocal = toLocalPath(MEMOS_CUBES_DIR);
    if (cubesDirLocal.endsWith(MEMOS_DEFAULT_CUBE)) {
      cubePath = cubesDirLocal;
    } else {
      cubePath = path.join(cubesDirLocal, MEMOS_DEFAULT_CUBE);
    }
  } else {
    cubePath = path.join(localBase, cubeId);
  }

  const configPath = path.join(cubePath, "config.json");
  if (fs.existsSync(cubePath) && fs.statSync(cubePath).isDirectory() && fs.existsSync(configPath)) {
    return cubePath;
  }
  return null;
}

/**
 * Get the original (possibly Windows) path for the cube, for API registration.
 * The API runs on Windows, so it needs the Windows path.
 */
function getCubeApiPath(cubeId: string): string | null {
  const localPath = getCubePath(cubeId);
  if (!localPath) return null;

  // Convert back to Windows path if MEMOS_CUBES_DIR is a Windows path
  const cubesDir = MEMOS_CUBES_DIR;
  const isWindowsPath = /^[A-Za-z]:/.test(cubesDir);

  if (isWindowsPath) {
    // Local path is /mnt/g/... → G:\...
    const match = localPath.match(/^\/mnt\/([a-z])\/(.*)/);
    if (match) {
      const drive = match[1].toUpperCase();
      const rest = match[2].replace(/\//g, "\\");
      return `${drive}:\\${rest}`;
    }
  }

  return localPath;
}

// ============================================================================
// Cube Configuration
// ============================================================================

function cloneConfig(config: CubeConfig): CubeConfig {
  return JSON.parse(JSON.stringify(config)) as CubeConfig;
}

function updateConfigForCube(config: CubeConfig, cubeId: string): CubeConfig {
  config.user_id = MEMOS_USER;
  config.cube_id = cubeId;
  config.config_filename = "config.json";

  const textMem = config.text_mem;
  if (typeof textMem === "object" && textMem !== null) {
    const textCfg = (textMem as Record<string, unknown>).config;
    if (typeof textCfg === "object" && textCfg !== null) {
      const tc = textCfg as Record<string, unknown>;
      if ("cube_id" in tc) tc.cube_id = cubeId;

      const graphDb = tc.graph_db;
      if (typeof graphDb === "object" && graphDb !== null) {
        const graphCfg = (graphDb as Record<string, unknown>).config;
        if (typeof graphCfg === "object" && graphCfg !== null) {
          const gc = graphCfg as Record<string, unknown>;
          const useMultiDb = gc.use_multi_db;
          if (useMultiDb === false || "user_name" in gc) {
            gc.user_name = cubeId;
          }
          const vecCfg = typeof gc.vec_config === "object" && gc.vec_config !== null
            ? (gc.vec_config as Record<string, unknown>).config
            : null;
          if (vecCfg && typeof vecCfg === "object" && "collection_name" in vecCfg) {
            (vecCfg as Record<string, unknown>).collection_name = `${cubeId}_graph`;
          }
        }
      }

      const vectorDb = tc.vector_db;
      if (typeof vectorDb === "object" && vectorDb !== null) {
        const vectorCfg = (vectorDb as Record<string, unknown>).config;
        if (typeof vectorCfg === "object" && vectorCfg !== null && "collection_name" in vectorCfg) {
          (vectorCfg as Record<string, unknown>).collection_name = `${cubeId}_collection`;
        }
      }
    }
  }

  return config;
}

function buildCubeConfig(cubeId: string): CubeConfig {
  const templatePath = getCubePath(MEMOS_DEFAULT_CUBE);
  if (templatePath !== null) {
    const configPath = path.join(templatePath, "config.json");
    try {
      const config = JSON.parse(fs.readFileSync(configPath, "utf-8")) as CubeConfig;
      const cloned = cloneConfig(config);
      return updateConfigForCube(cloned, cubeId);
    } catch (err) {
      logger.warning(`Failed to read template cube config: ${err}`);
    }
  }
  // Minimal fallback config (will likely fail API registration without proper fields)
  return {
    user_id: MEMOS_USER,
    cube_id: cubeId,
    config_filename: "config.json",
    text_mem: {},
    act_mem: {},
    para_mem: {},
  };
}

export function validateAndFixCubeConfig(cubeId: string, configPath: string): [boolean, string | null] {
  try {
    const config = JSON.parse(fs.readFileSync(configPath, "utf-8")) as CubeConfig;
    let modified = false;

    if (config.cube_id !== cubeId) {
      config.cube_id = cubeId;
      modified = true;
    }

    const textMem = config.text_mem;
    if (typeof textMem === "object" && textMem !== null) {
      const textCfg = (textMem as Record<string, unknown>).config;
      if (typeof textCfg === "object" && textCfg !== null) {
        const tc = textCfg as Record<string, unknown>;
        if (tc.cube_id !== cubeId) {
          tc.cube_id = cubeId;
          modified = true;
        }

        const graphDb = tc.graph_db;
        if (typeof graphDb === "object" && graphDb !== null) {
          const graphCfg = (graphDb as Record<string, unknown>).config;
          if (typeof graphCfg === "object" && graphCfg !== null) {
            const gc = graphCfg as Record<string, unknown>;
            if (gc.user_name && gc.user_name !== cubeId) {
              gc.user_name = cubeId;
              modified = true;
            }
            const vecCfg = typeof gc.vec_config === "object" && gc.vec_config !== null
              ? (gc.vec_config as Record<string, unknown>).config
              : null;
            if (vecCfg && typeof vecCfg === "object" && "collection_name" in vecCfg) {
              const expected = `${cubeId}_graph`;
              if ((vecCfg as Record<string, unknown>).collection_name !== expected) {
                (vecCfg as Record<string, unknown>).collection_name = expected;
                modified = true;
              }
            }
          }
        }
      }
    }

    if (modified) {
      fs.writeFileSync(configPath, JSON.stringify(config, null, 2), "utf-8");
    }

    return [modified, null];
  } catch (err) {
    return [false, `Failed to validate cube config: ${err}`];
  }
}

export function ensureCubeDirectory(cubeId: string): [string | null, string | null] {
  const localBase = getLocalCubesBaseDir();
  try {
    fs.mkdirSync(localBase, { recursive: true });
    const cubeDir = path.join(localBase, cubeId);
    const configPath = path.join(cubeDir, "config.json");

    if (fs.existsSync(cubeDir) && fs.existsSync(configPath)) {
      validateAndFixCubeConfig(cubeId, configPath);
      return [cubeDir, null];
    }

    fs.mkdirSync(cubeDir, { recursive: true });
    const config = buildCubeConfig(cubeId);
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2), "utf-8");
    return [cubeDir, null];
  } catch (err) {
    return [null, `Failed to create cube '${cubeId}': ${err}`];
  }
}

// ============================================================================
// Cube Registration
// ============================================================================

export async function verifyCubeLoaded(cubeId: string): Promise<boolean> {
  try {
    const response = await fetchWithTimeout(
      `${MEMOS_URL}/memories?user_id=${encodeURIComponent(MEMOS_USER)}&mem_cube_id=${encodeURIComponent(cubeId)}`,
      { method: "GET", timeoutMs: 5 }
    );
    if (response.ok) {
      const data = await response.json() as Record<string, unknown>;
      return data.code === 200;
    }
  } catch {
    // ignore
  }
  return false;
}

export async function ensureCubeRegistered(
  cubeId: string,
  force = false
): Promise<[boolean, string | null]> {
  const now = Date.now() / 1000;

  if (!force && registeredCubes.has(cubeId)) return [true, null];

  if (!force) {
    const lastAttempt = lastRegistrationAttempt.get(cubeId) ?? 0;
    if (now - lastAttempt < REGISTRATION_RETRY_INTERVAL && registeredCubes.has(cubeId)) {
      return [true, null];
    }
  }

  lastRegistrationAttempt.set(cubeId, now);

  try {
    // Check if already loaded
    if (await verifyCubeLoaded(cubeId)) {
      registeredCubes.add(cubeId);
      logger.debug(`Cube '${cubeId}' already loaded`);
      return [true, null];
    }

    // Get or create cube path
    let cubePath = getCubeApiPath(cubeId);
    if (!cubePath) {
      // Try to auto-create
      logger.debug(`Cube '${cubeId}' not found, attempting auto-creation...`);

      const templatePath = getCubePath(MEMOS_DEFAULT_CUBE);
      if (!templatePath) {
        const available = listAvailableCubes();
        const availableIds = available.map((c) => c.id);
        if (availableIds.length > 0) {
          return [false, `Cube '${cubeId}' not found. Available cubes: ${availableIds.join(", ")}`];
        }
        return [false, `Cube '${cubeId}' not found and no cubes available.`];
      }

      const [newDir, createErr] = ensureCubeDirectory(cubeId);
      if (!newDir) {
        return [false, `Failed to auto-create cube '${cubeId}': ${createErr}`];
      }

      cubePath = getCubeApiPath(cubeId);
      if (!cubePath) {
        return [false, `Failed to get path for cube '${cubeId}' after creation`];
      }
    }

    // Register with API
    const response = await fetchWithTimeout(`${MEMOS_URL}/mem_cubes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: MEMOS_USER,
        mem_cube_name_or_path: cubePath,
        mem_cube_id: cubeId,
      }),
      timeoutMs: MEMOS_TIMEOUT_STARTUP,
    });

    if (response.ok) {
      const data = await response.json() as Record<string, unknown>;
      if (data.code === 200) {
        registeredCubes.add(cubeId);
        logger.debug(`Auto-registered cube: ${cubeId}`);
        return [true, null];
      }
      const msg = String(data.message ?? "Unknown error");
      if (msg.toLowerCase().includes("already")) {
        registeredCubes.add(cubeId);
        return [true, null];
      }
      const available = listAvailableCubes();
      const availableIds = available.map((c) => c.id);
      return [false, `Failed to register cube '${cubeId}': ${msg}. Available: ${availableIds.join(", ") || "none"}`];
    }
  } catch (err) {
    const msg = String(err);
    if (msg.includes("ECONNREFUSED") || msg.includes("fetch failed") || msg.includes("ECONNRESET")) {
      return [false, `Cannot connect to MemOS API at ${MEMOS_URL}. Is the server running?`];
    }
    return [false, `Failed to register cube '${cubeId}': ${err}`];
  }

  return [false, `Unknown error registering cube '${cubeId}'`];
}

// ============================================================================
// Default Cube ID
// ============================================================================

export function getDefaultCubeId(): string {
  if (isDefaultCubeFromEnv()) {
    if (getCubePath(MEMOS_DEFAULT_CUBE) !== null) {
      return MEMOS_DEFAULT_CUBE;
    }
  }
  try {
    return detectCubeFromPath(process.cwd());
  } catch {
    return MEMOS_DEFAULT_CUBE;
  }
}
