import { describe, expect, it } from "vitest";
import { rmSync } from "fs";
import { join, sep } from "path";
import { parseCandidateFrontMatter, transitionCandidate, installTargetPath } from "./skill-lifecycle.js";
import { scratchDir } from "../scripts/_scratch.mjs";

describe("skill candidate lifecycle", () => {
  const candidate = `---\ngenerator: oh-memos-skill-distill\nstatus: candidate\nslug: migration-locking\nsource_memory_ids: ["m1", "m2"]\n---\n\n# Migration locking\n\nUse advisory locks.`;

  it("parses a valid candidate", () => {
    expect(parseCandidateFrontMatter(candidate)).toEqual({
      ok: true,
      status: "candidate",
      slug: "migration-locking",
      sourceMemoryIds: ["m1", "m2"],
    });
  });

  it("allows explicit approve/reject transitions only", () => {
    expect(transitionCandidate("candidate", "approve")).toBe("approved");
    expect(transitionCandidate("candidate", "reject")).toBe("rejected");
    expect(transitionCandidate("approved", "approve")).toBe(null);
    expect(transitionCandidate("rejected", "install")).toBe(null);
    expect(transitionCandidate("approved", "install")).toBe("installed");
  });

  it("rejects malformed or untrusted candidates", () => {
    expect(parseCandidateFrontMatter(candidate.replace("generator: oh-memos-skill-distill", "generator: other")).ok).toBe(false);
    expect(parseCandidateFrontMatter(candidate.replace("source_memory_ids: [\"m1\", \"m2\"]", "source_memory_ids: []")).ok).toBe(false);
  });

  it("confines installation to project .claude/skills", () => {
    // A real absolute root (not a Windows-style literal) so the assertion
    // holds on posix runners too, where "G:/project" is a relative path.
    const root = scratchDir("skill-target-");
    try {
      const target = installTargetPath(root, "migration-locking");
      expect(target.startsWith(root + sep)).toBe(true);
      expect(target.endsWith(join(".claude", "skills", "migration-locking", "SKILL.md"))).toBe(true);
      expect(() => installTargetPath(root, "../escape")).toThrow();
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});
