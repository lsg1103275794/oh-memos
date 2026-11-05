#!/usr/bin/env node
/**
 * Opt-in, fail-open session checkpoint capture for Claude hooks.
 *
 * It never captures PostToolUse output. PreCompact/Stop payloads are reduced to
 * bounded text, sent through the redacting /memories API, and deduplicated by
 * session + event + content hash in the OS temp directory.
 */
const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const http = require("http");
const https = require("https");

const env = process.env;
const enabled = env.MEMOS_MODE?.toLowerCase() !== "lite" && env.MEMOS_AUTO_CAPTURE?.toLowerCase() === "true";
const maxChars = Math.max(500, Math.min(Number(env.MEMOS_AUTO_CAPTURE_MAX_CHARS || 6000), 12000));
const timeoutMs = Math.max(500, Math.min(Number(env.MEMOS_AUTO_CAPTURE_TIMEOUT_MS || 2500), 5000));

function output(message) {
  process.stdout.write(JSON.stringify({ continue: true, suppressOutput: true, ...(message ? { message } : {}) }));
}
/**
 * Cube id for a project directory. Same rule as detectCubeFromPath in
 * mcp-server-node/src/keyword-enhancer.ts; hook-context.test.ts keeps the
 * copies in the hooks equal to it.
 */
function deriveCubeId(cwd) {
  const segments = String(cwd).replace(/\\/g, "/").replace(/\/$/, "").split("/");
  let folder = segments[segments.length - 1] || "";
  if (/^[A-Za-z]:$/.test(folder)) folder = segments[segments.length - 2] || "default";
  if (!folder) return "default_cube";
  let id = folder.toLowerCase().replace(/[-.\s]+/g, "_").replace(/[^a-z0-9_]/g, "");
  if (/^\d/.test(id)) id = "_" + id;
  if (!id.endsWith("_cube")) id += "_cube";
  return id || "default_cube";
}
function bounded(value) {
  return String(value || "").replace(/\r/g, "").replace(/\0/g, "").trim().slice(-maxChars);
}
function readInput() {
  return new Promise((resolve) => {
    let input = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => { input += chunk; if (input.length > 20000) process.stdin.destroy(); });
    process.stdin.on("end", () => { try { resolve(JSON.parse(input || "{}")); } catch { resolve({}); } });
    setTimeout(() => resolve({}), Math.min(timeoutMs, 250));
  });
}
function request(url, body) {
  return new Promise((resolve) => {
    try {
      const target = new URL(url);
      const transport = target.protocol === "https:" ? https : http;
      const req = transport.request(target, { method: "POST", timeout: timeoutMs, headers: { "Content-Type": "application/json" } }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        let payload = {};
        try { payload = JSON.parse(Buffer.concat(chunks).toString() || "{}"); } catch {}
        const acknowledged = res.statusCode >= 200 && res.statusCode < 300 && (payload.code === 200 || payload.data?.queued === true || payload.data?.memory_ids?.length > 0);
        resolve(acknowledged);
      });
      });
      req.on("error", () => resolve(false));
      req.on("timeout", () => { req.destroy(); resolve(false); });
      req.end(JSON.stringify(body));
    } catch { resolve(false); }
  });
}
async function main() {
  if (!enabled) { output(); return; }
  const event = await readInput();
  const eventName = String(event.hook_event_name || event.event || "pre-compact").toLowerCase();
  const normalizedEvent = eventName.replace(/[-_]/g, "");
  const supported = new Set(["precompact", "stop", "sessionend"]);
  if (!supported.has(normalizedEvent)) { output(); return; }
  if (normalizedEvent === "stop" && event.stop_hook_active === true) { output(); return; }
  const cwd = String(event.cwd || process.cwd());
  const sessionId = String(event.session_id || event.sessionId || "unknown-session");
  const raw = bounded(event.summary || event.context || event.transcript_tail || event.message || event.prompt || "");
  if (!raw || raw.length < 20) { output(); return; }
  const digest = crypto.createHash("sha256").update(`${sessionId}:${eventName}:${raw}`).digest("hex");
  const marker = path.join(os.tmpdir(), `oh-memos-auto-capture-${digest}.done`);
  if (fs.existsSync(marker)) { output(); return; }
  const baseUrl = String(env.MEMOS_URL || "http://127.0.0.1:18000").replace(/\/$/, "");
  const user = env.MEMOS_USER || "dev_user";
  const cube = env.MEMOS_DEFAULT_CUBE || deriveCubeId(cwd);
  const body = {
    user_id: user,
    mem_cube_id: cube,
    memory_content: `[PROGRESS] Session checkpoint (${eventName}):\n${raw}`,
    memory_type: "PROGRESS",
    tags: ["auto-capture", "session"],
    confidence: 0.25,
    source: "conversation",
    session_id: sessionId,
    source_ref: `claude-hook:${sessionId}:${eventName}:${digest.slice(0, 12)}`,
  };
  const ok = await request(`${baseUrl}/memories`, body);
  if (ok) { try { fs.writeFileSync(marker, new Date().toISOString(), { flag: "wx" }); } catch {} }
  output(ok ? "Session checkpoint captured." : "");
}

if (require.main === module) main().catch(() => output());

module.exports = { deriveCubeId };
