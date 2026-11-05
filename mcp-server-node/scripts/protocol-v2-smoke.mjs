// MCP SDK v2 client/era contract smoke.
//
// This complements protocol-smoke.mjs: the latter freezes raw 2025-era JSON-RPC,
// while this harness exercises the SDK v2 client legacy, auto, and pinned modern
// negotiation paths against the same executable package.
import { spawn } from "node:child_process";
import { once } from "node:events";
import { existsSync, rmSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";
import { scratchDir } from "./_scratch.mjs";

const DIST_ENTRY = fileURLToPath(new URL("../dist/index.js", import.meta.url));
const PACKAGE_ROOT = fileURLToPath(new URL("..", import.meta.url));
const MODERN_VERSION = "2026-07-28";

let failures = 0;

function check(label, condition, detail = "") {
  if (condition) {
    console.log("  ok   " + label);
    return;
  }
  console.log("  FAIL " + label + (detail ? " - " + detail : ""));
  failures += 1;
}

function textContent(result) {
  return result?.content?.map((item) => item.text ?? "").join("\n") ?? JSON.stringify(result);
}

function baseEnv(root, cube, overrides = {}) {
  return Object.fromEntries(
    Object.entries({
      ...process.env,
      MEMOS_MODE: "lite",
      MEMOS_PROVIDER: "local",
      MEMOS_URL: "",
      MEMOS_USER: "protocol-v2-smoke",
      MEMOS_DEFAULT_CUBE: cube,
      MEMOS_CUBES_DIR: root,
      MEMOS_ENV_FILE: join(root, "missing.env"),
      MEMOS_LITE_EMBED: "off",
      MEMOS_ENABLE_DELETE: "false",
      MEMOS_LOG_LEVEL: "INFO",
      ...overrides,
    }).filter(([, value]) => value !== undefined),
  );
}

function negotiation(mode) {
  return {
    versionNegotiation:
      mode === "pin" ? { mode: { pin: MODERN_VERSION } } : { mode },
  };
}

async function closeQuietly(client, transport) {
  if (!client && !transport) return;
  try {
    await client?.close();
  } catch {
    // The server may already have closed its pipe; cleanup remains best effort.
  }
  try {
    await transport?.close();
  } catch {
    // StdioClientTransport.close() is idempotent for the smoke's purposes.
  }
}

async function runClientContract(
  mode,
  {
    stringifyArguments = false,
    root,
    cube,
    envOverrides = {},
    expectedToolCount = 16,
    call = { name: "memos_suggest", arguments: { context: `${mode} default call` } },
    assertResult = () => true,
  },
) {
  const label = mode === "pin" ? "modern pin" : `v2 ${mode}`;
  const env = baseEnv(root, cube, envOverrides);
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [DIST_ENTRY],
    cwd: PACKAGE_ROOT,
    env,
    stderr: "pipe",
  });
  let stderr = "";
  transport.stderr?.on("data", (chunk) => {
    stderr += String(chunk);
  });

  if (stringifyArguments) {
    const send = transport.send.bind(transport);
    transport.send = (message, options) => {
      if (
        message?.method === "tools/call" &&
        message.params &&
        typeof message.params.arguments === "object" &&
        message.params.arguments !== null
      ) {
        message = {
          ...message,
          params: {
            ...message.params,
            arguments: JSON.stringify(message.params.arguments),
          },
        };
      }
      return send(message, options);
    };
  }

  const client = new Client(
    { name: "oh-memos-sdk-v2-smoke", version: "0" },
    negotiation(mode),
  );

  try {
    await client.connect(transport);
    const listed = await client.listTools();
    check(
      `${label} connects and lists ${expectedToolCount} tools`,
      listed.tools.length === expectedToolCount,
      String(listed.tools.length),
    );

    const result = await client.callTool(call);
    const text = textContent(result);
    check(`${label} calls a tool`, text.length > 0, text.slice(0, 180));
    check(`${label} representative result contract`, assertResult(result, text), text.slice(0, 240));
    if (stringifyArguments) {
      check(`${label} accepts stringified arguments`, !result.isError, text.slice(0, 180));
    }

    const unknown = await client.callTool({
      name: "memos_suggest",
      arguments: {
        context: `${label} unknown key`,
        extra_contract_key: "ignored",
      },
    });
    check(`${label} ignores unknown keys without failing`, !unknown.isError, textContent(unknown).slice(0, 180));

    const empty = await client.callTool({ name: "memos_suggest", arguments: {} });
    check(`${label} rejects an empty required-argument object`, empty.isError === true, textContent(empty).slice(0, 180));
    return { stderr, client, transport };
  } catch (error) {
    check(`${label} client contract`, false, `${String(error)}\nstderr:\n${stderr.slice(0, 1600)}`);
    await closeQuietly(client, transport);
    return { stderr, client: null, transport: null };
  }
}

async function runProbeSideEffectContract() {
  console.log("\nProbe/factory side-effect contract");
  const root = scratchDir("oh-memos-protocol-v2-probe-");
  const cube = "protocol_probe_cube";
  const env = baseEnv(root, cube, {
    MEMOS_MODE: "full",
    MEMOS_PROVIDER: "api",
    MEMOS_URL: "http://127.0.0.1:1",
    MEMOS_API_WAIT_MAX: "0",
    MEMOS_TIMEOUT_HEALTH: "1",
  });
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [DIST_ENTRY],
    cwd: PACKAGE_ROOT,
    env,
    stderr: "pipe",
  });
  let stderr = "";
  transport.stderr?.on("data", (chunk) => {
    stderr += String(chunk);
  });
  const client = new Client(
    { name: "oh-memos-sdk-v2-probe", version: "0" },
    { versionNegotiation: { mode: "auto" } },
  );

  try {
    await client.connect(transport);
    await new Promise((resolve) => setTimeout(resolve, 150));
    check(
      "auto probe does not start background init or API access",
      !/Local memory provider enabled|MemOS API not ready|Background init/i.test(stderr),
      stderr.slice(0, 400),
    );
    await client.callTool({
      name: "memos_suggest",
      arguments: { context: "first real call" },
    });
    await client.callTool({
      name: "memos_suggest",
      arguments: { context: "second real call" },
    });
    await new Promise((resolve) => setTimeout(resolve, 50));
    const initLogs = stderr.match(/MemOS API not ready after 0s/g) ?? [];
    check("background init starts once on real calls", initLogs.length === 1, stderr.slice(0, 600));
    check("probe/fallback creates no cube before a write", !existsSync(join(root, cube)));
  } catch (error) {
    check("probe side-effect contract", false, `${String(error)}\nstderr:\n${stderr.slice(0, 1600)}`);
  } finally {
    await closeQuietly(client, transport);
    rmSync(root, { recursive: true, force: true });
  }
}

async function runLargeMessageContract() {
  console.log("\nStdio buffer boundary contract");
  const root = scratchDir("oh-memos-protocol-v2-large-");
  const cube = "protocol_large_cube";
  const query = "x".repeat(4_800_000);
  const envelope = JSON.stringify({
    jsonrpc: "2.0",
    id: 1,
    method: "tools/call",
    params: {
      name: "memos_graph",
      arguments: { mode: "related", query, project_path: root, cube_id: cube },
    },
  });
  check("large Graphify-shaped request stays below stdio 10 MB", Buffer.byteLength(envelope) < 10 * 1024 * 1024);

  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [DIST_ENTRY],
    cwd: PACKAGE_ROOT,
    env: baseEnv(root, cube),
    stderr: "pipe",
  });
  let stderr = "";
  transport.stderr?.on("data", (chunk) => {
    stderr += String(chunk);
  });
  const client = new Client(
    { name: "oh-memos-sdk-v2-large", version: "0" },
    { versionNegotiation: { mode: { pin: MODERN_VERSION } } },
  );
  try {
    await client.connect(transport);
    const result = await client.callTool({
      name: "memos_graph",
      arguments: { mode: "related", query, project_path: root, cube_id: cube },
    });
    const text = textContent(result);
    check("large request reaches business layer", text.includes("Lite mode"), text.slice(0, 240));
    check("large request does not close the transport", !stderr.includes("exceeds the maximum"), stderr.slice(0, 400));
  } catch (error) {
    check("large message contract", false, `${String(error)}\nstderr:\n${stderr.slice(0, 1600)}`);
  } finally {
    await closeQuietly(client, transport);
    rmSync(root, { recursive: true, force: true });
  }
}

async function runSignalContract() {
  console.log("\nSignal close contract");
  for (const signalName of ["SIGINT", "SIGTERM"]) {
    const root = scratchDir(`oh-memos-protocol-v2-${signalName.toLowerCase()}-`);
    const child = spawn(process.execPath, [DIST_ENTRY], {
      cwd: PACKAGE_ROOT,
      env: baseEnv(root, `protocol_${signalName.toLowerCase()}_cube`, { MEMOS_LOG_LEVEL: "DEBUG" }),
      // Keep stdin open: EOF can stop the server before a signal is sent.
      stdio: ["pipe", "pipe", "pipe"],
    });
    // Listen immediately, including during startup, and drain stderr before
    // checking shutdown diagnostics.
    const exited = once(child, "close");
    let markStarted;
    const started = new Promise((resolve) => {
      markStarted = resolve;
    });
    let stderr = "";
    child.stderr.setEncoding("utf8");
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
      if (stderr.includes("MemOS MCP Server (Node.js) started")) markStarted();
    });
    try {
      // The startup log follows signal-handler registration. A fixed sleep
      // can either miss an early exit or kill a server before its handlers run.
      await withTimeout(Promise.race([
        started,
        exited.then(([code, signal]) => {
          throw new Error(`Server exited before readiness: ${code}/${signal}`);
        }),
      ]), 5000, "Server did not become ready");
      if (!child.kill(signalName)) throw new Error(`${signalName} was not delivered`);
      const [code, signal] = await withTimeout(exited, 2500, `${signalName} close timed out`);
      // Windows terminates a process for these signals instead of invoking
      // POSIX signal handlers. On POSIX, require the graceful zero-code exit.
      const cleanExit = code === 0 || (process.platform === "win32" && signal === signalName);
      check(`${signalName} closes the server`, cleanExit, `${code}/${signal}`);
      check(`${signalName} close has no unhandled rejection`, !/unhandled promise rejection|unhandledpromiserejection/i.test(stderr), stderr.slice(0, 600));
    } catch (error) {
      check(`${signalName} close contract`, false, `${String(error)}\nstderr:\n${stderr.slice(0, 1200)}`);
    } finally {
      if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
      await exited.catch(() => {});
      rmSync(root, { recursive: true, force: true });
    }
  }
}

async function withTimeout(promise, timeoutMs, message) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(message)), timeoutMs);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

async function runClientPipeCloseContract() {
  console.log("\nClient pipe close contract");
  const root = scratchDir("oh-memos-protocol-v2-pipe-close-");
  const child = spawn(process.execPath, [DIST_ENTRY], {
    cwd: PACKAGE_ROOT,
    env: baseEnv(root, "protocol_pipe_close_cube"),
    stdio: ["pipe", "pipe", "pipe"],
  });
  let stderr = "";
  child.stderr.setEncoding("utf8");
  child.stderr.on("data", (chunk) => {
    stderr += chunk;
  });
  try {
    child.stdin.write(`${JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2025-11-25",
        capabilities: {},
        clientInfo: { name: "pipe-close", version: "0" },
      },
    })}\n`);
    await new Promise((resolve) => setTimeout(resolve, 120));
    child.stdin.end();
    const [code, signal] = await Promise.race([
      once(child, "exit"),
      new Promise((resolve) => setTimeout(() => resolve([null, "timeout"]), 2500)),
    ]);
    check("client pipe close releases the server", code !== null || signal !== "timeout", `${code}/${signal}`);
    check("client pipe close has no unhandled rejection", !/unhandled promise rejection|unhandledpromiserejection/i.test(stderr), stderr.slice(0, 600));
  } catch (error) {
    check("client pipe close contract", false, `${String(error)}\nstderr:\n${stderr.slice(0, 1200)}`);
  } finally {
    if (child.exitCode === null) child.kill();
    rmSync(root, { recursive: true, force: true });
  }
}

async function runConditionalToolMatrix() {
  console.log("\nConditional tool matrix");
  for (const mode of ["legacy", "auto", "pin"]) {
    const root = scratchDir(`oh-memos-protocol-v2-delete-${mode}-`);
    const result = await runClientContract(mode, {
      root,
      cube: `protocol_v2_delete_${mode}_cube`,
      expectedToolCount: 17,
      envOverrides: { MEMOS_ENABLE_DELETE: "true" },
      call: {
        name: "memos_delete",
        arguments: { memory_id: "not-used-in-lite" },
      },
      assertResult: (_result, text) => text.includes("Lite mode: memos_delete is unavailable"),
    });
    await closeQuietly(result.client, result.transport);
    rmSync(root, { recursive: true, force: true });
  }
}

async function runProviderMatrix() {
  console.log("\nProvider matrix");
  for (const mode of ["legacy", "auto", "pin"]) {
    const root = scratchDir(`oh-memos-protocol-v2-full-${mode}-`);
    const result = await runClientContract(mode, {
      root,
      cube: `protocol_v2_full_${mode}_cube`,
      envOverrides: {
        MEMOS_MODE: "full",
        MEMOS_PROVIDER: "api",
        MEMOS_URL: "http://127.0.0.1:1",
        MEMOS_API_WAIT_MAX: "0",
        MEMOS_TIMEOUT_HEALTH: "1",
      },
      call: { name: "memos_admin", arguments: { action: "capabilities" } },
      assertResult: (_result, text) => text.includes("**Mode**: full") && text.includes("Full exposes API"),
    });
    await closeQuietly(result.client, result.transport);
    rmSync(root, { recursive: true, force: true });
  }
}

if (!existsSync(DIST_ENTRY)) {
  console.error("dist/index.js is missing; run npm run build first.");
  process.exit(2);
}

console.log("\nv2 client legacy contract");
const legacyRoot = scratchDir("oh-memos-protocol-v2-legacy-");
const legacyCube = "protocol_v2_legacy_cube";
const legacy = await runClientContract("legacy", { root: legacyRoot, cube: legacyCube });
await closeQuietly(legacy.client, legacy.transport);
rmSync(legacyRoot, { recursive: true, force: true });

console.log("\nv2 client auto contract");
const autoRoot = scratchDir("oh-memos-protocol-v2-auto-");
const autoCube = "protocol_v2_auto_cube";
const auto = await runClientContract("auto", { root: autoRoot, cube: autoCube });
await closeQuietly(auto.client, auto.transport);
rmSync(autoRoot, { recursive: true, force: true });

console.log("\nv2 client modern pin contract");
const pinRoot = scratchDir("oh-memos-protocol-v2-pin-");
const pinCube = "protocol_v2_pin_cube";
const pin = await runClientContract("pin", { root: pinRoot, cube: pinCube });
await closeQuietly(pin.client, pin.transport);
rmSync(pinRoot, { recursive: true, force: true });

console.log("\nv2 client stringified argument contracts");
for (const mode of ["legacy", "auto", "pin"]) {
  const root = scratchDir(`oh-memos-protocol-v2-string-${mode}-`);
  const result = await runClientContract(mode, {
    root,
    cube: `protocol_v2_string_${mode}_cube`,
    stringifyArguments: true,
  });
  await closeQuietly(result.client, result.transport);
  rmSync(root, { recursive: true, force: true });
}

await runProbeSideEffectContract();
await runLargeMessageContract();
await runConditionalToolMatrix();
await runProviderMatrix();
await runClientPipeCloseContract();
await runSignalContract();

console.log(
  failures === 0
    ? "\nall v2 protocol smoke checks passed"
    : `\n${failures} v2 protocol smoke check(s) failed`,
);
process.exitCode = failures === 0 ? 0 : 1;
