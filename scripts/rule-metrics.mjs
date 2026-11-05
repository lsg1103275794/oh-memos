#!/usr/bin/env node
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
 * Usage:
 *   node scripts/rule-metrics.mjs [--days 28] [--project .] [--out file.json]
 *                                 [--history file]... [--instructions file]...
 */

import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

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

function main() {
  const { values } = parseArgs({
    options: {
      days: { type: "string", default: "28" },
      project: { type: "string", default: "." },
      out: { type: "string" },
      history: { type: "string", multiple: true },
      instructions: { type: "string", multiple: true },
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

  if (values.out) {
    mkdirSync(dirname(resolve(values.out)), { recursive: true });
    writeFileSync(values.out, `${JSON.stringify(report, null, 2)}\n`);
  }

  const { reminders, alwaysOn, sources } = report;
  console.log(`Always-on: ${alwaysOn.files.length} files, ${alwaysOn.chars} chars, ~${alwaysOn.tokens} tokens, ${alwaysOn.emphasis} emphasis words`);
  for (const file of alwaysOn.files) console.log(`  ${String(file.tokens).padStart(5)}  ${file.path}`);
  console.log(`\nLast ${days} days from ${sources.length} history file(s): ${reminders.messages} messages, ${reminders.corrections} corrections, ${reminders.reminders} reminders, ${reminders.per100} per 100`);
  for (const hit of reminders.hits) console.log(`  ${hit.at} ${hit.kind.padEnd(10)} ${hit.text}`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}
