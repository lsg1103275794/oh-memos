import { spawn } from "node:child_process";
import { createServer, type IncomingMessage, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { createRequire } from "node:module";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { detectCubeFromPath } from "./keyword-enhancer.js";

const require = createRequire(import.meta.url);
const hooksDir = join(process.cwd(), "..", "project-memory", "hooks", "node");
const contextInject = join(hooksDir, "oh_memos_context_inject.js");
const hookModules = ["oh_memos_context_inject.js", "oh_memos_session_start.js", "oh_memos_auto_capture.js"];

// The hooks are copied into user settings one file at a time, so each keeps its
// own copy of the cube rule. This table keeps all copies equal to the server's.
const PATHS = [
  "G:/test/oh-memos",
  "G:\\test\\oh-memos",
  "/mnt/g/Cyber/AudioCraft Studio",
  "/home/me/projects/my-web-app/",
  "/srv/already_cube",
  "/srv/2048-game",
  "/srv/v1.2 release",
  "/srv/café",
  "G:/",
];

describe("hook cube ids", () => {
  for (const file of hookModules) {
    it(`${file} matches detectCubeFromPath`, () => {
      const { deriveCubeId } = require(join(hooksDir, file)) as { deriveCubeId: (cwd: string) => string };
      for (const path of PATHS) expect(deriveCubeId(path), path).toBe(detectCubeFromPath(path));
    });
  }
});

type HookRun = { status: number | null; stdout: string };

function runHook(script: string, payload: unknown, env: Record<string, string>): Promise<HookRun> {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [script], { env: { ...process.env, ...env } });
    let stdout = "";
    child.stdout.on("data", (chunk) => (stdout += chunk));
    child.on("error", reject);
    child.on("close", (status) => resolve({ status, stdout }));
    child.stdin.end(JSON.stringify(payload));
  });
}

function readBody(req: IncomingMessage): Promise<Record<string, unknown>> {
  return new Promise((resolve) => {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => resolve(JSON.parse(body || "{}")));
  });
}

let server: Server | undefined;
afterEach(() => new Promise<void>((resolve) => (server ? server.close(() => resolve()) : resolve())));

async function fakeSearchApi(memories: unknown[]): Promise<{ url: string; requests: Record<string, unknown>[] }> {
  const requests: Record<string, unknown>[] = [];
  server = createServer(async (req, res) => {
    requests.push(await readBody(req));
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({
      message: "Search completed successfully",
      data: { text_mem: [{ cube_id: "x", memories }] },
    }));
  });
  await new Promise<void>((resolve) => server!.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as AddressInfo;
  return { url: `http://127.0.0.1:${port}`, requests };
}

const readEvent = {
  hook_event_name: "PreToolUse",
  tool_name: "Read",
  tool_input: { file_path: "G:/test/oh-memos/mcp-server-node/src/keyword-enhancer.ts" },
  cwd: "G:/test/oh-memos",
};

describe("context_inject hook", () => {
  it("sends found memories to the model through hookSpecificOutput.additionalContext", async () => {
    const api = await fakeSearchApi([{ memory: "detectCubeFromPath strips the drive letter", metadata: { key: "cube rule" } }]);
    const { status, stdout } = await runHook(contextInject, readEvent, { MEMOS_URL: api.url, MEMOS_USER: "hook_user" });

    expect(status).toBe(0);
    const out = JSON.parse(stdout);
    expect(out.hookSpecificOutput.hookEventName).toBe("PreToolUse");
    expect(out.hookSpecificOutput.additionalContext).toContain("cube rule: detectCubeFromPath strips the drive letter");
    expect(out).not.toHaveProperty("additionalContext");
    expect(api.requests[0]).toMatchObject({ user_id: "hook_user", install_cube_ids: ["oh_memos_cube"] });
  });

  it("prints nothing when no memory matches", async () => {
    const api = await fakeSearchApi([]);
    const { status, stdout } = await runHook(contextInject, readEvent, { MEMOS_URL: api.url });
    expect(status).toBe(0);
    expect(stdout.trim()).toBe("");
  });

  it("prints nothing and exits 0 when the API is unreachable", async () => {
    const { status, stdout } = await runHook(contextInject, readEvent, { MEMOS_URL: "http://127.0.0.1:1" });
    expect(status).toBe(0);
    expect(stdout.trim()).toBe("");
  });
});
