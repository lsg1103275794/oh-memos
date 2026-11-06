import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { toolSchemas } from "./tools-registry.js";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const canonicalPath = resolve(repoRoot, "docs", "architecture", "oh-memos-layered.mmd");
const targetDocs = [
  "README.md",
  "README_CN.md",
  "ARCHITECTURE.md",
  "docs/CHANGELOG.md",
];

const START = "<!-- architecture-aware-memory:start -->";
const END = "<!-- architecture-aware-memory:end -->";
const TOOL_START = "<!-- mcp-tool-inventory:start -->";
const TOOL_END = "<!-- mcp-tool-inventory:end -->";

function markedRegion(markdown: string, startMarker: string, endMarker: string): string | null {
  const start = markdown.indexOf(startMarker);
  const end = markdown.indexOf(endMarker);
  if (start === -1 || end === -1 || end <= start) return null;
  return markdown.slice(start + startMarker.length, end).trim();
}

function embeddedMermaid(markdown: string): string | null {
  const region = markedRegion(markdown, START, END);
  if (region === null) return null;
  const match = region.match(/^```mermaid\s*\n([\s\S]*?)\n```$/);
  return match?.[1].trim() ?? null;
}

describe("architecture-aware memory documentation", () => {
  it("keeps the README and changelog diagrams equal to the canonical topology", () => {
    // Compare content, not line endings: on Windows one file can be checked out
    // with CRLF while another was rewritten with LF by an editor or script.
    const read = (path: string) => readFileSync(path, "utf8").replace(/\r\n/g, "\n");
    const canonical = read(canonicalPath).trim();
    for (const relative of targetDocs) {
      const markdown = read(resolve(repoRoot, relative));
      expect(embeddedMermaid(markdown), relative).toBe(canonical);
    }
  });

  it("contains one marked architecture diagram in every target document", () => {
    for (const relative of targetDocs) {
      const markdown = readFileSync(resolve(repoRoot, relative), "utf8");
      expect(markdown.split(START).length - 1, relative).toBe(1);
      expect(markdown.split(END).length - 1, relative).toBe(1);
    }
  });

  it("keeps the architecture tool inventory aligned with the registry", () => {
    const architecture = readFileSync(resolve(repoRoot, "ARCHITECTURE.md"), "utf8");
    const names = Object.keys(toolSchemas);
    expect(architecture).toContain(`推荐 Node MCP 定义 ${names.length} 个工具 schema`);
    for (const name of names) expect(architecture, name).toContain(`\`${name}\``);
  });

  it("keeps the Node MCP README tool inventory aligned with the registry", () => {
    const readme = readFileSync(resolve(repoRoot, "mcp-server-node", "README.md"), "utf8");
    const names = Object.keys(toolSchemas);
    const inventory = markedRegion(readme, TOOL_START, TOOL_END);

    expect(readme).toContain(`## Tools (${names.length})`);
    expect(inventory).not.toBeNull();
    for (const name of names) expect(inventory, name).toContain(`\`${name}\``);
  });
});
