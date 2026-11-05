import { existsSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { afterAll, describe, expect, it, vi } from "vitest";
import { scratchDir } from "../scripts/_scratch.mjs";

const fixtureRoot = scratchDir("oh-memos-factory-");
vi.stubEnv("MEMOS_MODE", "full");
vi.stubEnv("MEMOS_PROVIDER", "api");
vi.stubEnv("MEMOS_URL", "http://127.0.0.1:1");
vi.stubEnv("MEMOS_USER", "factory-test");
vi.stubEnv("MEMOS_DEFAULT_CUBE", "factory_cube");
vi.stubEnv("MEMOS_CUBES_DIR", fixtureRoot);
const envFile = join(fixtureRoot, ".env");
writeFileSync(envFile, "", "utf8");
vi.stubEnv("MEMOS_ENV_FILE", envFile);
vi.stubEnv("MEMOS_LITE_EMBED", "off");

const { buildServer } = await import("./server.js");

describe("buildServer", () => {
  it("can construct probe and fallback instances without backend or storage side effects", () => {
    const first = buildServer();
    const second = buildServer();

    expect(first).not.toBe(second);
    expect(first.server.getCapabilities()).toMatchObject({ tools: {} });
    expect(second.server.getCapabilities()).toMatchObject({ tools: {} });
    expect(existsSync(join(fixtureRoot, "factory_cube"))).toBe(false);
  });
});

afterAll(() => {
  vi.unstubAllEnvs();
  rmSync(fixtureRoot, { recursive: true, force: true });
});
