import { readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { describe, expect, it } from "vitest";
import { scratchDir } from "../scripts/_scratch.mjs";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const scriptPath = resolve(
  repoRoot,
  "scripts",
  "generate-readme-changelog.mjs",
);

/**
 * 导入仓库根的 `scripts/*.mjs`，绕开 shebang。
 *
 * 该脚本首行是 `#!/usr/bin/env node`。Vite 的 module runner 加载非入口
 * `.mjs` 时**不剥 shebang**，`#` 作为非法 token 让整个 suite 收集失败
 * （`SyntaxError: Invalid or unexpected token`，报在 import 那一行，
 * 看起来像测试文件自己的语法错，实际错在被导入的模块）。
 *
 * 实测排除的三条路：
 *   - 裸绝对路径 → Windows 上 `G:` 被当 URL scheme
 *   - `pathToFileURL` 单独用 → 仍走 Vite runner，shebang 照旧不剥
 *   - `/* @vite-ignore *&#47;` → runner 依然接管动态 import
 *   - `server.deps.external` → 3.2.7 下对项目内文件不生效
 *
 * 所以剥掉首行写到临时文件再导入。**必须是真实文件路径**而非 data URL：
 * 脚本末尾的 main-guard 会求值 `fileURLToPath(import.meta.url)`
 * （`process.argv[1]` 在 vitest 下非空，短路不掉），data URL 会让它抛错。
 * 临时文件路径与 `process.argv[1]` 不同，guard 判假，`main()` 不会跑。
 *
 * 不选「删掉脚本的 shebang」—— 那是为了过测试去改被测对象。所有调用点
 * （CI、README）都是 `node scripts/...`，shebang 无害。
 */
async function importWithoutShebang(
  path: string,
): Promise<Record<string, unknown>> {
  const source = readFileSync(path, "utf8");
  const stripped = source.replace(/^#![^\n]*/, "");
  const dir = scratchDir("ohm-readme-");
  const copy = join(dir, "generate-readme-changelog.mjs");
  try {
    writeFileSync(copy, stripped, "utf8");
    return (await import(pathToFileURL(copy).href)) as Record<string, unknown>;
  } finally {
    // import 完成后模块已在内存里，删掉临时目录不影响后续断言。
    rmSync(dir, { recursive: true, force: true });
  }
}

const {
  CHANGELOG,
  ENTRY_COUNT,
  START,
  END,
  TARGETS,
  UNRELEASED,
  EN_HINT,
  formatVersion,
  parseEntries,
  renderBlock,
  replaceMarkedBlock,
} = (await importWithoutShebang(scriptPath)) as any;

const changelog = readFileSync(resolve(repoRoot, CHANGELOG), "utf8");
const readmes = (TARGETS as { file: string; lang: string }[]).map(
  ({ file, lang }) => ({
    relative: file,
    lang,
    source: readFileSync(resolve(repoRoot, file), "utf8"),
  }),
);
const recent = parseEntries(changelog).slice(0, ENTRY_COUNT);

describe("README changelog block", () => {
  it("carries exactly one marked block in every target README", () => {
    for (const { relative, source } of readmes) {
      expect(source.split(START).length - 1, relative).toBe(1);
      expect(source.split(END).length - 1, relative).toBe(1);
    }
  });

  it("matches what the generator would write right now", () => {
    for (const { relative, lang, source } of readmes) {
      const block = renderBlock(recent, lang);
      expect(replaceMarkedBlock(source, block), relative).toBe(source);
    }
  });

  it("renders exactly ENTRY_COUNT entries, one per line, in both languages", () => {
    expect(recent).toHaveLength(ENTRY_COUNT);
    for (const lang of ["en", "zh"]) {
      const lines = renderBlock(recent, lang).split("\n");
      expect(lines, lang).toHaveLength(ENTRY_COUNT);
      for (const line of lines) expect(line.startsWith("- "), lang).toBe(true);
    }
  });

  it("renders each README in its own language", () => {
    const en = renderBlock(recent, "en");
    const zh = renderBlock(recent, "zh");
    expect(en).not.toBe(zh);
    // The English block must not leak CJK from an untranslated entry.
    expect(en).not.toMatch(/[一-鿿]/);
    expect(zh).toMatch(/[一-鿿]/);
  });

  it("has an English title for every entry inside the rendered window", () => {
    for (const entry of recent) {
      expect(entry.titleEn, `### ${entry.title} needs ${EN_HINT}`).toBeTruthy();
    }
  });

  it.each([
    ["LF", "\n"],
    ["CRLF", "\r\n"],
  ])("preserves %s line endings and surrounding content", (_name, eol) => {
    // Git checkouts may use either style. Explicit fixtures exercise both on
    // every platform instead of assuming the developer's checkout settings.
    const source = ["# Before", START, "- outdated", END, "## After", ""].join(eol);
    const expected = [
      "# Before", START, "- first", "- second", END, "## After", "",
    ].join(eol);

    expect(replaceMarkedBlock(source, "- first\n- second")).toBe(expected);
  });
});

describe("changelog parser", () => {
  it("ignores headings inside fenced code blocks", () => {
    const entries = parseEntries(
      [
        "## [9.9.9] - 2026-01-01",
        "### real entry",
        "",
        "```bash",
        "## [8.8.8] - 2025-01-01",
        "### fake entry in a fence",
        "```",
        "",
        "### second real entry",
      ].join("\n"),
    );
    expect(entries.map((e: { title: string }) => e.title)).toEqual([
      "real entry",
      "second real entry",
    ]);
    expect(
      entries.every(
        (e: { version: string }) => e.version === "9.9.9 · 2026-01-01",
      ),
    ).toBe(true);
  });

  it("keeps document order rather than sorting by version", () => {
    // The real changelog is not monotonic: 3.0.1 precedes 3.2.0 and 3.0.0
    // appears twice, so sorting would reorder history.
    const entries = parseEntries(
      [
        "## [3.0.1] - 2026-08-19",
        "### newer",
        "## [3.2.0] - 2026-08-15",
        "### older",
      ].join("\n"),
    );
    expect(entries.map((e: { title: string }) => e.title)).toEqual([
      "newer",
      "older",
    ]);
  });

  it("does not let trailing prose sections re-tag entries as a version", () => {
    const entries = parseEntries(
      [
        "## [1.0.0] - 2026-01-01",
        "### tagged",
        "## Contributing",
        "### still tagged",
      ].join("\n"),
    );
    expect(entries.map((e: { version: string }) => e.version)).toEqual([
      "1.0.0 · 2026-01-01",
      "1.0.0 · 2026-01-01",
    ]);
  });

  it("formats version headings and rejects non-version ones", () => {
    expect(formatVersion("[3.0.1] - 2026-08-19")).toBe("3.0.1 · 2026-08-19");
    expect(formatVersion("[Unreleased]")).toBe(UNRELEASED);
    expect(formatVersion("Contributing")).toBeNull();
    expect(formatVersion("Version History")).toBeNull();
  });

  it("binds an en comment to the heading directly above it", () => {
    const entries = parseEntries(
      [
        "## [1.0.0] - 2026-01-01",
        "### 中文标题",
        "<!-- en: English title -->",
        "",
        "body text",
      ].join("\n"),
    );
    expect(entries).toHaveLength(1);
    expect(entries[0].titleEn).toBe("English title");
    expect(renderBlock(entries, "en")).toBe(
      "- `1.0.0 · 2026-01-01` — English title",
    );
    expect(renderBlock(entries, "zh")).toBe(
      "- `1.0.0 · 2026-01-01` — 中文标题",
    );
  });

  it("tolerates a blank line between the heading and its en comment", () => {
    const entries = parseEntries(
      ["### 标题", "", "<!-- en: Title -->", "", "body"].join("\n"),
    );
    expect(entries[0].titleEn).toBe("Title");
  });

  it("does not bind an en comment that appears after body prose", () => {
    const entries = parseEntries(
      ["### 标题", "", "body text first", "<!-- en: Too late -->"].join("\n"),
    );
    expect(entries[0].titleEn).toBeNull();
  });

  it("does not bind an en comment from inside a fenced block", () => {
    const entries = parseEntries(
      ["### 标题", "```md", "<!-- en: Not a title -->", "```"].join("\n"),
    );
    expect(entries[0].titleEn).toBeNull();
  });

  it("leaves titleEn null when no en comment is present", () => {
    const entries = parseEntries(["### 只有中文", "", "body"].join("\n"));
    expect(entries[0].titleEn).toBeNull();
    // renderBlock falls back so a partial run is still readable; main() is what
    // refuses to write, so the fallback never reaches a committed README.
    expect(renderBlock(entries, "en")).toBe("- 只有中文");
  });

  it("tags released entries and leaves unreleased ones bare", () => {
    const block = renderBlock(
      [
        { version: UNRELEASED, title: "pending work", titleEn: "pending work" },
        {
          version: "3.0.1 · 2026-08-19",
          title: "shipped work",
          titleEn: "shipped work",
        },
      ],
      "zh",
    );
    expect(block).toBe("- pending work\n- `3.0.1 · 2026-08-19` — shipped work");
  });

  it("reports malformed markers instead of silently writing", () => {
    expect(replaceMarkedBlock("no markers here", "- x")).toBeNull();
    expect(replaceMarkedBlock(`${END}\n${START}`, "- x")).toBeNull();
  });
});
