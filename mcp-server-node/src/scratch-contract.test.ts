import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, utimesSync } from "node:fs";
import { basename, join, resolve, sep } from "node:path";
import { describe, expect, it } from "vitest";
import { SCRATCH, scratchDir, sweepStale } from "../scripts/_scratch.mjs";

// Contract: .agents/contracts/common/artifacts.md. Test temp files go under
// <repo>/runtime/scratch/node/, never the system temp dir.
const REPO = resolve(process.cwd(), "..");

describe("scratch directories", () => {
  it("live under runtime/scratch/node in the repository", () => {
    expect(SCRATCH).toBe(join(REPO, "runtime", "scratch", "node"));
    const dir = scratchDir("scratch-contract-");
    try {
      expect(dir.startsWith(SCRATCH + sep)).toBe(true);
      expect(basename(dir).startsWith("scratch-contract-")).toBe(true);
      expect(existsSync(dir)).toBe(true);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("sweep removes leftovers older than a day and keeps fresh ones", () => {
    const stale = scratchDir("scratch-stale-");
    const fresh = scratchDir("scratch-fresh-");
    try {
      const twoDaysAgo = new Date(Date.now() - 2 * 864e5);
      utimesSync(stale, twoDaysAgo, twoDaysAgo);
      sweepStale();
      expect(existsSync(stale)).toBe(false);
      expect(existsSync(fresh)).toBe(true);
    } finally {
      rmSync(stale, { recursive: true, force: true });
      rmSync(fresh, { recursive: true, force: true });
    }
  });

  it("sweep tolerates a missing scratch root", () => {
    mkdirSync(SCRATCH, { recursive: true });
    expect(() => sweepStale(Date.now())).not.toThrow();
  });
});

describe("no test or smoke script writes to the system temp dir", () => {
  const sources = [
    ...readdirSync(join(REPO, "mcp-server-node", "src"))
      .filter((name) => name.endsWith(".test.ts"))
      .map((name) => join(REPO, "mcp-server-node", "src", name)),
    ...readdirSync(join(REPO, "mcp-server-node", "scripts"))
      .filter((name) => name.endsWith(".mjs"))
      .map((name) => join(REPO, "mcp-server-node", "scripts", name)),
  ];

  it.each(sources.map((path) => [basename(path), path]))("%s", (_name, path) => {
    expect(readFileSync(path, "utf8")).not.toMatch(/\btmpdir\(\)/);
  });
});
