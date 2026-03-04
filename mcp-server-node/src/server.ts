/**
 * MemOS MCP Server — McpServer setup + background init
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { MEMOS_DEFAULT_CUBE, MEMOS_ENABLE_DELETE, logger } from "./config.js";
import { waitForApiReady } from "./api-client.js";
import { ensureCubeRegistered } from "./cube-manager.js";
import { toolSchemas } from "./tools-registry.js";
import { dispatchTool, handleApiUnreachable } from "./handlers/index.js";
import type { TextContent } from "./types.js";

// ============================================================================
// Register All Tools
// ============================================================================

function registerTools(server: McpServer): void {
  for (const [name, schema] of Object.entries(toolSchemas)) {
    // Skip delete tool if not enabled
    if (name === "memos_delete" && !MEMOS_ENABLE_DELETE) {
      logger.debug("Delete tool skipped (MEMOS_ENABLE_DELETE=false)");
      continue;
    }

    server.registerTool(
      name,
      {
        description: schema.description,
        inputSchema: schema.inputSchema,
      },
      async (args: Record<string, unknown>) => {
        try {
          const result = await dispatchTool(name, args);
          return {
            content: result.map((r: TextContent) => ({ type: "text" as const, text: r.text })),
          };
        } catch (err: unknown) {
          const errStr = String(err);
          if (errStr.includes("ECONNREFUSED") || errStr.includes("fetch failed")) {
            const unreachable = await handleApiUnreachable();
            return {
              content: unreachable.map((r) => ({ type: "text" as const, text: r.text })),
            };
          }
          logger.exception("Tool call failed", err);
          return {
            content: [
              {
                type: "text" as const,
                text: [
                  `❌ [UNEXPECTED_ERROR] ${errStr}`,
                  "",
                  "💡 Suggestions:",
                  "- Check MCP server logs for details",
                  "- Verify MemOS API is healthy: `curl http://localhost:18000/health/detail`",
                ].join("\n"),
              },
            ],
          };
        }
      }
    );
  }

  if (MEMOS_ENABLE_DELETE) {
    logger.debug("Delete tool enabled (MEMOS_ENABLE_DELETE=true)");
  }
}

// ============================================================================
// Background Init
// ============================================================================

async function backgroundInit(): Promise<void> {
  try {
    const apiReady = await waitForApiReady();

    if (apiReady) {
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          const [regSuccess, regError] = await ensureCubeRegistered(MEMOS_DEFAULT_CUBE, true);
          if (regSuccess) {
            logger.debug(`Default cube '${MEMOS_DEFAULT_CUBE}' ready`);
            return;
          }
          logger.warning(`Cube registration attempt ${attempt + 1} failed: ${regError}`);
          await sleep(2000);
        } catch (err) {
          logger.warning(`Registration attempt ${attempt + 1} error: ${err}`);
          await sleep(2000);
        }
      }
    } else {
      logger.warning("API not ready, will register cube on first tool call");
    }
  } catch (err) {
    logger.warning(`Background init failed: ${err}`);
  }
}

// ============================================================================
// Run Server
// ============================================================================

export async function runServer(): Promise<void> {
  const server = new McpServer({
    name: "memos-memory",
    version: "1.0.0",
  });

  registerTools(server);

  const transport = new StdioServerTransport();

  // Connect FIRST (completes MCP handshake immediately),
  // then do background init to prevent Claude Code timeout.
  await server.connect(transport);

  // Background init — don't await
  backgroundInit().catch((err) => {
    logger.error(`Background init error: ${err}`);
  });

  logger.debug("MemOS MCP Server (Node.js) started");
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
