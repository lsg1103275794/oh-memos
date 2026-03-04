/**
 * Handler Utilities
 *
 * Shared error formatting and cube ID resolution.
 */

import { detectCubeFromPath } from "../keyword-enhancer.js";
import { getDefaultCubeId } from "../cube-manager.js";
import type { TextContent } from "../types.js";

// ============================================================================
// Error Codes
// ============================================================================

export const ERR_API_UNREACHABLE = "API_UNREACHABLE";
export const ERR_API_ERROR = "API_ERROR";
export const ERR_CUBE_NOT_FOUND = "CUBE_NOT_FOUND";
export const ERR_CUBE_REGISTRATION = "CUBE_REGISTRATION_FAILED";
export const ERR_PARAM_MISSING = "PARAM_MISSING";
export const ERR_PARAM_INVALID = "PARAM_INVALID";
export const ERR_NEO4J_CONFIG = "NEO4J_CONFIG_MISSING";
export const ERR_OPERATION_FAILED = "OPERATION_FAILED";
export const ERR_DELETE_DISABLED = "DELETE_DISABLED";
export const ERR_USER_ERROR = "USER_ERROR";

// ============================================================================
// Response Helpers
// ============================================================================

export function errorResponse(
  message: string,
  errorCode?: string,
  suggestions?: string[]
): TextContent[] {
  const parts: string[] = [];

  if (errorCode) {
    parts.push(`❌ [${errorCode}] ${message}`);
  } else {
    parts.push(`❌ ${message}`);
  }

  if (suggestions && suggestions.length > 0) {
    parts.push("");
    parts.push("💡 Suggestions:");
    for (const s of suggestions) {
      parts.push(`- ${s}`);
    }
  }

  return [{ type: "text", text: parts.join("\n") }];
}

export function successResponse(message: string): TextContent[] {
  return [{ type: "text", text: message }];
}

export function cubeRegistrationError(cubeId: string, detail: string | null): TextContent[] {
  return errorResponse(
    `Cube '${cubeId}' registration failed: ${detail ?? "unknown error"}`,
    ERR_CUBE_REGISTRATION,
    [
      `Check if MemOS API is running: \`curl http://localhost:18000/health\``,
      `Verify cube exists: \`memos_list_cubes(include_status=True)\``,
      `Try manual registration: \`memos_register_cube(cube_id="...")\``,
    ]
  );
}

export function apiErrorResponse(operation: string, statusOrMsg: string | number): TextContent[] {
  return errorResponse(
    `${operation} failed: ${statusOrMsg}`,
    ERR_API_ERROR,
    [
      "Check API health: `curl http://localhost:18000/health/detail`",
      "Check API logs for details",
    ]
  );
}

// ============================================================================
// Cube ID Resolution
// ============================================================================

export function getCubeIdFromArgs(arguments_: Record<string, unknown>): string {
  const argCubeId = arguments_.cube_id as string | undefined;
  const projectPath = arguments_.project_path as string | undefined;

  if (projectPath) {
    try {
      const derived = detectCubeFromPath(projectPath);
      if (derived) return derived;
    } catch {
      // ignore
    }
  }

  return argCubeId ?? getDefaultCubeId();
}
