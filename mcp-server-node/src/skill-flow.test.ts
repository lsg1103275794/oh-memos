import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { rmSync, mkdirSync, writeFileSync, readFileSync, existsSync } from "fs";
import { join } from "path";
import {
  handleMemosReviewSkillCandidate,
  handleMemosInstallSkillCandidate,
} from "./handlers/skill.js";
import { scratchDir } from "../scripts/_scratch.mjs";

let root = "";
const CANDIDATE = `---
generator: oh-memos-skill-distill
status: candidate
slug: migration-locking
generated_at: 2026-08-16T00:00:00Z
source_memory_ids: ["m1"]
---

# Migration locking

Use advisory locks.
`;

function writeCandidate(content = CANDIDATE): string {
  mkdirSync(join(root, "skill-candidates"), { recursive: true });
  const file = join(root, "skill-candidates", "migration-locking.md");
  writeFileSync(file, content, "utf8");
  return file;
}

beforeEach(() => { root = scratchDir("skill-flow-"); });
afterEach(() => rmSync(root, { recursive: true, force: true }));

describe("skill candidate review and install", () => {
  it("approves a candidate and records the reviewer", () => {
    const file = writeCandidate();
    const result = handleMemosReviewSkillCandidate({ project_path: root, candidate_id: "migration-locking.md", action: "approve", reviewer: "alice" });
    expect(result[0].text).toContain("approved");
    const updated = readFileSync(file, "utf8");
    expect(updated).toContain("status: approved");
    expect(updated).toContain("reviewer: alice");
  });

  it("refuses installation until approved", () => {
    writeCandidate();
    const result = handleMemosInstallSkillCandidate({ project_path: root, candidate_id: "migration-locking.md" });
    expect(result[0].text).toContain("must be approved");
    expect(existsSync(join(root, ".claude", "skills", "migration-locking", "SKILL.md"))).toBe(false);
  });

  it("installs an approved candidate into .claude/skills once", () => {
    writeCandidate();
    handleMemosReviewSkillCandidate({ project_path: root, candidate_id: "migration-locking.md", action: "approve", reviewer: "alice" });
    const first = handleMemosInstallSkillCandidate({ project_path: root, candidate_id: "migration-locking.md" });
    expect(first[0].text).toContain("installed at");
    expect(existsSync(join(root, ".claude", "skills", "migration-locking", "SKILL.md"))).toBe(true);
    const second = handleMemosInstallSkillCandidate({ project_path: root, candidate_id: "migration-locking.md" });
    expect(second[0].text).toContain("refusing overwrite");
  });

  it("rejects rejected candidates and path traversal", () => {
    writeCandidate();
    handleMemosReviewSkillCandidate({ project_path: root, candidate_id: "migration-locking.md", action: "reject", reviewer: "bob" });
    expect(handleMemosInstallSkillCandidate({ project_path: root, candidate_id: "migration-locking.md" })[0].text).toContain("must be approved");
    expect(handleMemosInstallSkillCandidate({ project_path: root, candidate_id: "../../evil.md" })[0].text).toContain("failed");
  });

  it("rejects candidates that are not ours", () => {
    writeCandidate(CANDIDATE.replace("generator: oh-memos-skill-distill", "generator: someone-else"));
    expect(handleMemosReviewSkillCandidate({ project_path: root, candidate_id: "migration-locking.md", action: "approve", reviewer: "alice" })[0].text).toContain("Invalid candidate");
  });
});
