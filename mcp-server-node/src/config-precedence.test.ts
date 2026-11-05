import { describe, expect, it } from "vitest";
import { execFileSync } from "child_process";
import { rmSync, writeFileSync } from "fs";
import { join, resolve } from "path";
import { scratchDir } from "../scripts/_scratch.mjs";

const entry = resolve(process.cwd(), "dist/config.js");
const entryUrl = `file://${entry.replace(/\\/g, "/")}`;

function loadConfig(cwd: string, env: Record<string, string>, args: string[] = []): { stdout: string; stderr: string } {
  const script = `import(${JSON.stringify(entryUrl)}).then(c=>console.log(JSON.stringify({url:c.MEMOS_URL,provider:c.MEMOS_PROVIDER,cube:c.MEMOS_DEFAULT_CUBE})))`;
  try {
    const stdout = execFileSync(process.execPath, ["-e", script, ...args], {
      cwd,
      env: { ...process.env, ...env },
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    return { stdout, stderr: "" };
  } catch (error) {
    const e = error as { stdout?: Buffer; stderr?: Buffer };
    return { stdout: e.stdout?.toString() ?? "", stderr: e.stderr?.toString() ?? "" };
  }
}

describe("dotenv precedence", () => {
  it("keeps inherited process values over a guessed cwd .env", () => {
    const cwd = scratchDir("config-cwd-");
    try {
      writeFileSync(join(cwd, ".env"), "MEMOS_URL=http://guessed\nMEMOS_PROVIDER=api\nMEMOS_USER=file\nMEMOS_DEFAULT_CUBE=file_cube\nMEMOS_CUBES_DIR=/tmp/file\n");
      const out = loadConfig(cwd, { MEMOS_URL: "http://inherited", MEMOS_PROVIDER: "local", MEMOS_USER: "process", MEMOS_DEFAULT_CUBE: "process_cube", MEMOS_CUBES_DIR: "/tmp/process" });
      expect(JSON.parse(out.stdout)).toMatchObject({ url: "http://inherited", provider: "local", cube: "process_cube" });
    } finally { rmSync(cwd, { recursive: true, force: true }); }
  });

  it("lets an explicitly selected env file override inherited values", () => {
    const cwd = scratchDir("config-explicit-");
    try {
      const explicit = join(cwd, "explicit.env");
      writeFileSync(explicit, "MEMOS_URL=http://explicit\nMEMOS_PROVIDER=api\nMEMOS_USER=explicit\nMEMOS_DEFAULT_CUBE=explicit_cube\nMEMOS_CUBES_DIR=/tmp/explicit\n");
      const out = loadConfig(cwd, { MEMOS_ENV_FILE: explicit, MEMOS_URL: "http://inherited", MEMOS_USER: "process", MEMOS_DEFAULT_CUBE: "process_cube", MEMOS_CUBES_DIR: "/tmp/process" });
      expect(JSON.parse(out.stdout)).toMatchObject({ url: "http://explicit", provider: "api", cube: "explicit_cube" });
    } finally { rmSync(cwd, { recursive: true, force: true }); }
  });
});
