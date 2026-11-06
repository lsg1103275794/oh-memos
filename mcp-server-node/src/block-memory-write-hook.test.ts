import { describe, expect, it } from "vitest";
import { execFileSync } from "child_process";
import { join } from "path";
import { readdirSync, readFileSync, statSync } from "fs";
import { toolSchemas } from "./tools-registry.js";

const hooksDir = join(process.cwd(), "../project-memory/hooks");
const blockMemoryWrite = join(hooksDir, "node/oh_memos_block_memory_write.js");
const blockMkdir = join(hooksDir, "node/oh_memos_block_mkdir_memory.js");
const template = join(hooksDir, "settings-template.json");

/** Windows paths are built from char codes so no source-level escaping is involved. */
const B = String.fromCharCode(92);
const winPath = (...parts: string[]) => parts.join(B);

type HookResult = { status: number; stdout: string; stderr: string };

function runHook(script: string, payload: unknown): HookResult {
  try {
    const stdout = execFileSync(process.execPath, [script], {
      input: JSON.stringify(payload),
      encoding: "utf8",
    });
    return { status: 0, stdout, stderr: "" };
  } catch (err: unknown) {
    const e = err as { status?: number; stdout?: string; stderr?: string };
    return { status: e.status ?? -1, stdout: e.stdout ?? "", stderr: e.stderr ?? "" };
  }
}

/**
 * A PreToolUse hook blocks the tool call with exit code 2. Exit 1 is a
 * NON-blocking error and lets the write through — the bug this suite pins down.
 */
const BLOCK = 2;

describe("block-memory-write hook", () => {
  const builtinWin = winPath(
    "C:", "Users", "u", ".claude", "projects", "G--work-novel", "memory", "note.md",
  );

  it("blocks a built-in memory write on Windows-style paths", () => {
    const r = runHook(blockMemoryWrite, { tool_input: { file_path: builtinWin } });
    expect(r.status).toBe(BLOCK);
  });

  it("blocks a built-in memory write on POSIX-style paths", () => {
    const r = runHook(blockMemoryWrite, {
      tool_input: { file_path: "/home/u/.claude/projects/proj/memory/note.md" },
    });
    expect(r.status).toBe(BLOCK);
  });

  it("blocks the MEMORY.md index too", () => {
    const r = runHook(blockMemoryWrite, {
      tool_input: { file_path: "C:/Users/u/.claude/projects/p/memory/MEMORY.md" },
    });
    expect(r.status).toBe(BLOCK);
  });

  it("names memos_save and carries cwd through for project_path routing", () => {
    const cwd = winPath("G:", "work", "novel-writer");
    const r = runHook(blockMemoryWrite, { tool_input: { file_path: builtinWin }, cwd });
    expect(r.status).toBe(BLOCK);
    expect(r.stderr).toMatch(/(?<!oh_)memos_save\(/);
    expect(r.stderr).not.toContain("oh_memos_save");
    expect(r.stderr).toContain("novel-writer");
    // Must steer the agent away from retrying, or it burns turns on the same call.
    expect(r.stderr).toMatch(/Do not retry/i);
  });

  it("leaves a project's own project-memory/ alone", () => {
    const r = runHook(blockMemoryWrite, {
      tool_input: { file_path: winPath("G:", "test", "oh-memos", "project-memory", "SKILL.md") },
    });
    expect(r.status).toBe(0);
    expect(JSON.parse(r.stdout).continue).toBe(true);
  });

  it("leaves docs/memory-wiki/ alone", () => {
    const r = runHook(blockMemoryWrite, {
      tool_input: { file_path: winPath("G:", "test", "oh-memos", "docs", "memory-wiki", "index.md") },
    });
    expect(r.status).toBe(0);
  });

  it("ignores non-markdown files inside the built-in memory dir", () => {
    const r = runHook(blockMemoryWrite, {
      tool_input: { file_path: "C:/Users/u/.claude/projects/p/memory/data.json" },
    });
    expect(r.status).toBe(0);
  });

  it("allows ordinary source files", () => {
    const r = runHook(blockMemoryWrite, {
      tool_input: { file_path: winPath("G:", "test", "oh-memos", "mcp-server-node", "src", "index.ts") },
    });
    expect(r.status).toBe(0);
  });

  it("fails open on malformed stdin", () => {
    let out: string;
    try {
      out = execFileSync(process.execPath, [blockMemoryWrite], {
        input: "not-json",
        encoding: "utf8",
      });
    } catch {
      throw new Error("hook must not block when stdin cannot be parsed");
    }
    expect(JSON.parse(out).continue).toBe(true);
  });

  it("allows an empty file_path", () => {
    const r = runHook(blockMemoryWrite, { tool_input: { file_path: "" } });
    expect(r.status).toBe(0);
  });
});

describe("block-mkdir-memory hook", () => {
  it("blocks with exit 2, not the non-blocking exit 1", () => {
    const r = runHook(blockMkdir, {
      tool_input: { command: "mkdir -p /home/u/.claude/projects/p/memory" },
    });
    expect(r.status).toBe(BLOCK);
    expect(r.stderr).toMatch(/(?<!oh_)memos_save\b/);
    expect(r.stderr).not.toContain("oh_memos_");
  });

  // On Windows, Claude Code runs shell commands through the PowerShell tool,
  // whose input carries the same `command` field.
  it.each([
    ["New-Item", `New-Item -ItemType Directory -Force -Path "${winPath("C:", "Users", "u", ".claude", "projects", "p", "memory")}"`],
    ["New-Item for a file", `New-Item -ItemType File "${winPath("C:", "Users", "u", ".claude", "projects", "p", "memory", "note.md")}"`],
    ["mkdir alias", `mkdir ${winPath("C:", "Users", "u", ".claude", "projects", "p", "memory")} | Out-Null`],
    ["a chained command", "cd /tmp && mkdir -p memory"],
  ])("blocks PowerShell-style creation: %s", (_label, command) => {
    const r = runHook(blockMkdir, { tool_name: "PowerShell", tool_input: { command } });
    expect(r.status).toBe(BLOCK);
  });

  // With PowerShell matched too, every shell command passes through this hook,
  // including ones that only mention the words.
  it.each([
    ["a commit message", 'git commit -m "fix: stop mkdir of memory dirs"'],
    ["running this hook", "node project-memory/hooks/node/oh_memos_block_mkdir_memory.js"],
    ["reading this hook", "Get-Content project-memory/hooks/node/oh_memos_block_mkdir_memory.js"],
    ["a dir that only starts with memory", "mkdir -p runtime/scratch/memory-test"],
    ["a project-memory dir", "mkdir project-memory/new"],
  ])("allows a command that only mentions it: %s", (_label, command) => {
    const r = runHook(blockMkdir, { tool_name: "PowerShell", tool_input: { command } });
    expect(r.status).toBe(0);
  });

  it("allows unrelated commands", () => {
    const r = runHook(blockMkdir, { tool_input: { command: "mkdir -p build/output" } });
    expect(r.status).toBe(0);
    expect(JSON.parse(r.stdout).continue).toBe(true);
  });

  it("fails open on malformed stdin", () => {
    const out = execFileSync(process.execPath, [blockMkdir], {
      input: "not-json",
      encoding: "utf8",
    });
    expect(JSON.parse(out).continue).toBe(true);
  });
});

/**
 * `matcher` is evaluated against the TOOL NAME only. Per the Claude Code docs, a
 * value containing any character outside [A-Za-z0-9_-, |*] is treated as an
 * unanchored regex, so an expression such as
 *   tool == "Bash" && tool_input.command matches "mkdir.*memory"
 * never matches a tool name and the hook silently never fires. This guards the
 * shipped template against that class of typo regressing.
 */
describe("settings-template.json matcher syntax", () => {
  const SIMPLE_MATCHER = /^[A-Za-z0-9_\-, |*]*$/;

  const parsed = JSON.parse(readFileSync(template, "utf8")) as {
    hooks: Record<string, Array<{ matcher?: string; hooks: unknown[] }>>;
  };

  it("every matcher is a bare tool name, list or wildcard", () => {
    const offenders: string[] = [];
    for (const [event, entries] of Object.entries(parsed.hooks)) {
      for (const entry of entries) {
        if (entry.matcher === undefined) continue; // omitted = match all
        if (!SIMPLE_MATCHER.test(entry.matcher)) {
          offenders.push(`${event}: ${JSON.stringify(entry.matcher)}`);
        }
      }
    }
    expect(offenders).toEqual([]);
  });

  it("registers the built-in memory guard across every edit tool", () => {
    const entries = parsed.hooks.PreToolUse ?? [];
    const guard = entries.find(e =>
      JSON.stringify(e.hooks).includes("oh_memos_block_memory_write"),
    );
    expect(guard, "oh_memos_block_memory_write must be wired into PreToolUse").toBeDefined();
    // Covering only Write lets the agent slip through by using Edit instead.
    for (const tool of ["Write", "Edit"]) {
      expect(guard!.matcher).toContain(tool);
    }
  });

  it("registers the mkdir guard for both Bash and PowerShell", () => {
    const entries = parsed.hooks.PreToolUse ?? [];
    const guard = entries.find(e =>
      JSON.stringify(e.hooks).includes("oh_memos_block_mkdir_memory"),
    );
    expect(guard, "oh_memos_block_mkdir_memory must be wired into PreToolUse").toBeDefined();
    expect(guard!.matcher!.split("|").sort()).toEqual(["Bash", "PowerShell"]);
  });

  it("references only hook scripts that exist on disk", () => {
    const missing: string[] = [];
    for (const entries of Object.values(parsed.hooks)) {
      for (const entry of entries) {
        for (const h of entry.hooks as Array<{ command?: string }>) {
          const m = h.command?.match(/node\/([a-z0-9_]+\.js)/i);
          if (!m) continue;
          try {
            readFileSync(join(hooksDir, "node", m[1]));
          } catch {
            missing.push(m[1]);
          }
        }
      }
    }
    expect(missing).toEqual([]);
  });
});

/**
 * The MCP tools are named memos_save, memos_search and so on. Hook messages
 * once called them oh_memos_save, which sends the agent looking for a tool that
 * does not exist.
 */
describe("hook text names real MCP tools", () => {
  // toolSchemas keys are the full names (memos_save, ...), so this matches oh_memos_save.
  const stale = new RegExp(`oh_(${Object.keys(toolSchemas).join("|")})\\b`, "g");

  function files(dir: string): string[] {
    return readdirSync(dir).flatMap(name => {
      const p = join(dir, name);
      return statSync(p).isDirectory() ? files(p) : [p];
    });
  }

  it("uses no oh_memos_<tool> names in project-memory/hooks", () => {
    const hits: string[] = [];
    for (const f of files(hooksDir)) {
      const found = readFileSync(f, "latin1").match(stale);
      if (found) hits.push(`${f.slice(hooksDir.length + 1)}: ${[...new Set(found)].join(", ")}`);
    }
    expect(hits).toEqual([]);
  });
});
