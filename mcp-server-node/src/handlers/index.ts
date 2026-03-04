/**
 * Tool Handler Dispatcher
 */

import { handleMemosSave, handleMemosList, handleMemosGet, handleMemosGetStats } from "./memory.js";
import { handleMemosSearch, handleMemosSearchContext, handleMemosSuggest, handleMemosContextResume } from "./search.js";
import { handleMemosTracePath, handleMemosGetGraph, handleMemosExportSchema, handleMemosImpact } from "./graph.js";
import { handleMemosCalendar } from "./calendar.js";
import {
  handleMemosListCubes,
  handleMemosRegisterCube,
  handleMemosCreateUser,
  handleMemosValidateCubes,
  handleMemosDelete,
} from "./admin.js";
import type { TextContent } from "../types.js";
import { MEMOS_URL } from "../config.js";
import { errorResponse } from "./utils.js";

export async function dispatchTool(
  name: string,
  arguments_: Record<string, unknown>
): Promise<TextContent[]> {
  switch (name) {
    // Memory tools
    case "memos_save":
      return handleMemosSave(arguments_);
    case "memos_list_v2":
      return handleMemosList(arguments_);
    case "memos_get":
      return handleMemosGet(arguments_);
    case "memos_get_stats":
      return handleMemosGetStats(arguments_);

    // Search tools
    case "memos_search":
      return handleMemosSearch(arguments_);
    case "memos_search_context":
      return handleMemosSearchContext(arguments_);
    case "memos_suggest":
      return handleMemosSuggest(arguments_);
    case "memos_context_resume":
      return handleMemosContextResume(arguments_);

    // Graph tools
    case "memos_trace_path":
      return handleMemosTracePath(arguments_);
    case "memos_get_graph":
      return handleMemosGetGraph(arguments_);
    case "memos_export_schema":
      return handleMemosExportSchema(arguments_);
    case "memos_impact":
      return handleMemosImpact(arguments_);

    // Calendar
    case "memos_calendar":
      return handleMemosCalendar(arguments_);

    // Admin tools
    case "memos_list_cubes":
      return handleMemosListCubes(arguments_);
    case "memos_register_cube":
      return handleMemosRegisterCube(arguments_);
    case "memos_create_user":
      return handleMemosCreateUser(arguments_);
    case "memos_validate_cubes":
      return handleMemosValidateCubes(arguments_);
    case "memos_delete":
      return handleMemosDelete(arguments_);

    default:
      return errorResponse(`Unknown tool: ${name}`);
  }
}

export async function handleApiUnreachable(): Promise<TextContent[]> {
  return [{
    type: "text",
    text: [
      `❌ [API_UNREACHABLE] Cannot connect to MemOS API at ${MEMOS_URL}`,
      "",
      "💡 Suggestions:",
      "- Check if MemOS API is running: `curl http://localhost:18000/health`",
      "- Start with: `scripts/local/start.bat`",
      "- Check port availability",
    ].join("\n"),
  }];
}
