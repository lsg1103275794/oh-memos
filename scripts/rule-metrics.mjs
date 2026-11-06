/**
 * Measures whether rule learning is working, using two numbers:
 *   1. Always-on size: instruction text loaded into every session.
 *   2. Repeat reminders: user prompts that correct the agent or tell it which
 *      tool to use.
 *
 * The patterns are deliberately rough. Every hit is listed so a person can drop
 * false positives; compare windows by reading the hits, not by the rate alone.
 * Prompt excerpts stay on this machine: write --out under an ignored directory.
 *
 * Always-on also covers the oh-memos MCP server (server instructions plus the
 * tools marked to load up front, read from a built dist/index.js) and the
 * skill listing (each skill's name and description). Skill descriptions are
 * counted in full, so that number is an upper bound: clients may shorten them.
 *
 * Usage:
 *   node scripts/rule-metrics.mjs [--days 28] [--project .] [--out file.json]
 *                                 [--history file]... [--instructions file]...
 *                                 [--skills-dir dir]... [--no-skills]
 *                                 [--mcp dist/index.js] [--no-mcp]
 */

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { scratchDir } from "../mcp-server-node/scripts/_scratch.mjs";

const DEFAULT_MCP_ENTRY = fileURLToPath(new URL("../mcp-server-node/dist/index.js", import.meta.url));

const TOOL_WORDS = "memos?|记忆|mcp|skill|技能|子代理|subagent|agent|jcm|jcodemunch|context7|hook|工具|浏览器|playwright";
const CORRECTION = /我说过|说过了|又(去|在|用|忘|没|开始)|怎么又|每次都要|为什么(不用|没用|没有用|没调用|没查)|不应该|以后注意|别再|不要再|别用|不要用/;
const REMINDER = new RegExp(`先(去)?(查|用|调用|使用)[^。\\n]{0,12}(${TOOL_WORDS})|(调用|(?<!可以|尽情)使用|利用)[^。\\n]{0,10}(${TOOL_WORDS})`, "i");
const EMPHASIS = /\b(MUST|ALWAYS|NEVER|CRITICAL|MANDATORY|IMPORTANT)\b|必须|禁止|严禁|务必/g;

// Longer prompts are task briefs that mention tools in passing, not reminders.
const MAX_PROMPT_CHARS = 200;
const EXCERPT_CHARS = 80;

export function classifyPrompt(text) {
  if (text.length > MAX_PROMPT_CHARS) return null;
  if (CORRECTION.test(text)) return "correction";
  if (REMINDER.test(text)) return "reminder";
  return null;
}

/** Reads Claude Code ({display, timestamp ms}) and Codex ({text, ts s}) history. */
export function loadPrompts(paths) {
  const seen = new Set();
  const prompts = [];
  for (const path of paths) {
    if (!existsSync(path)) continue;
    for (const line of readFileSync(path, "utf8").split("\n")) {
      let entry;
      try {
        entry = JSON.parse(line);
      } catch {
        continue;
      }
      const text = String(entry.display ?? entry.text ?? "").trim();
      const at = entry.timestamp ? Number(entry.timestamp) : Number(entry.ts) * 1000;
      // Per day, not per text: the same reminder on another day is the signal.
      const key = `${Math.floor(at / 864e5)}:${text}`;
      if (!text || text.startsWith("/") || !at || seen.has(key)) continue;
      seen.add(key);
      prompts.push({ text, at });
    }
  }
  return prompts;
}

export function summarize(prompts, { since, until }) {
  const inWindow = prompts.filter(({ at }) => at >= since && at <= until);
  const hits = inWindow.flatMap(({ text, at }) => {
    const kind = classifyPrompt(text);
    return kind ? [{ kind, at: new Date(at).toISOString().slice(0, 10), text: text.replace(/\s+/g, " ").slice(0, EXCERPT_CHARS) }] : [];
  });
  const corrections = hits.filter(({ kind }) => kind === "correction").length;
  const reminders = hits.length - corrections;
  const per100 = inWindow.length ? Math.round((hits.length / inWindow.length) * 1000) / 10 : 0;
  return { messages: inWindow.length, corrections, reminders, per100, hits };
}

export function estimateTokens(text) {
  const cjk = (text.match(/[一-鿿]/g) ?? []).length;
  return Math.round(cjk + (text.length - cjk) / 4);
}

/** Reads `description:` from SKILL.md frontmatter: plain, quoted, or a folded/literal block. */
function parseSkillDescription(text) {
  const frontmatter = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text)?.[1] ?? "";
  const lines = frontmatter.split(/\r?\n/);
  const at = lines.findIndex((line) => /^description:/.test(line));
  if (at < 0) return "";
  const value = lines[at].slice("description:".length).trim();
  if (value === ">" || value === "|" || value === ">-" || value === "|-") {
    const block = [];
    for (const line of lines.slice(at + 1)) {
      if (line.trim() && !/^\s/.test(line)) break;
      block.push(line.trim());
    }
    return block.filter(Boolean).join(value.startsWith(">") ? " " : "\n");
  }
  const quoted = /^(["'])(.*)\1$/.exec(value);
  return quoted ? quoted[2] : value;
}

/** Name plus description of every skill a client lists; the first directory wins on a duplicate name. */
export function skillListing(dirs) {
  const descriptions = {};
  for (const dir of dirs) {
    if (!existsSync(dir)) continue;
    for (const name of readdirSync(dir)) {
      const file = join(dir, name, "SKILL.md");
      if (name in descriptions || !existsSync(file)) continue;
      descriptions[name] = parseSkillDescription(readFileSync(file, "utf8"));
    }
  }
  const text = Object.entries(descriptions).map(([name, description]) => name + description).join("");
  return { skills: Object.keys(descriptions).length, chars: text.length, tokens: estimateTokens(text), descriptions };
}

/** Server instructions plus the description and schema of each tool marked to load up front. */
export function mcpAlwaysOn(initResult, tools) {
  const instructions = typeof initResult?.instructions === "string" ? initResult.instructions : "";
  const upfront = tools.filter((tool) => tool._meta?.["anthropic/alwaysLoad"] === true);
  const text = instructions + upfront.map((tool) => (tool.description ?? "") + JSON.stringify(tool.inputSchema ?? {})).join("");
  return {
    instructionChars: instructions.length,
    tools: upfront.map((tool) => tool.name),
    chars: text.length,
    tokens: estimateTokens(text),
  };
}

/** Starts a built oh-memos server in Lite mode and measures what it sends at session start. */
export function measureMcp(entry, env = {}) {
  const root = scratchDir("rule-metrics-mcp-");
  const envFile = join(root, "empty.env");
  writeFileSync(envFile, "");
  const child = spawn(process.execPath, [entry], {
    env: {
      ...process.env,
      MEMOS_MODE: "lite",
      MEMOS_PROVIDER: "local",
      MEMOS_URL: "",
      MEMOS_USER: "rule_metrics",
      MEMOS_DEFAULT_CUBE: "rule_metrics_cube",
      MEMOS_CUBES_DIR: root,
      MEMOS_ENV_FILE: envFile,
      ...env,
    },
    stdio: ["pipe", "pipe", "ignore"],
  });
  return new Promise((resolvePromise, reject) => {
    let buffer = "";
    let init;
    let settled = false;
    const finish = (error, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      child.kill();
      try {
        rmSync(root, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
      } catch {}
      error ? reject(error) : resolvePromise(value);
    };
    const timer = setTimeout(() => finish(new Error(`no initialize/tools/list reply from ${entry}`)), 15000);
    const send = (message) => child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", ...message })}\n`);
    child.on("error", (error) => finish(error));
    child.stdout.on("data", (chunk) => {
      buffer += chunk;
      let newline;
      while ((newline = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, newline);
        buffer = buffer.slice(newline + 1);
        let message;
        try {
          message = JSON.parse(line);
        } catch {
          continue;
        }
        if (message.id === 1) {
          init = message.result ?? {};
          send({ method: "notifications/initialized" });
          send({ id: 2, method: "tools/list" });
        } else if (message.id === 2) {
          finish(null, mcpAlwaysOn(init, message.result?.tools ?? []));
        }
      }
    });
    send({
      id: 1,
      method: "initialize",
      params: { protocolVersion: "2025-11-25", capabilities: {}, clientInfo: { name: "rule-metrics", version: "1" } },
    });
  });
}

function measureInstructions(paths) {
  const files = paths.filter(existsSync).map((path) => {
    const text = readFileSync(path, "utf8");
    return { path, chars: text.length, tokens: estimateTokens(text), emphasis: (text.match(EMPHASIS) ?? []).length };
  });
  const total = (key) => files.reduce((sum, file) => sum + file[key], 0);
  return { files, chars: total("chars"), tokens: total("tokens"), emphasis: total("emphasis") };
}

function defaultInstructionFiles(project) {
  const claudeHome = join(homedir(), ".claude");
  const rulesDir = join(claudeHome, "rules");
  const rules = existsSync(rulesDir)
    ? readdirSync(rulesDir).filter((name) => name.endsWith(".md")).map((name) => join(rulesDir, name))
    : [];
  return [join(claudeHome, "CLAUDE.md"), join(claudeHome, "RTK.md"), ...rules, join(project, "AGENTS.md"), join(project, "CLAUDE.md")];
}

async function main() {
  const { values } = parseArgs({
    options: {
      days: { type: "string", default: "28" },
      project: { type: "string", default: "." },
      out: { type: "string" },
      history: { type: "string", multiple: true },
      instructions: { type: "string", multiple: true },
      "skills-dir": { type: "string", multiple: true },
      "no-skills": { type: "boolean", default: false },
      mcp: { type: "string" },
      "no-mcp": { type: "boolean", default: false },
    },
  });
  const days = Number(values.days);
  if (!Number.isFinite(days) || days <= 0) throw new Error(`--days must be a positive number, got ${values.days}`);

  const codexHome = process.env.CODEX_HOME ?? join(homedir(), ".codex");
  const history = values.history ?? [join(homedir(), ".claude", "history.jsonl"), join(codexHome, "history.jsonl")];
  const until = Date.now();
  const report = {
    measuredAt: new Date(until).toISOString(),
    days,
    sources: history.filter(existsSync),
    reminders: summarize(loadPrompts(history), { since: until - days * 864e5, until }),
    alwaysOn: measureInstructions(values.instructions ?? defaultInstructionFiles(resolve(values.project))),
  };

  if (!values["no-skills"]) {
    const { descriptions: _omitted, ...listing } = skillListing(values["skills-dir"] ?? [join(homedir(), ".claude", "skills")]);
    report.skills = listing;
  }
  const mcpEntry = values.mcp ?? DEFAULT_MCP_ENTRY;
  if (!values["no-mcp"]) {
    if (existsSync(mcpEntry)) report.mcp = { entry: mcpEntry, ...(await measureMcp(mcpEntry)) };
    else console.log(`MCP server not measured: ${mcpEntry} not found (run npm run build in mcp-server-node)`);
  }

  if (values.out) {
    mkdirSync(dirname(resolve(values.out)), { recursive: true });
    writeFileSync(values.out, `${JSON.stringify(report, null, 2)}\n`);
  }

  const { reminders, alwaysOn, sources, mcp, skills } = report;
  console.log(`Always-on: ${alwaysOn.files.length} files, ${alwaysOn.chars} chars, ~${alwaysOn.tokens} tokens, ${alwaysOn.emphasis} emphasis words`);
  for (const file of alwaysOn.files) console.log(`  ${String(file.tokens).padStart(5)}  ${file.path}`);
  if (mcp) console.log(`MCP server: ${mcp.instructionChars} instruction chars + ${mcp.tools.length} always-loaded tool(s) [${mcp.tools.join(", ")}], ~${mcp.tokens} tokens`);
  if (skills) console.log(`Skill listing: ${skills.skills} skills, ${skills.chars} chars, ~${skills.tokens} tokens (upper bound)`);
  console.log(`Total always-on: ~${alwaysOn.tokens + (mcp?.tokens ?? 0) + (skills?.tokens ?? 0)} tokens`);
  console.log(`\nLast ${days} days from ${sources.length} history file(s): ${reminders.messages} messages, ${reminders.corrections} corrections, ${reminders.reminders} reminders, ${reminders.per100} per 100`);
  for (const hit of reminders.hits) console.log(`  ${hit.at} ${hit.kind.padEnd(10)} ${hit.text}`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}
