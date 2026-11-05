import { describe, expect, it } from "vitest";
import { z } from "zod";
import { ALWAYS_LOAD_TOOLS, SERVER_INSTRUCTIONS, serverOptions, toolMeta } from "./server-instructions.js";
import { toolSchemas } from "./tools-registry.js";

// Text in these places reaches the model in every session: server
// instructions, and the descriptions of tools kept loaded up front.
const ALWAYS_ON = ["memos_save", "memos_search", "memos_context_resume"] as const;
const SHOUTING = /🚨|\b(MUST|NEVER|ALWAYS|CRITICAL|PROACTIVELY|PREFER(RED)?|ONLY)\b/;

function allText(name: keyof typeof toolSchemas): string {
  const schema = toolSchemas[name];
  const params = JSON.stringify(z.toJSONSchema(schema.inputSchema));
  return `${schema.description}\n${params}`;
}

describe("server instructions", () => {
  it("fit in the part Codex reads first and name the tools they point to", () => {
    expect(SERVER_INSTRUCTIONS.length).toBeLessThanOrEqual(512);
    expect(SERVER_INSTRUCTIONS).toContain("memos_search");
    expect(SERVER_INSTRUCTIONS).toContain("memos_context_resume");
    expect(SERVER_INSTRUCTIONS).toContain("memos_save");
    expect(SERVER_INSTRUCTIONS).toContain("project_path");
    expect(SERVER_INSTRUCTIONS).not.toMatch(SHOUTING);
  });

  it("are sent only while always-on loading is enabled", () => {
    expect(serverOptions(true)).toEqual({ instructions: SERVER_INSTRUCTIONS });
    expect(serverOptions(false)).toEqual({});
  });
});

describe("always-loaded tools", () => {
  it("are memos_save and memos_search", () => {
    expect([...ALWAYS_LOAD_TOOLS]).toEqual(["memos_save", "memos_search"]);
  });

  it("carry anthropic/alwaysLoad only while enabled", () => {
    expect(toolMeta("memos_save", true)).toEqual({ "anthropic/alwaysLoad": true });
    expect(toolMeta("memos_search", true)).toEqual({ "anthropic/alwaysLoad": true });
    expect(toolMeta("memos_graph", true)).toBeUndefined();
    expect(toolMeta("memos_save", false)).toBeUndefined();
  });
});

describe("text that reaches the model in every session", () => {
  it.each(ALWAYS_ON)("%s states facts instead of shouting", (name) => {
    expect(allText(name)).not.toMatch(SHOUTING);
  });

  it("says once, in memos_save, that hand-written memory files are not read", () => {
    expect(toolSchemas.memos_save.description).toMatch(/memory files written by hand/);
    expect(toolSchemas.memos_search.description).not.toMatch(/mkdir|memory files/i);
    expect(toolSchemas.memos_context_resume.description).not.toMatch(/mkdir|memory files/i);
  });
});
