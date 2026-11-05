/**
 * MemOS MCP Server — factory, dual-era stdio serving, and background init
 */
import { McpServer } from "@modelcontextprotocol/server";
import { serveStdio, StdioServerTransport } from "@modelcontextprotocol/server/stdio";
import type { StdioServerHandle } from "@modelcontextprotocol/server/stdio";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { MEMOS_ALWAYS_LOAD, MEMOS_DEFAULT_CUBE, MEMOS_ENABLE_DELETE, MEMOS_PROVIDER, logger } from "./config.js";
import {
  apiHealthUrl,
  apiUrlForDisplay,
  isApiTimeoutError,
  isApiUnreachableError,
  waitForApiReady,
} from "./api-client.js";
import { ensureCubeRegistered } from "./cube-manager.js";
import { toolSchemas, toolAnnotations } from "./tools-registry.js";
import { serverOptions, toolMeta } from "./server-instructions.js";
import { dispatchTool, handleApiTimeout, handleApiUnreachable } from "./handlers/index.js";
import { UnconfirmedMemoryWriteError } from "./memory-write-response.js";
import type { TextContent } from "./types.js";
import { createOnceFireAndForget } from "./server-lifecycle.js";
import { NormalizingStdioTransport } from "./stdio-compat-transport.js";

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
        // Lets a client tell retrieval from mutation without parsing prose.
        // The practical win is plan mode: without readOnlyHint every
        // `memos_search` raises a permission prompt, and CLAUDE.md asks for a
        // search before coding — so the friction was quietly training the
        // rule away.
        annotations: toolAnnotations[name],
        _meta: toolMeta(name, MEMOS_ALWAYS_LOAD),
      },
      async (args: Record<string, unknown>) => {
        startBackgroundInitOnce();
        try {
          const result = await dispatchTool(name, args);
          return {
            content: result.map((r: TextContent) => ({ type: "text" as const, text: r.text })),
          };
        } catch (err: unknown) {
          if (err instanceof UnconfirmedMemoryWriteError) {
            return { content: err.content, isError: true };
          }
          const errStr = String(err);
          if (isApiTimeoutError(err)) {
            return { content: await handleApiTimeout(), isError: true };
          }
          if (isApiUnreachableError(err)) {
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
                  `- Verify MemOS API is healthy: \`curl ${apiUrlForDisplay(apiHealthUrl(undefined, true))}\``,
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

const startBackgroundInitOnce = createOnceFireAndForget(
  () => backgroundInit(),
  (error) => logger.error(`Background init error: ${String(error)}`),
);

// ============================================================================
// Background Init
// ============================================================================

async function backgroundInit(): Promise<void> {
  if (MEMOS_PROVIDER === "local") {
    logger.info("Local memory provider enabled; skipping API readiness and cube registration");
    return;
  }
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

// serverInfo 从 package.json 读取,而非硬编码 —— 硬编码会在每次发版后
// 悄悄漂移(2.0.0 发布时这里仍报 1.0.1)。dist/server.js 的上一级即包根。
const pkg: { name: string; version: string } = JSON.parse(
  readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), "..", "package.json"),
    "utf8",
  ),
);

export function buildServer(): McpServer {
  const server = new McpServer(
    {
      name: pkg.name,
      version: pkg.version,
    },
    serverOptions(MEMOS_ALWAYS_LOAD),
  );
  registerTools(server);
  return server;
}

export async function runServer(): Promise<StdioServerHandle> {
  const transport = new NormalizingStdioTransport(new StdioServerTransport());
  const handle = serveStdio(buildServer, {
    legacy: "serve",
    transport,
    onerror: (error) => logger.error(`MCP transport error: ${String(error)}`),
  });

  let closing: Promise<void> | undefined;
  let onSignal: (() => void) | undefined;
  const close = (): Promise<void> => {
    if (!closing) {
      closing = handle.close().catch((error) => {
        logger.error(`MCP transport close failed: ${String(error)}`);
      }).finally(() => {
        if (onSignal) {
          process.off("SIGINT", onSignal);
          process.off("SIGTERM", onSignal);
        }
      });
    }
    return closing;
  };

  onSignal = (): void => {
    void close();
  };
  process.once("SIGINT", onSignal);
  process.once("SIGTERM", onSignal);

  logger.debug("MemOS MCP Server (Node.js) started");
  return { close };
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
