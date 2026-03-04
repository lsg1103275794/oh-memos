#!/usr/bin/env node

/**
 * oh-memos-mcp — MCP Server for MemOS Intelligent Memory Management
 *
 * Usage:
 *   npx oh-memos-mcp
 *   node dist/index.js
 *
 * Configuration via environment variables or CLI args.
 * See README.md for full documentation.
 */

import { runServer } from "./server.js";
import { logger } from "./config.js";

runServer().catch((err) => {
  logger.error(`Fatal error: ${err}`);
  process.exit(1);
});
