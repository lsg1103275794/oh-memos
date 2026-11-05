#!/usr/bin/env node

// Freeze the business-relevant portion of the tools/list schema.
// JSON Schema dialect metadata and local $ref layout are intentionally ignored;
// required fields, constraints, descriptions, annotations, and tool order are
// part of the compatibility contract.
import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { existsSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { once } from "node:events";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { scratchDir } from "./_scratch.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const DIST_ENTRY = join(ROOT, "dist", "index.js");
const BASELINE_PATH = join(ROOT, "schema-semantic-baseline.json");
const LEGACY_PROTOCOL_VERSION = "2025-11-25";
const DIALECT_KEYS = new Set(["$schema", "$id", "$comment", "$defs"]);
const ORDER_INSENSITIVE_ARRAY_KEYS = new Set(["required", "enum", "type", "anyOf", "oneOf", "allOf"]);

function sortObject(object) {
  return Object.fromEntries(Object.entries(object).sort(([a], [b]) => a.localeCompare(b)));
}

function resolvePointer(root, ref) {
  if (typeof ref !== "string" || !ref.startsWith("#/")) return undefined;
  let current = root;
  for (const raw of ref.slice(2).split("/")) {
    if (current === null || typeof current !== "object" || Array.isArray(current)) return undefined;
    const key = raw.replaceAll("~1", "/").replaceAll("~0", "~");
    current = current[key];
  }
  return current;
}

function canonicalize(value, root, parentKey = "", path = [], refs = new Set()) {
  if (Array.isArray(value)) {
    const items = value.map((item) => canonicalize(item, root, "", path, refs));
    if (ORDER_INSENSITIVE_ARRAY_KEYS.has(parentKey)) {
      return items.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
    }
    return items;
  }
  if (value === null || typeof value !== "object") return value;

  const ref = typeof value.$ref === "string" ? value.$ref : undefined;
  if (ref && !refs.has(ref)) {
    const target = resolvePointer(root, ref);
    if (target !== undefined) {
      const nextRefs = new Set(refs);
      nextRefs.add(ref);
      return canonicalize(target, root, parentKey, path, nextRefs);
    }
  }

  const result = {};
  for (const key of Object.keys(value).sort()) {
    if (DIALECT_KEYS.has(key) || key === "$ref") continue;
    const nextPath = [...path, key];
    result[key] =
      key === "default" && path.at(-1) === "cube_id"
        ? "<MEMOS_DEFAULT_CUBE>"
        : canonicalize(value[key], root, key, nextPath, refs);
  }
  return sortObject(result);
}

function schemaHash(schema) {
  const canonical = JSON.stringify(canonicalize(schema, schema));
  return createHash("sha256").update(canonical).digest("hex");
}

function envFor(root, cube, enableDelete) {
  return {
    ...process.env,
    MEMOS_MODE: "lite",
    MEMOS_PROVIDER: "local",
    MEMOS_URL: "",
    MEMOS_USER: "schema-semantic-snapshot",
    MEMOS_DEFAULT_CUBE: cube,
    MEMOS_CUBES_DIR: root,
    MEMOS_ENV_FILE: join(root, "missing.env"),
    MEMOS_LITE_EMBED: "off",
    MEMOS_ENABLE_DELETE: String(enableDelete),
    NEO4J_HTTP_URL: "",
  };
}

async function captureTools(enableDelete) {
  const root = scratchDir("oh-memos-schema-semantic-");
  const child = spawn(process.execPath, [DIST_ENTRY], {
    cwd: ROOT,
    env: envFor(root, "ci_cube", enableDelete),
    stdio: ["pipe", "pipe", "pipe"],
  });
  let stderr = "";
  let buffer = "";
  let nextId = 1;
  const pending = new Map();
  const rejectPending = (error) => {
    for (const { reject } of pending.values()) reject(error);
    pending.clear();
  };
  const timeout = setTimeout(() => {
    rejectPending(new Error(`tools/list timed out\nstderr:\n${stderr.slice(0, 1200)}`));
  }, 10000);

  const cleanup = async () => {
    clearTimeout(timeout);
    if (child.exitCode === null) child.kill();
    if (child.exitCode === null) await Promise.race([once(child, "exit"), new Promise((resolve) => setTimeout(resolve, 500))]);
    rmSync(root, { recursive: true, force: true });
  };

  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) => {
    buffer += chunk;
    let newline = buffer.indexOf("\n");
    while (newline !== -1) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (line) {
        try {
          const message = JSON.parse(line);
          const handler = pending.get(String(message.id));
          if (handler) {
            pending.delete(String(message.id));
            handler.resolve(message);
          }
        } catch {
          stderr += `\n[non-json stdout] ${line}`;
        }
      }
      newline = buffer.indexOf("\n");
    }
  });
  child.stderr.on("data", (chunk) => {
    stderr += chunk;
  });
  child.on("error", (error) => rejectPending(error));
  child.on("exit", (code, signal) => {
    if (pending.size > 0) {
      rejectPending(new Error(`server exited before tools/list (code=${String(code)}, signal=${String(signal)})`));
    }
  });

  const rpc = (method, params) => {
    const id = nextId++;
    return new Promise((resolve, reject) => {
      pending.set(String(id), { resolve, reject });
      try {
        child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`);
      } catch (error) {
        pending.delete(String(id));
        reject(error);
      }
    });
  };

  try {
    const initialized = await rpc("initialize", {
      protocolVersion: LEGACY_PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: { name: "schema-semantic-snapshot", version: "1" },
    });
    if (initialized.error) throw new Error(`initialize failed: ${JSON.stringify(initialized.error)}`);
    child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized", params: {} })}\n`);
    const listed = await rpc("tools/list", {});
    if (listed.error || !Array.isArray(listed.result?.tools)) {
      throw new Error(`tools/list failed: ${JSON.stringify(listed)}`);
    }
    return listed.result.tools;
  } finally {
    child.stdin.end();
    await cleanup();
  }
}

async function buildSnapshot() {
  if (!existsSync(DIST_ENTRY)) throw new Error(`${DIST_ENTRY} is missing; run npm run build first`);
  const [alwaysOn, all] = await Promise.all([captureTools(false), captureTools(true)]);
  const alwaysOnNames = alwaysOn.map((tool) => tool.name);
  const allNames = all.map((tool) => tool.name);
  if (allNames.length !== 17 || new Set(allNames).size !== allNames.length) {
    throw new Error(`expected 17 unique tools, received ${allNames.length}: ${JSON.stringify(allNames)}`);
  }
  if (alwaysOnNames.length !== 16 || new Set(alwaysOnNames).size !== alwaysOnNames.length) {
    throw new Error(`expected 16 unique always-on tools, received ${alwaysOnNames.length}: ${JSON.stringify(alwaysOnNames)}`);
  }
  const conditionalNames = allNames.filter((name) => !alwaysOnNames.includes(name));
  if (JSON.stringify(conditionalNames) !== JSON.stringify(["memos_delete"])) {
    throw new Error(`unexpected conditional tools: ${JSON.stringify(conditionalNames)}`);
  }

  const tools = Object.fromEntries(
    all.map((tool) => [
      tool.name,
      {
        description: tool.description ?? "",
        annotations: sortObject(tool.annotations ?? {}),
        schemaSha256: schemaHash(tool.inputSchema ?? {}),
      },
    ]),
  );
  return {
    snapshotVersion: 1,
    protocolVersion: LEGACY_PROTOCOL_VERSION,
    toolOrder: allNames,
    alwaysOnTools: alwaysOnNames,
    conditionalTools: conditionalNames,
    tools,
  };
}

function compare(current, baseline) {
  const currentText = JSON.stringify(current, null, 2);
  const baselineText = JSON.stringify(baseline, null, 2);
  if (currentText === baselineText) {
    console.log(`semantic schema snapshot matches (${current.toolOrder.length} tools)`);
    return true;
  }
  const currentLines = currentText.split("\n");
  const baselineLines = baselineText.split("\n");
  const first = currentLines.findIndex((line, index) => line !== baselineLines[index]);
  console.error(`semantic schema snapshot drift at line ${first + 1}`);
  console.error(`  baseline: ${baselineLines[first] ?? "<missing>"}`);
  console.error(`  current:  ${currentLines[first] ?? "<missing>"}`);
  return false;
}

const current = await buildSnapshot();
if (process.argv.includes("--write")) {
  writeFileSync(BASELINE_PATH, `${JSON.stringify(current, null, 2)}\n`, "utf8");
  console.log(`wrote semantic schema snapshot: ${BASELINE_PATH}`);
} else if (process.argv.includes("--check")) {
  if (!existsSync(BASELINE_PATH)) {
    console.error(`missing ${BASELINE_PATH}; run npm run schema:semantic:freeze once`);
    process.exitCode = 2;
  } else if (!compare(current, JSON.parse(readFileSync(BASELINE_PATH, "utf8")))) {
    process.exitCode = 1;
  }
} else {
  console.log(JSON.stringify(current, null, 2));
}
