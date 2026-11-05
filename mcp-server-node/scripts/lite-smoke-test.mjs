// Standalone Lite-mode smoke test over real MCP stdio.
// No FastAPI, Neo4j, Qdrant, or Ollama is required.
import { spawn } from "node:child_process";
import { existsSync, readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { scratchDir } from "./_scratch.mjs";

const root = scratchDir("lite-mcp-smoke-");
const cube = "lite_smoke_cube";
const child = spawn(process.execPath, ["dist/index.js"], {
  stdio: ["pipe", "pipe", "pipe"],
  env: {
    ...process.env,
    MEMOS_MODE: "lite",
    MEMOS_PROVIDER: "local",
    MEMOS_USER: "lite-smoke",
    MEMOS_DEFAULT_CUBE: cube,
    MEMOS_CUBES_DIR: root,
    MEMOS_ENV_FILE: join(root, "missing.env"),
    MEMOS_LITE_EMBED: "off",
    MEMOS_URL: "",
    NEO4J_HTTP_URL: "",
  },
});

let stderr = "";
child.stderr.on("data", (data) => {
  stderr += data.toString();
});

let buffer = "";
const pending = new Map();
child.stdout.on("data", (chunk) => {
  buffer += chunk.toString();
  let newline;
  while ((newline = buffer.indexOf("\n")) !== -1) {
    const line = buffer.slice(0, newline).trim();
    buffer = buffer.slice(newline + 1);
    if (!line) continue;
    try {
      const message = JSON.parse(line);
      const resolve = pending.get(message.id);
      if (resolve) {
        pending.delete(message.id);
        resolve(message);
      }
    } catch {
      // MCP stdout should be JSON-RPC; leave malformed lines for the timeout/error.
    }
  }
});

let nextId = 1;
function rpc(method, params) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`timeout on ${method}`));
    }, 10_000);
    pending.set(id, (message) => {
      clearTimeout(timer);
      resolve(message);
    });
    child.stdin.write(
      `${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`,
    );
  });
}

function text(response) {
  return (
    response.result?.content?.map((content) => content.text).join("\n") ??
    JSON.stringify(response.error ?? response)
  );
}

let failures = 0;
function check(label, condition, detail = "") {
  if (condition) console.log(`  ok   ${label}`);
  else {
    console.log(`  FAIL ${label}${detail ? ` — ${detail}` : ""}`);
    failures += 1;
  }
}

try {
  await rpc("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "lite-smoke", version: "0" },
  });
  child.stdin.write(
    `${JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" })}\n`,
  );

  const tools = await rpc("tools/list", {});
  const names = (tools.result?.tools ?? []).map((tool) => tool.name);
  check(
    "MCP server advertises memos_save",
    names.includes("memos_save"),
    names.join(","),
  );
  check(
    "MCP server advertises memos_search",
    names.includes("memos_search"),
    names.join(","),
  );

  const save = text(
    await rpc("tools/call", {
      name: "memos_save",
      arguments: {
        cube_id: cube,
        content: "Lite mode persists without a backend",
        memory_type: "DECISION",
      },
    }),
  );
  check(
    "save succeeds without API",
    save.includes("Memory saved as [DECISION]"),
    save.slice(0, 240),
  );

  const search = text(
    await rpc("tools/call", {
      name: "memos_search",
      arguments: { cube_id: cube, query: "without a backend", top_k: 5 },
    }),
  );
  check(
    "search finds the local memory",
    search.includes("Lite mode persists without a backend"),
    search.slice(0, 240),
  );

  const store = join(root, cube, "memories.jsonl");
  check("memory is persisted as JSONL", existsSync(store), store);
  if (existsSync(store)) {
    const record = JSON.parse(readFileSync(store, "utf8").trim());
    check(
      "JSONL record keeps its type",
      record.metadata?.type === "DECISION",
      JSON.stringify(record),
    );
  }

  // 访问追踪闭环。这段刻意走真实 MCP 调用：memos_get 记账与 search 读取统计
  // 都发生在 handler 里，单测到不了那一层 —— 变异验证确认过，切断这两处接线时
  // 全部 vitest 仍然通过。这里是唯一能守住它们的地方。
  let accessedId = "";
  if (existsSync(store)) {
    accessedId = JSON.parse(readFileSync(store, "utf8").trim()).id ?? "";
  }
  check("stored record exposes an id", Boolean(accessedId), accessedId);

  if (accessedId) {
    const got = text(
      await rpc("tools/call", {
        name: "memos_get",
        arguments: { cube_id: cube, memory_id: accessedId },
      }),
    );
    check(
      "memos_get returns the memory",
      got.includes("Memory Details"),
      got.slice(0, 240),
    );

    const accessLog = join(root, cube, "access-log.jsonl");
    check("memos_get records an access", existsSync(accessLog), accessLog);
    if (existsSync(accessLog)) {
      const entry = JSON.parse(
        readFileSync(accessLog, "utf8").trim().split("\n")[0],
      );
      check(
        "access log names the fetched id",
        Array.isArray(entry.ids) && entry.ids.includes(accessedId),
        JSON.stringify(entry),
      );
    }

    // search 必须把侧车统计喂进打分 —— 命中项的 access_count 应当出现在结果里。
    const reranked = text(
      await rpc("tools/call", {
        name: "memos_search",
        arguments: {
          cube_id: cube,
          query: "without a backend",
          top_k: 5,
          compact: false,
        },
      }),
    );
    // 断言必须只认 access_count —— 早先写成 `... || 找到了这条记忆` 时，
    // 第二个条件恒真，切断 accessStats 接线也照样通过。变异验证暴露了这一点。
    check(
      "search reflects recorded access",
      /access_count\s+1/.test(reranked),
      reranked.slice(0, 400),
    );
  }

  const graph = text(
    await rpc("tools/call", {
      name: "memos_graph",
      arguments: { cube_id: cube, mode: "related", query: "backend" },
    }),
  );
  check(
    "Full-only graph call explains Lite boundary",
    graph.includes("Lite mode") && graph.includes("MEMOS_MODE=full"),
    graph.slice(0, 240),
  );
} catch (error) {
  console.log(`  FAIL harness error — ${error.message}`);
  console.log(`  stderr — ${stderr.slice(0, 800)}`);
  failures += 1;
} finally {
  child.kill();
  rmSync(root, { recursive: true, force: true });
}

console.log(
  failures === 0
    ? "\nall Lite smoke checks passed"
    : `\n${failures} check(s) failed`,
);
process.exit(failures === 0 ? 0 : 1);
