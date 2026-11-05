import { describe, expect, it } from "vitest";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { classifyPrompt, estimateTokens, loadPrompts, summarize } from "../../scripts/rule-metrics.mjs";

describe("classifyPrompt", () => {
  it.each([
    ["AI在选择记忆的时候又去手写Write了", "correction"],
    ["我说过不要这样", "correction"],
    ["别再用 grep 了", "correction"],
    ["为什么不用 memos", "correction"],
    ["那两份repo不应该去向别的项目的 以后注意些", "correction"],
    ["你继续codex的edge 任务 先查memos 记忆", "reminder"],
    ["你先查找记忆中关于Edge的cookie还原任务细节 并继续", "reminder"],
    ["调用skill先做个plan 然后实现", "reminder"],
    ["开始测试前端 利用MCP浏览器助手", "reminder"],
  ])("%s -> %s", (text, kind) => {
    expect(classifyPrompt(text)).toBe(kind);
  });

  it.each([
    "修复登录页的样式",
    "是",
    "最好用的skills是什么",
    "不用停，继续跑",
    "万一社区有64G内存开发对于这种也不会在意",
    "你可以使用任何你觉得合适的工具，做出最惊艳的效果",
    "你可以尽情使用所有你想要的工具",
  ])("ignores %s", (text) => {
    expect(classifyPrompt(text)).toBeNull();
  });

  it("ignores long task briefs that only mention tools in passing", () => {
    const brief = `帮我做一条动画，你可以使用任何你觉得合适的工具，不要使用已有的skill。${"背景".repeat(120)}`;
    expect(classifyPrompt(brief)).toBeNull();
  });
});

describe("loadPrompts", () => {
  it("reads both history formats, drops slash commands, bad lines and duplicates", () => {
    const dir = mkdtempSync(join(tmpdir(), "rule-metrics-"));
    try {
      const claude = join(dir, "claude.jsonl");
      const codex = join(dir, "codex.jsonl");
      writeFileSync(
        claude,
        [
          JSON.stringify({ display: "先查memos", timestamp: 2000 }),
          JSON.stringify({ display: "/mcp", timestamp: 2000 }),
          "not json",
        ].join("\n"),
      );
      writeFileSync(
        codex,
        [
          JSON.stringify({ text: "先查memos", ts: 3 }),
          JSON.stringify({ text: "继续", ts: 5 }),
        ].join("\n"),
      );
      expect(loadPrompts([claude, codex, join(dir, "missing.jsonl")])).toEqual([
        { text: "先查memos", at: 2000 },
        { text: "继续", at: 5000 },
      ]);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe("loadPrompts repeats", () => {
  it("keeps the same reminder on different days, since repeats are what we measure", () => {
    const dir = mkdtempSync(join(tmpdir(), "rule-metrics-"));
    try {
      const file = join(dir, "history.jsonl");
      const day = 864e5;
      writeFileSync(
        file,
        [
          JSON.stringify({ display: "先查memos", timestamp: day }),
          JSON.stringify({ display: "先查memos", timestamp: day + 1000 }),
          JSON.stringify({ display: "先查memos", timestamp: 3 * day }),
        ].join("\n"),
      );
      expect(loadPrompts([file]).map(({ at }) => at)).toEqual([day, 3 * day]);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe("summarize", () => {
  it("counts only the window and truncates listed hits to 80 characters", () => {
    const long = `先查memos ${"x".repeat(100)}`;
    const result = summarize(
      [
        { text: "我说过了", at: 500 },
        { text: long, at: 1500 },
        { text: "继续", at: 1600 },
        { text: "又忘了", at: 2500 },
      ],
      { since: 1000, until: 2000 },
    );
    expect(result.messages).toBe(2);
    expect(result.corrections).toBe(0);
    expect(result.reminders).toBe(1);
    expect(result.per100).toBe(50);
    expect(result.hits).toHaveLength(1);
    expect(result.hits[0].text).toHaveLength(80);
  });

  it("reports zero per100 for an empty window", () => {
    expect(summarize([], { since: 0, until: 1 }).per100).toBe(0);
  });
});

describe("estimateTokens", () => {
  it("counts CJK characters as one token and other text as a quarter", () => {
    expect(estimateTokens("记忆abcd")).toBe(3);
  });
});
