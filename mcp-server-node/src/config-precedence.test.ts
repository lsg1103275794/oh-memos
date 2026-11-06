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

describe("boolean CLI flags", () => {
  // `node -e` drops the first extra argument from process.argv, hence "_".
  function flags(args: string[], extraEnv: Record<string, string> = {}): string {
    const cwd = scratchDir("config-flags-");
    try {
      const envFile = join(cwd, "empty.env");
      writeFileSync(envFile, "");
      const env: Record<string, string | undefined> = {
        ...process.env,
        MEMOS_MODE: "lite",
        MEMOS_PROVIDER: "local",
        MEMOS_URL: "",
        MEMOS_USER: "ci",
        MEMOS_DEFAULT_CUBE: "ci_cube",
        MEMOS_CUBES_DIR: cwd,
        MEMOS_ENV_FILE: envFile,
        ...extraEnv,
      };
      if (!("MEMOS_ALWAYS_LOAD" in extraEnv)) delete env.MEMOS_ALWAYS_LOAD;
      if (!("MEMOS_ENABLE_DELETE" in extraEnv)) delete env.MEMOS_ENABLE_DELETE;
      const script = `import(${JSON.stringify(entryUrl)}).then(c=>console.log(JSON.stringify({alwaysLoad:c.MEMOS_ALWAYS_LOAD,enableDelete:c.MEMOS_ENABLE_DELETE})),e=>console.log(JSON.stringify({error:String(e)})))`;
      return execFileSync(process.execPath, ["-e", script, "_", ...args], { cwd, env, encoding: "utf8" });
    } finally {
      rmSync(cwd, { recursive: true, force: true });
    }
  }

  it.each([
    [[], { alwaysLoad: true, enableDelete: false }],
    [["--memos-always-load", "false"], { alwaysLoad: false }],
    [["--memos-always-load=false"], { alwaysLoad: false }],
    [["--memos-always-load"], { alwaysLoad: true }],
    [["--memos-enable-delete"], { enableDelete: true }],
    [["--memos-enable-delete", "false"], { enableDelete: false }],
  ])("%j", (args, expected) => {
    expect(JSON.parse(flags(args as string[]))).toMatchObject(expected);
  });

  it("reads MEMOS_ALWAYS_LOAD from the environment", () => {
    expect(JSON.parse(flags([], { MEMOS_ALWAYS_LOAD: "false" }))).toMatchObject({ alwaysLoad: false });
  });
});

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
