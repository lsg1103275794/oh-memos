// Legacy MCP stdio contract smoke.
//
// This intentionally uses raw JSON-RPC instead of the SDK client so it freezes
// the initialize-era wire behavior independently of client package changes.
import { spawn } from "node:child_process";
import { once } from "node:events";
import { existsSync, readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { scratchDir } from "./_scratch.mjs";

const LEGACY_PROTOCOL_VERSION = "2025-11-25";
const DIST_ENTRY = fileURLToPath(new URL("../dist/index.js", import.meta.url));
const PACKAGE_JSON = JSON.parse(
  readFileSync(new URL("../package.json", import.meta.url), "utf8")
);

const EXPECTED_TOOL_ORDER = [
  "memos_context_resume",
  "memos_search",
  "memos_think",
  "memos_export_wiki",
  "memos_import_wiki",
  "memos_save",
  "memos_list_v2",
  "memos_get",
  "memos_suggest",
  "memos_distill_skill",
  "memos_list_skill_candidates",
  "memos_review_skill_candidate",
  "memos_install_skill_candidate",
  "memos_graph",
  "memos_admin",
  "memos_canvas",
  "memos_delete",
];

const EXPECTED_ANNOTATIONS = {
  memos_context_resume: { readOnlyHint: true, openWorldHint: false },
  memos_search: { readOnlyHint: true, openWorldHint: true },
  memos_think: { readOnlyHint: true, openWorldHint: true },
  memos_export_wiki: { readOnlyHint: false, openWorldHint: false },
  memos_import_wiki: { readOnlyHint: false, openWorldHint: true },
  memos_save: { readOnlyHint: false, openWorldHint: true },
  memos_list_v2: { readOnlyHint: true, openWorldHint: false },
  memos_get: { readOnlyHint: true, openWorldHint: false },
  memos_suggest: { readOnlyHint: true, openWorldHint: false },
  memos_distill_skill: { readOnlyHint: false, openWorldHint: true },
  memos_list_skill_candidates: { readOnlyHint: true, openWorldHint: false },
  memos_review_skill_candidate: { readOnlyHint: false, openWorldHint: false },
  memos_install_skill_candidate: { readOnlyHint: false, openWorldHint: false },
  memos_graph: { readOnlyHint: true, openWorldHint: true },
  memos_admin: { readOnlyHint: false, openWorldHint: false },
  memos_canvas: { readOnlyHint: false, openWorldHint: false },
  memos_delete: { readOnlyHint: false, openWorldHint: false },
};

let failures = 0;

function check(label, condition, detail = "") {
  if (condition) {
    console.log("  ok   " + label);
    return;
  }
  console.log("  FAIL " + label + (detail ? " - " + detail : ""));
  failures += 1;
}

function textContent(response) {
  return (
    response.result?.content?.map((item) => item.text).join("\n") ??
    JSON.stringify(response.error ?? response)
  );
}

function baseEnv(root, cube, overrides = {}) {
  return {
    ...process.env,
    MEMOS_USER: "protocol-smoke",
    MEMOS_DEFAULT_CUBE: cube,
    MEMOS_CUBES_DIR: root,
    MEMOS_ENV_FILE: join(root, "missing.env"),
    MEMOS_LITE_EMBED: "off",
    MEMOS_ENABLE_DELETE: "false",
    NEO4J_HTTP_URL: "",
    ...overrides,
  };
}

class LegacyStdioClient {
  constructor(label, env) {
    this.label = label;
    this.stderr = "";
    this.stdoutBuffer = "";
    this.pending = new Map();
    this.nextId = 1;

    this.child = spawn(process.execPath, [DIST_ENTRY], {
      stdio: ["pipe", "pipe", "pipe"],
      env,
    });

    this.child.stdout.setEncoding("utf8");
    this.child.stderr.setEncoding("utf8");
    this.child.stdout.on("data", (chunk) => this.handleStdout(chunk));
    this.child.stderr.on("data", (chunk) => {
      this.stderr += chunk;
    });
    this.child.stdin.on("error", () => {
      // A closing child can reject a final write; pending RPCs report the exit.
    });
    this.child.on("exit", (code, signal) => {
      const detail =
        this.label +
        " server exited before responding (code=" +
        String(code) +
        ", signal=" +
        String(signal) +
        ")";
      for (const pending of this.pending.values()) {
        clearTimeout(pending.timer);
        pending.reject(new Error(detail));
      }
      this.pending.clear();
    });
  }

  handleStdout(chunk) {
    this.stdoutBuffer += chunk;
    let newline = this.stdoutBuffer.indexOf("\n");
    while (newline !== -1) {
      const line = this.stdoutBuffer.slice(0, newline).trim();
      this.stdoutBuffer = this.stdoutBuffer.slice(newline + 1);
      if (line) {
        try {
          const message = JSON.parse(line);
          const pending = this.pending.get(String(message.id));
          if (pending) {
            clearTimeout(pending.timer);
            this.pending.delete(String(message.id));
            pending.resolve(message);
          }
        } catch {
          this.stderr += "\n[non-json stdout] " + line;
        }
      }
      newline = this.stdoutBuffer.indexOf("\n");
    }
  }

  rpc(method, params) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(String(id));
        reject(
          new Error(
            this.label +
              " timed out on " +
              method +
              "\nstderr:\n" +
              this.stderr.slice(0, 1600)
          )
        );
      }, 10000);

      this.pending.set(String(id), { resolve, reject, timer });
      this.child.stdin.write(
        JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n"
      );
    });
  }

  notify(method, params = {}) {
    this.child.stdin.write(
      JSON.stringify({ jsonrpc: "2.0", method, params }) + "\n"
    );
  }

  async initialize() {
    const response = await this.rpc("initialize", {
      protocolVersion: LEGACY_PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: { name: "oh-memos-protocol-smoke", version: "0" },
    });
    this.notify("notifications/initialized");
    return response;
  }

  async close() {
    if (this.child.exitCode !== null) return;

    this.child.stdin.end();
    this.child.kill();
    await Promise.race([
      once(this.child, "exit"),
      new Promise((resolve) => setTimeout(resolve, 1500)),
    ]);
    if (this.child.exitCode === null) this.child.kill();
  }
}

function validateInitialize(label, response) {
  check(
    label + " negotiates the 2025-era protocol",
    response.result?.protocolVersion === LEGACY_PROTOCOL_VERSION,
    JSON.stringify(response)
  );
  check(
    label + " advertises package serverInfo",
    response.result?.serverInfo?.name === PACKAGE_JSON.name &&
      response.result?.serverInfo?.version === PACKAGE_JSON.version,
    JSON.stringify(response.result?.serverInfo)
  );
  check(
    label + " advertises tools capability",
    typeof response.result?.capabilities?.tools === "object",
    JSON.stringify(response.result?.capabilities)
  );
}

function validateTools(label, tools, expectedNames) {
  const names = tools.map((tool) => tool.name);
  check(
    label + " keeps deterministic tool order",
    JSON.stringify(names) === JSON.stringify(expectedNames),
    names.join(",")
  );

  for (const name of expectedNames) {
    const actual = tools.find((tool) => tool.name === name)?.annotations;
    const expected = EXPECTED_ANNOTATIONS[name];
    check(
      label + " keeps annotations for " + name,
      actual?.readOnlyHint === expected.readOnlyHint &&
        actual?.openWorldHint === expected.openWorldHint,
      JSON.stringify(actual)
    );
  }
}

async function runLiteContracts() {
  console.log("\nLite legacy contract");
  const root = scratchDir("oh-memos-protocol-lite-");
  const cube = "protocol_lite_cube";
  const client = new LegacyStdioClient(
    "lite",
    baseEnv(root, cube, {
      MEMOS_MODE: "lite",
      MEMOS_PROVIDER: "local",
      MEMOS_URL: "",
    })
  );

  try {
    const initialized = await client.initialize();
    validateInitialize("Lite", initialized);

    const listed = await client.rpc("tools/list", {});
    const tools = listed.result?.tools ?? [];
    validateTools("Lite default", tools, EXPECTED_TOOL_ORDER.slice(0, -1));

    const objectContent = "Phase 0 object arguments remain compatible";
    const objectSave = textContent(
      await client.rpc("tools/call", {
        name: "memos_save",
        arguments: {
          cube_id: cube,
          content: objectContent,
          memory_type: "DECISION",
        },
      })
    );
    check(
      "object arguments return the legacy save text",
      objectSave.includes("Memory saved as [DECISION]"),
      objectSave.slice(0, 240)
    );

    const stringContent = "Phase 0 string arguments remain compatible";
    const stringSave = textContent(
      await client.rpc("tools/call", {
        name: "memos_save",
        arguments: JSON.stringify({
          cube_id: cube,
          content: stringContent,
          memory_type: "DECISION",
        }),
      })
    );
    check(
      "stringified arguments are normalized before validation",
      stringSave.includes("Memory saved as [DECISION]"),
      stringSave.slice(0, 240)
    );

    const search = textContent(
      await client.rpc("tools/call", {
        name: "memos_search",
        arguments: {
          cube_id: cube,
          query: "Phase 0 arguments compatible",
          top_k: 10,
        },
      })
    );
    check(
      "Lite search returns both representative writes",
      search.includes(objectContent) && search.includes(stringContent),
      search.slice(0, 360)
    );

    const unknownKey = await client.rpc("tools/call", {
      name: "memos_suggest",
      arguments: {
        context: "protocol migration",
        extra_contract_key: "ignored",
      },
    });
    check(
      "unknown argument keys remain non-fatal",
      Boolean(unknownKey.result) && !unknownKey.error,
      JSON.stringify(unknownKey)
    );

    const invalid = await client.rpc("tools/call", {
      name: "memos_save",
      arguments: { cube_id: cube, content: "missing memory type" },
    });
    check(
      "invalid arguments remain a tool error",
      invalid.result?.isError === true || Boolean(invalid.error),
      JSON.stringify(invalid)
    );

    const liteBoundary = textContent(
      await client.rpc("tools/call", {
        name: "memos_graph",
        arguments: { cube_id: cube, mode: "related", query: "protocol" },
      })
    );
    check(
      "Full-only calls keep the Lite boundary text",
      liteBoundary.includes("Lite mode") &&
        liteBoundary.includes("MEMOS_MODE=full"),
      liteBoundary.slice(0, 300)
    );

    const storePath = join(root, cube, "memories.jsonl");
    check("Lite writes remain JSONL-backed", existsSync(storePath), storePath);
    if (existsSync(storePath)) {
      const records = readFileSync(storePath, "utf8")
        .trim()
        .split("\n")
        .filter(Boolean)
        .map((line) => JSON.parse(line));
      check(
        "Lite JSONL keeps both DECISION records",
        records.length === 2 &&
          records.every((record) => record.metadata?.type === "DECISION"),
        JSON.stringify(records)
      );
    }
  } catch (error) {
    check(
      "Lite harness completes",
      false,
      String(error) + "\nstderr:\n" + client.stderr.slice(0, 1600)
    );
  } finally {
    await client.close();
    rmSync(root, { recursive: true, force: true });
  }
}

async function runConditionalDeleteContract() {
  console.log("\nConditional tool contract");
  const root = scratchDir("oh-memos-protocol-delete-");
  const cube = "protocol_delete_cube";
  const client = new LegacyStdioClient(
    "delete-enabled",
    baseEnv(root, cube, {
      MEMOS_MODE: "lite",
      MEMOS_PROVIDER: "local",
      MEMOS_URL: "",
      MEMOS_ENABLE_DELETE: "true",
    })
  );

  try {
    validateInitialize("Delete-enabled", await client.initialize());
    const listed = await client.rpc("tools/list", {});
    validateTools("Delete-enabled", listed.result?.tools ?? [], EXPECTED_TOOL_ORDER);

    const deleteResult = textContent(
      await client.rpc("tools/call", {
        name: "memos_delete",
        arguments: { memory_id: "not-used-in-lite", cube_id: cube },
      })
    );
    check(
      "delete-enabled tool is callable without mutating the Lite fixture",
      deleteResult.includes("Lite mode: memos_delete is unavailable"),
      deleteResult
    );
  } catch (error) {
    check(
      "delete-enabled harness completes",
      false,
      String(error) + "\nstderr:\n" + client.stderr.slice(0, 1600)
    );
  } finally {
    await client.close();
    rmSync(root, { recursive: true, force: true });
  }
}

async function runFullContracts() {
  console.log("\nFull legacy contract");
  const root = scratchDir("oh-memos-protocol-full-");
  const cube = "protocol_full_cube";
  const client = new LegacyStdioClient(
    "full",
    baseEnv(root, cube, {
      MEMOS_MODE: "full",
      MEMOS_PROVIDER: "api",
      MEMOS_URL: "http://127.0.0.1:1",
    })
  );

  try {
    validateInitialize("Full", await client.initialize());
    const listed = await client.rpc("tools/list", {});
    validateTools("Full default", listed.result?.tools ?? [], EXPECTED_TOOL_ORDER.slice(0, -1));

    const capabilities = textContent(
      await client.rpc("tools/call", {
        name: "memos_admin",
        arguments: { action: "capabilities" },
      })
    );
    check(
      "Full capabilities keep the representative success text",
      capabilities.includes("**Mode**: full") &&
        capabilities.includes("Full exposes API"),
      capabilities.slice(0, 300)
    );

    const unreachable = textContent(
      await client.rpc("tools/call", {
        name: "memos_admin",
        arguments: {
          action: "create_user",
          user_id: "protocol-smoke-unreachable",
        },
      })
    );
    check(
      "Full API failure keeps the actionable legacy text",
      unreachable.includes("[API_ERROR]") &&
        unreachable.includes("health/detail"),
      unreachable.slice(0, 360)
    );
  } catch (error) {
    check(
      "Full harness completes",
      false,
      String(error) + "\nstderr:\n" + client.stderr.slice(0, 1600)
    );
  } finally {
    await client.close();
    rmSync(root, { recursive: true, force: true });
  }
}

if (!existsSync(DIST_ENTRY)) {
  console.error("dist/index.js is missing; run npm run build first.");
  process.exit(2);
}

await runLiteContracts();
await runConditionalDeleteContract();
await runFullContracts();

console.log(
  failures === 0
    ? "\nall legacy protocol smoke checks passed"
    : "\n" + failures + " protocol smoke check(s) failed"
);
process.exitCode = failures === 0 ? 0 : 1;
