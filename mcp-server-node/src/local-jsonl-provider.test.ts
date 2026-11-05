import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { rmSync, mkdirSync, writeFileSync, readFileSync } from "fs";
import { join } from "path";
import { LocalJsonlProvider } from "./providers/local-jsonl-provider.js";
import type { LiteEmbedder } from "./providers/lite-embedding.js";
import { scratchDir } from "../scripts/_scratch.mjs";

let root = "";
beforeEach(() => { root = scratchDir("lite-store-"); });
afterEach(() => rmSync(root, { recursive: true, force: true }));

function provider(): LocalJsonlProvider {
  return new LocalJsonlProvider(root);
}

describe("local jsonl provider", () => {
  it("saves and reads back a typed memory", async () => {
    const p = provider();
    const saved = await p.save({ cubeId: "demo_cube", content: "Use advisory locks", memoryType: "DECISION", tags: ["db"] });
    expect(saved.id).toMatch(/[0-9a-f-]{36}/);
    expect(saved.memory).toBe("[DECISION] Use advisory locks");
    const got = await p.get("demo_cube", saved.id);
    expect(got?.memory).toBe("[DECISION] Use advisory locks");
    expect(got?.metadata?.type).toBe("DECISION");
    expect(got?.metadata?.source).toBe("local-lite");
  });

  it("lists newest first and filters by type", async () => {
    const p = provider();
    await p.save({ cubeId: "c", content: "one", memoryType: "BUGFIX" });
    await p.save({ cubeId: "c", content: "two", memoryType: "DECISION" });
    const all = await p.list("c", 10);
    expect(all.length).toBe(2);
    const decisions = await p.list("c", 10, "DECISION");
    expect(decisions.map((m) => m.memory)).toEqual(["[DECISION] two"]);
  });

  it("performs deterministic lexical search with relativity", async () => {
    const p = provider();
    await p.save({ cubeId: "c", content: "Qdrant vector recall tuning", memoryType: "CONFIG" });
    await p.save({ cubeId: "c", content: "unrelated note about coffee", memoryType: "PROGRESS" });
    const hits = await p.search("c", "qdrant recall", 5);
    expect(hits[0].memory).toContain("Qdrant");
    expect(Number(hits[0].metadata?.relativity)).toBeGreaterThan(0);
    expect(hits.length).toBeLessThanOrEqual(5);
  });

  it("returns only recent memories for context resume", async () => {
    const p = provider();
    const saved = await p.save({ cubeId: "c", content: "fresh", memoryType: "PROGRESS" });
    const file = join(root, "c", "memories.jsonl");
    const stale = JSON.parse(readFileSync(file, "utf8").trim());
    stale.id = "00000000-0000-4000-8000-000000000000";
    stale.updated_at = new Date(Date.now() - 72 * 3600_000).toISOString();
    writeFileSync(file, `${JSON.stringify(stale)}\n${JSON.stringify({ ...stale, id: saved.id, updated_at: new Date().toISOString() })}\n`, "utf8");
    const recent = await p.recent("c", 24, 10);
    expect(recent.map((m) => m.id)).toEqual([saved.id]);
  });

  it("tolerates a truncated trailing line but rejects corrupt middle lines", async () => {
    const p = provider();
    const saved = await p.save({ cubeId: "c", content: "kept", memoryType: "BUGFIX" });
    const file = join(root, "c", "memories.jsonl");
    const good = readFileSync(file, "utf8").trim();
    writeFileSync(file, `${good}\n{"id":"partial"`, "utf8");
    expect((await p.list("c", 10)).map((m) => m.id)).toEqual([saved.id]);
    writeFileSync(file, `not-json\n${good}\n`, "utf8");
    await expect(p.list("c", 10)).rejects.toThrow(/corrupt/i);
  });

  it("refuses to write while another process holds the lock", async () => {
    const p = provider();
    mkdirSync(join(root, "c"), { recursive: true });
    writeFileSync(join(root, "c", "memories.jsonl.lock"), JSON.stringify({ pid: 1, started_at: new Date().toISOString() }), "utf8");
    await expect(p.save({ cubeId: "c", content: "blocked", memoryType: "BUGFIX" })).rejects.toThrow(/lock/i);
  });
});

// Three fixed concept vectors: the vector-store concept family (qdrant,
// vector, recall) maps to [1,0,0], coffee to [0,1,0], everything else to
// [0,0,1]. Enough to make cosine order observable without a real model.
function fakeEmbedder(overrides: Partial<Record<"save" | "search", (text: string) => number[] | null>> = {}): LiteEmbedder {
  const concept = (text: string): number[] => {
    if (/qdrant|vector|recall/i.test(text)) return [1, 0, 0];
    if (/coffee/i.test(text)) return [0, 1, 0];
    return [0, 0, 1];
  };
  return {
    kind: "fake",
    embed: async (text: string) => {
      // An explicit override returning null means "embedding failed" and must
      // NOT fall back to the concept vector — that is the whole point of the
      // degradation tests.
      const overridden = /^query:/.test(text) ? overrides.search?.(text) : overrides.save?.(text);
      return overridden !== undefined ? overridden : concept(text);
    },
  };
}

describe("local jsonl provider semantic search", () => {
  it("persists embeddings in the store but never returns them", async () => {
    const p = new LocalJsonlProvider(root, fakeEmbedder());
    const saved = await p.save({ cubeId: "c", content: "Qdrant tuning", memoryType: "CONFIG" });
    const rawLine = readFileSync(join(root, "c", "memories.jsonl"), "utf8").trim();
    expect(JSON.parse(rawLine).embedding).toEqual([1, 0, 0]);
    expect(saved).not.toHaveProperty("embedding");
    expect(await p.get("c", saved.id)).not.toHaveProperty("embedding");
    const listed = await p.list("c", 10);
    expect(listed[0]).not.toHaveProperty("embedding");
  });

  it("ranks a semantic match above lexical-only noise", async () => {
    const p = new LocalJsonlProvider(root, fakeEmbedder());
    await p.save({ cubeId: "c", content: "Coffee brewing notes", memoryType: "PROGRESS" });
    await p.save({ cubeId: "c", content: "Vector recall", memoryType: "CONFIG" });
    // Query has no lexical overlap with "Vector recall" but the same concept
    // vector as the qdrant-family memories; only semantic matching finds it.
    const hits = await p.search("c", "query: qdrant", 5);
    expect(hits[0]?.memory).toContain("Vector recall");
    expect(hits.map((m) => m.memory)).not.toContain(expect.stringContaining("Coffee"));
  });

  it("falls back to lexical ranking when the embedder is unavailable", async () => {
    const p = new LocalJsonlProvider(root, fakeEmbedder({ save: () => [1, 0, 0], search: () => null }));
    await p.save({ cubeId: "c", content: "Qdrant vector recall tuning", memoryType: "CONFIG" });
    await p.save({ cubeId: "c", content: "unrelated coffee note", memoryType: "PROGRESS" });
    const hits = await p.search("c", "query: qdrant recall", 5);
    expect(hits).toHaveLength(1);
    expect(hits[0].memory).toContain("Qdrant");
  });

  it("saves without an embedding when embedding fails at write time", async () => {
    const p = new LocalJsonlProvider(root, fakeEmbedder({ save: () => null }));
    const saved = await p.save({ cubeId: "c", content: "Qdrant tuning", memoryType: "CONFIG" });
    const rawLine = readFileSync(join(root, "c", "memories.jsonl"), "utf8").trim();
    expect(JSON.parse(rawLine)).not.toHaveProperty("embedding");
    // The lexical path must still find it.
    const hits = await p.search("c", "qdrant", 5);
    expect(hits[0]?.id).toBe(saved.id);
  });

  it("ignores stored embeddings whose dimension mismatches the query", async () => {
    const p = new LocalJsonlProvider(root, fakeEmbedder({ save: () => [1, 0] }));
    await p.save({ cubeId: "c", content: "Qdrant tuning", memoryType: "CONFIG" });
    const hits = await p.search("c", "query: qdrant", 5);
    // 2-dim record vs 3-dim query: cosine undefined, lexical decides.
    expect(hits[0]?.memory).toContain("Qdrant");
  });
});
