#!/usr/bin/env node
/**
 * Schema token budget.
 *
 * Every tool's name, description, inputSchema and annotations are sent to the
 * model in `tools/list` on **every turn**, before the user has said anything.
 * That cost is invisible while you edit a description, and it only ever moves
 * one way. This measures it and fails the build when it drifts.
 *
 * Two notes on method:
 *
 * - The script starts the built stdio server and requests `tools/list`, so the
 *   bytes counted are the actual wire entries emitted by the installed SDK.
 * - Tokens are approximated from bytes rather than measured with a tokenizer.
 *   Installing tiktoken for a housekeeping script is a poor trade, and the
 *   number that matters here is *relative drift*, which bytes track faithfully.
 *   The divisor is a blend: Chinese runs ~2 bytes/token in UTF-8, English ~4.
 *
 * Usage:
 *   node scripts/schema-budget.mjs            # report
 *   node scripts/schema-budget.mjs --check    # compare to baseline, exit 1 on breach
 *   node scripts/schema-budget.mjs --write    # freeze current numbers as the baseline
 */

import { spawn } from "node:child_process";
import { existsSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { scratchDir } from "./_scratch.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const BASELINE_PATH = join(ROOT, "schema-baseline.json");
const DIST_ENTRY = join(ROOT, "dist", "index.js");
const LEGACY_PROTOCOL_VERSION = "2025-11-25";
const SCHEMA_DEFAULT_CUBE = "ci_cube";

const BYTES_PER_TOKEN = 3.2;
const DRIFT_THRESHOLD = 0.05; // +5% over baseline total fails --check
const TOP_N = 5;

/** Tools the server only registers under a flag — they are not part of the per-turn floor. */
const CONDITIONAL_TOOLS = new Set(["memos_delete"]);

const bytes = (s) => Buffer.byteLength(s, "utf8");
const tokens = (b) => Math.round(b / BYTES_PER_TOKEN);
const pct = (n) => `${n >= 0 ? "+" : ""}${(n * 100).toFixed(1)}%`;

function listTools(enableDelete) {
  const tempRoot = scratchDir("oh-memos-schema-budget-");
  const env = {
    ...process.env,
    MEMOS_MODE: "lite",
    MEMOS_PROVIDER: "local",
    MEMOS_URL: "",
    MEMOS_USER: "schema-budget",
    // Keep the fixture length stable: schema defaults are part of wire bytes.
    MEMOS_DEFAULT_CUBE: SCHEMA_DEFAULT_CUBE,
    MEMOS_CUBES_DIR: tempRoot,
    MEMOS_ENV_FILE: join(tempRoot, "missing.env"),
    MEMOS_LITE_EMBED: "off",
    MEMOS_ENABLE_DELETE: String(enableDelete),
    NEO4J_HTTP_URL: "",
  };

  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [DIST_ENTRY], {
      stdio: ["pipe", "pipe", "pipe"],
      env,
    });
    const pending = new Map();
    let stdoutBuffer = "";
    let stderr = "";
    let settled = false;

    const cleanup = () => {
      if (child.exitCode === null && child.signalCode === null) child.kill();
      rmSync(tempRoot, { recursive: true, force: true });
    };
    const fail = (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      cleanup();
      reject(error);
    };

    const timeout = setTimeout(() => {
      fail(new Error(`Timed out waiting for tools/list.\nstderr:\n${stderr.slice(0, 1600)}`));
    }, 10000);

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdoutBuffer += chunk;
      let newline = stdoutBuffer.indexOf("\n");
      while (newline !== -1) {
        const line = stdoutBuffer.slice(0, newline).trim();
        stdoutBuffer = stdoutBuffer.slice(newline + 1);
        if (line) {
          try {
            const message = JSON.parse(line);
            const handler = pending.get(String(message.id));
            if (handler) {
              pending.delete(String(message.id));
              handler(message);
            }
          } catch {
            stderr += `\n[non-json stdout] ${line}`;
          }
        }
        newline = stdoutBuffer.indexOf("\n");
      }
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", fail);
    child.on("exit", (code, signal) => {
      if (!settled && pending.size > 0) {
        fail(
          new Error(
            `Server exited before tools/list (code=${String(code)}, signal=${String(signal)}).\n` +
              `stderr:\n${stderr.slice(0, 1600)}`
          )
        );
      }
    });

    const rpc = (id, method, params) =>
      new Promise((resolveRpc) => {
        pending.set(String(id), resolveRpc);
        child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`);
      });

    (async () => {
      const initialized = await rpc(1, "initialize", {
        protocolVersion: LEGACY_PROTOCOL_VERSION,
        capabilities: {},
        clientInfo: { name: "schema-budget", version: "1.0.0" },
      });
      if (initialized.error) {
        throw new Error(`initialize failed: ${JSON.stringify(initialized.error)}`);
      }

      child.stdin.write(
        `${JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized", params: {} })}\n`
      );
      const listed = await rpc(2, "tools/list", {});
      if (listed.error) {
        throw new Error(`tools/list failed: ${JSON.stringify(listed.error)}`);
      }
      if (!Array.isArray(listed.result?.tools)) {
        throw new Error("tools/list returned no tools array");
      }

      settled = true;
      clearTimeout(timeout);
      child.stdin.end();
      cleanup();
      resolve(listed.result.tools);
    })().catch(fail);
  });
}

async function measure() {
  if (!existsSync(DIST_ENTRY)) {
    console.error(`✗ ${DIST_ENTRY} not found — run \`npm run build\` first.`);
    process.exit(2);
  }

  const [alwaysOnEntries, allEntries] = await Promise.all([listTools(false), listTools(true)]);
  const alwaysOnNames = new Set(alwaysOnEntries.map((tool) => tool.name));

  const tools = {};
  for (const wireEntry of allEntries) {
    const conditional = !alwaysOnNames.has(wireEntry.name);
    tools[wireEntry.name] = {
      descriptionBytes: bytes(wireEntry.description ?? ""),
      schemaBytes: bytes(JSON.stringify(wireEntry.inputSchema ?? {})),
      totalBytes: bytes(JSON.stringify(wireEntry)),
      conditional: conditional || undefined,
    };
  }

  const conditionalNames = new Set(
    Object.entries(tools)
      .filter(([, tool]) => tool.conditional)
      .map(([name]) => name)
  );
  if (
    conditionalNames.size !== CONDITIONAL_TOOLS.size ||
    [...CONDITIONAL_TOOLS].some((name) => !conditionalNames.has(name))
  ) {
    throw new Error(
      `Conditional tool set changed: expected ${[...CONDITIONAL_TOOLS].join(", ")}; ` +
        `received ${[...conditionalNames].join(", ")}`
    );
  }

  const totalBytes = Object.values(tools).reduce((a, t) => a + t.totalBytes, 0);
  const alwaysOnBytes = Object.values(tools)
    .filter((tool) => !tool.conditional)
    .reduce((a, tool) => a + tool.totalBytes, 0);

  return {
    bytesPerTokenAssumed: BYTES_PER_TOKEN,
    toolCount: Object.keys(tools).length,
    totalBytes,
    alwaysOnBytes,
    tools,
  };
}

function report(current, baseline) {
  const ranked = Object.entries(current.tools).sort((a, b) => b[1].totalBytes - a[1].totalBytes);

  console.log("Tool surface — what every turn pays before the user speaks\n");
  console.log(`  tools:        ${current.toolCount}`);
  console.log(
    `  total:        ${current.totalBytes} B  ≈ ${tokens(current.totalBytes)} tokens`
  );
  console.log(
    `  always-on:    ${current.alwaysOnBytes} B  ≈ ${tokens(current.alwaysOnBytes)} tokens ` +
      `(excludes ${[...CONDITIONAL_TOOLS].join(", ")}, registered only under a flag)`
  );

  console.log(`\n  Most expensive ${TOP_N}:`);
  for (const [name, t] of ranked.slice(0, TOP_N)) {
    const share = ((t.totalBytes / current.totalBytes) * 100).toFixed(1);
    console.log(
      `    ${name.padEnd(24)} ${String(t.totalBytes).padStart(5)} B  (${share.padStart(4)}%)  ` +
        `desc ${t.descriptionBytes} / schema ${t.schemaBytes}`
    );
  }

  if (!baseline) {
    console.log(`\n  No baseline yet — freeze one with \`--write\`.`);
    return;
  }

  const drift = (current.totalBytes - baseline.totalBytes) / baseline.totalBytes;
  console.log(
    `\n  Baseline:     ${baseline.totalBytes} B → now ${current.totalBytes} B  (${pct(drift)})`
  );

  // Per-tool movement is the actionable part: a total that crept up is only
  // useful if you can see which description did the creeping.
  const moved = Object.entries(current.tools)
    .map(([name, t]) => [name, t.totalBytes - (baseline.tools[name]?.totalBytes ?? 0)])
    .filter(([, delta]) => delta !== 0)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

  if (moved.length > 0) {
    console.log("\n  Changed since baseline:");
    for (const [name, delta] of moved) {
      const isNew = !(name in baseline.tools);
      console.log(
        `    ${delta > 0 ? "▲" : "▼"} ${name.padEnd(24)} ${delta > 0 ? "+" : ""}${delta} B${isNew ? "  (new tool)" : ""}`
      );
    }
  }
  for (const name of Object.keys(baseline.tools)) {
    if (!(name in current.tools)) console.log(`    ✗ ${name.padEnd(24)} removed`);
  }

  return drift;
}

async function main() {
  const args = process.argv.slice(2);
  const current = await measure();
  const baseline = existsSync(BASELINE_PATH)
    ? JSON.parse(readFileSync(BASELINE_PATH, "utf8"))
    : null;

  if (args.includes("--write")) {
    writeFileSync(BASELINE_PATH, `${JSON.stringify(current, null, 2)}\n`, "utf8");
    console.log(`✓ Baseline frozen: ${current.totalBytes} B ≈ ${tokens(current.totalBytes)} tokens`);
    console.log(`  ${BASELINE_PATH}`);
    return;
  }

  const drift = report(current, baseline);

  if (args.includes("--check")) {
    if (!baseline) {
      console.error("\n✗ --check needs a baseline. Run with --write once, and commit the file.");
      process.exit(2);
    }
    if (drift > DRIFT_THRESHOLD) {
      console.error(
        `\n✗ Tool surface grew ${pct(drift)}, over the ${pct(DRIFT_THRESHOLD)} budget.`
      );
      console.error("  Either trim a description, or re-freeze with --write if the growth is earned.");
      process.exit(1);
    }
    console.log(`\n✓ Within budget (${pct(drift)} vs ${pct(DRIFT_THRESHOLD)} allowed).`);
  }
}

main().catch((err) => {
  console.error(`✗ schema-budget failed: ${err?.stack ?? err}`);
  process.exit(2);
});
