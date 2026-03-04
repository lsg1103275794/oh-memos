/**
 * Admin Handlers
 *
 * memos_list_cubes, memos_register_cube, memos_create_user,
 * memos_validate_cubes, memos_delete
 */

import * as fs from "fs";
import * as path from "path";

import {
  MEMOS_URL,
  MEMOS_USER,
  MEMOS_DEFAULT_CUBE,
  MEMOS_CUBES_DIR,
  MEMOS_ENABLE_DELETE,
  MEMOS_TIMEOUT_TOOL,
  registeredCubes,
} from "../config.js";
import { fetchWithTimeout } from "../api-client.js";
import {
  ensureCubeRegistered,
  getCubePath,
  getCubesBaseDir,
  getLocalCubesBaseDir,
  listAvailableCubes,
  validateAndFixCubeConfig,
  verifyCubeLoaded,
} from "../cube-manager.js";
import type { TextContent } from "../types.js";
import {
  ERR_CUBE_NOT_FOUND,
  ERR_DELETE_DISABLED,
  ERR_PARAM_MISSING,
  apiErrorResponse,
  cubeRegistrationError,
  errorResponse,
  getCubeIdFromArgs,
} from "./utils.js";

// ============================================================================
// memos_list_cubes
// ============================================================================

export async function handleMemosListCubes(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const includeStatus = arguments_.include_status === true;
  const available = listAvailableCubes();

  if (available.length === 0) {
    const cubesDir = MEMOS_CUBES_DIR.endsWith(MEMOS_DEFAULT_CUBE)
      ? path.dirname(MEMOS_CUBES_DIR)
      : MEMOS_CUBES_DIR;
    return [{ type: "text", text: [
      "## No cubes found",
      "",
      `Cubes directory: \`${cubesDir}\``,
      "",
      `To create a new cube, use the MemOS web interface at ${MEMOS_URL}/docs`,
      "or create a cube directory with a config.json file.",
    ].join("\n") }];
  }

  const result: string[] = ["## Available Memory Cubes\n"];
  result.push(`Cubes directory: \`${MEMOS_CUBES_DIR}\`\n`);

  for (const cube of available) {
    if (includeStatus) {
      const isLoaded = await verifyCubeLoaded(cube.id);
      const status = isLoaded ? "loaded" : "not loaded";
      result.push(`- **${cube.id}**: \`${cube.path}\` (${status})`);
    } else {
      result.push(`- **${cube.id}**: \`${cube.path}\``);
    }
  }

  result.push(`\n**Default cube**: \`${MEMOS_DEFAULT_CUBE}\``);
  result.push("\n*Use `memos_list_cubes(include_status=True)` to check registration status.*");

  return [{ type: "text", text: result.join("\n") }];
}

// ============================================================================
// memos_register_cube
// ============================================================================

export async function handleMemosRegisterCube(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const cubeId = String(arguments_.cube_id ?? "");
  let cubePath = arguments_.cube_path ? String(arguments_.cube_path) : undefined;

  if (!cubeId) {
    return errorResponse(
      "cube_id parameter is required",
      ERR_PARAM_MISSING,
      [
        "Use memos_list_cubes() to find available cubes",
        '`memos_register_cube(cube_id="dev_cube")`',
      ]
    );
  }

  if (!cubePath) {
    // Try to find cube path (returns Windows/original path for API)
    const localPath = getCubePath(cubeId);
    if (!localPath) {
      const available = listAvailableCubes();
      const hint = available.length > 0
        ? `\n\n**Available cubes:**\n${available.map((c) => `- \`${c.id}\``).join("\n")}`
        : "";
      return [{ type: "text", text: `❌ Cube \`${cubeId}\` not found in cubes directory.\n\nCubes directory: \`${getCubesBaseDir()}\`${hint}` }];
    }
    // Convert back to Windows path if needed
    const cubesDir = MEMOS_CUBES_DIR;
    const isWindowsPath = /^[A-Za-z]:/.test(cubesDir);
    if (isWindowsPath) {
      const match = localPath.match(/^\/mnt\/([a-z])\/(.*)/);
      if (match) {
        cubePath = `${match[1].toUpperCase()}:\\${match[2].replace(/\//g, "\\")}`;
      } else {
        cubePath = localPath;
      }
    } else {
      cubePath = localPath;
    }
  }

  try {
    const response = await fetchWithTimeout(`${MEMOS_URL}/mem_cubes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: MEMOS_USER,
        mem_cube_name_or_path: cubePath,
        mem_cube_id: cubeId,
      }),
      timeoutMs: MEMOS_TIMEOUT_TOOL,
    });

    if (response.ok) {
      const data = await response.json() as Record<string, unknown>;
      if (data.code === 200) {
        registeredCubes.add(cubeId);
        return [{ type: "text", text: [
          "✅ **Cube registered successfully!**",
          "",
          `- Cube ID: \`${cubeId}\``,
          `- Path: \`${cubePath}\``,
          "",
          "You can now use this cube with other memos_* tools.",
        ].join("\n") }];
      } else {
        const errorMsg = String(data.message ?? "Unknown error");
        let hint = "";
        if (errorMsg.toLowerCase().includes("reranker")) {
          hint = "Edit the cube's config.json and change `reranker.backend` to `http_bge` or `noop`.";
        } else if (errorMsg.toLowerCase().includes("user")) {
          hint = "Use `memos_create_user` tool to create the user first.";
        }
        return errorResponse(
          `Registration failed: ${errorMsg}`,
          errorMsg.toLowerCase().includes("not found") ? ERR_CUBE_NOT_FOUND : undefined,
          hint ? [hint] : []
        );
      }
    } else {
      return apiErrorResponse("Registration", `HTTP ${response.status}`);
    }
  } catch (err) {
    return apiErrorResponse("Registration", String(err));
  }
}

// ============================================================================
// memos_create_user
// ============================================================================

export async function handleMemosCreateUser(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const userId = String(arguments_.user_id ?? MEMOS_USER);
  const userName = String(arguments_.user_name ?? userId);

  try {
    const response = await fetchWithTimeout(`${MEMOS_URL}/users`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_name: userName,
        user_id: userId,
        role: "USER",
      }),
      timeoutMs: MEMOS_TIMEOUT_TOOL,
    });

    if (response.ok) {
      const data = await response.json() as Record<string, unknown>;
      if (data.code === 200) {
        return [{ type: "text", text: [
          "✅ **User created successfully!**",
          "",
          `- User ID: \`${userId}\``,
          `- User Name: \`${userName}\``,
          "",
          "You can now register cubes and store memories.",
        ].join("\n") }];
      } else {
        const errorMsg = String(data.message ?? "Unknown error");
        if (errorMsg.toLowerCase().includes("exist")) {
          return [{ type: "text", text: `ℹ️ User \`${userId}\` already exists. You can proceed with cube registration.` }];
        }
        return errorResponse(`User creation failed: ${errorMsg}`);
      }
    } else {
      return apiErrorResponse("User creation", `HTTP ${response.status}`);
    }
  } catch (err) {
    return apiErrorResponse("User creation", String(err));
  }
}

// ============================================================================
// memos_validate_cubes
// ============================================================================

export async function handleMemosValidateCubes(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  const fixIssues = arguments_.fix !== false; // Default true
  const localCubesDir = getLocalCubesBaseDir();

  if (!fs.existsSync(localCubesDir) || !fs.statSync(localCubesDir).isDirectory()) {
    return errorResponse(
      `Cubes directory not found: ${localCubesDir}`,
      ERR_CUBE_NOT_FOUND,
      [
        "Set MEMOS_CUBES_DIR in .env",
        "Verify the directory exists on disk",
      ]
    );
  }

  const results = ["## 🔍 Cube Configuration Validation\n"];
  let fixedCount = 0;
  let errorCount = 0;
  let okCount = 0;

  try {
    const items = fs.readdirSync(localCubesDir);
    for (const cubeName of items) {
      const cubePath = path.join(localCubesDir, cubeName);
      const configPath = path.join(cubePath, "config.json");

      if (!fs.existsSync(cubePath) || !fs.statSync(cubePath).isDirectory() || !fs.existsSync(configPath)) {
        continue;
      }

      try {
        const config = JSON.parse(fs.readFileSync(configPath, "utf-8")) as Record<string, unknown>;
        const issues: string[] = [];

        if (config.cube_id !== cubeName) {
          issues.push(`cube_id: \`${config.cube_id}\` → \`${cubeName}\``);
        }

        const textCfg = (config.text_mem as Record<string, unknown>)?.config as Record<string, unknown>;
        const graphCfg = (textCfg?.graph_db as Record<string, unknown>)?.config as Record<string, unknown>;
        const currentUserName = graphCfg?.user_name;
        if (currentUserName && currentUserName !== cubeName) {
          issues.push(`user_name: \`${currentUserName}\` → \`${cubeName}\``);
        }

        if (issues.length > 0) {
          if (fixIssues) {
            const [wasFixes, fixError] = validateAndFixCubeConfig(cubeName, configPath);
            if (wasFixes) {
              results.push(`- **${cubeName}**: ✅ Fixed - ${issues.join(", ")}`);
              fixedCount++;
            } else if (fixError) {
              results.push(`- **${cubeName}**: ❌ Error - ${fixError}`);
              errorCount++;
            }
          } else {
            results.push(`- **${cubeName}**: ⚠️ Issues - ${issues.join(", ")}`);
            errorCount++;
          }
        } else {
          results.push(`- **${cubeName}**: ✅ OK`);
          okCount++;
        }
      } catch (err) {
        results.push(`- **${cubeName}**: ❌ Error reading config - ${err}`);
        errorCount++;
      }
    }

    results.push("\n### Summary");
    results.push(`- ✅ OK: ${okCount}`);
    if (fixedCount > 0) results.push(`- 🔧 Fixed: ${fixedCount}`);
    if (errorCount > 0) results.push(`- ⚠️ Issues: ${errorCount}`);
    if (fixedCount > 0) results.push("\n**Note:** Fixed cubes need API restart to take effect.");

    return [{ type: "text", text: results.join("\n") }];
  } catch (err) {
    return apiErrorResponse("Validation", String(err));
  }
}

// ============================================================================
// memos_delete
// ============================================================================

export async function handleMemosDelete(arguments_: Record<string, unknown>): Promise<TextContent[]> {
  if (!MEMOS_ENABLE_DELETE) {
    return errorResponse(
      "Delete functionality is disabled",
      ERR_DELETE_DISABLED,
      [
        "Set MEMOS_ENABLE_DELETE=true in environment to enable",
        "This is a safety feature to prevent accidental data loss",
      ]
    );
  }

  const cubeId = getCubeIdFromArgs(arguments_);
  const memoryId = arguments_.memory_id ? String(arguments_.memory_id) : undefined;
  const memoryIds = Array.isArray(arguments_.memory_ids)
    ? (arguments_.memory_ids as string[]).map(String)
    : [];
  const deleteAll = arguments_.delete_all === true;

  const [regSuccess, regError] = await ensureCubeRegistered(cubeId);
  if (!regSuccess) return cubeRegistrationError(cubeId, regError);

  if (deleteAll) {
    const response = await fetchWithTimeout(
      `${MEMOS_URL}/memories/${cubeId}?user_id=${encodeURIComponent(MEMOS_USER)}`,
      { method: "DELETE" }
    );

    if (response.ok) {
      const data = await response.json() as Record<string, unknown>;
      if (data.code === 200) {
        return [{ type: "text", text: `⚠️ **ALL memories deleted** from cube: \`${cubeId}\`` }];
      } else {
        return errorResponse(`❌ **Delete all failed**: ${data.message ?? "Unknown error"}`);
      }
    } else {
      return errorResponse(`❌ **API error** during delete all: ${response.status}`);
    }
  }

  const idsToDelete: string[] = [];
  if (memoryId) idsToDelete.push(memoryId);
  idsToDelete.push(...memoryIds);

  if (idsToDelete.length === 0) {
    return errorResponse(
      "No target specified for deletion",
      ERR_PARAM_MISSING,
      [
        "Provide `memory_id` for single delete",
        "Provide `memory_ids` for batch delete",
        "Set `delete_all=true` to delete all memories (dangerous)",
      ]
    );
  }

  const results: string[] = [];
  for (const mid of idsToDelete) {
    let memContent = "*(Unknown content)*";
    try {
      const getResp = await fetchWithTimeout(
        `${MEMOS_URL}/memories/${cubeId}/${mid}?user_id=${encodeURIComponent(MEMOS_USER)}`,
        { method: "GET" }
      );
      if (getResp.ok) {
        const gData = await getResp.json() as Record<string, unknown>;
        if (gData.code === 200 && gData.data) {
          const memNode = gData.data as Record<string, unknown>;
          if (typeof memNode === "object") {
            memContent = String(memNode.memory ?? memContent);
          }
        }
      }
    } catch {
      memContent = "*(Fetch failed)*";
    }

    const deleteResp = await fetchWithTimeout(
      `${MEMOS_URL}/memories/${cubeId}/${mid}?user_id=${encodeURIComponent(MEMOS_USER)}`,
      { method: "DELETE" }
    );

    if (deleteResp.ok) {
      const data = await deleteResp.json() as Record<string, unknown>;
      if (data.code === 200) {
        results.push(`✅ Deleted: \`${mid}\`\n   > ${memContent.slice(0, 150)}...`);
      } else {
        results.push(`❌ Failed: \`${mid}\` (${data.message ?? "Unknown error"})`);
      }
    } else {
      results.push(`❌ API Error: \`${mid}\` (Status: ${deleteResp.status})`);
    }
  }

  return [{ type: "text", text: results.join("\n") }];
}
