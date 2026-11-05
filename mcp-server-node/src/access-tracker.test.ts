import { afterEach, beforeEach, describe, expect, it } from "vitest";
import * as fs from "fs";
import * as path from "path";
import {
  readAccessStats,
  recordAccess,
  resetAccessCache,
} from "./access-tracker.js";
import { applyMemoryQualityPolicy } from "./memory-quality.js";
import type { MemoryNode } from "./types.js";
import { scratchDir } from "../scripts/_scratch.mjs";

let root: string;
const CUBE = "test_cube";

const logFile = (): string => path.join(root, CUBE, "access-log.jsonl");
const lines = (): string[] =>
  fs
    .readFileSync(logFile(), "utf8")
    .split("\n")
    .filter((l) => l.trim());

beforeEach(() => {
  root = scratchDir("access-tracker-");
  resetAccessCache();
});

afterEach(() => {
  fs.rmSync(root, { recursive: true, force: true });
  resetAccessCache();
});

describe("recordAccess", () => {
  it("首次记账会建目录并写一行", () => {
    recordAccess(root, CUBE, ["a"]);
    expect(lines()).toHaveLength(1);
    expect(readAccessStats(root, CUBE).get("a")?.count).toBe(1);
  });

  it("多次记账累加计数", () => {
    for (let i = 0; i < 3; i += 1) {
      recordAccess(root, CUBE, ["a"]);
      resetAccessCache();
    }
    expect(readAccessStats(root, CUBE).get("a")?.count).toBe(3);
  });

  it("一次可记多个 id，各自独立计数", () => {
    recordAccess(root, CUBE, ["a", "b"]);
    resetAccessCache();
    recordAccess(root, CUBE, ["b"]);
    resetAccessCache();
    const stats = readAccessStats(root, CUBE);
    expect(stats.get("a")?.count).toBe(1);
    expect(stats.get("b")?.count).toBe(2);
  });

  it("空 id 与空数组不写盘", () => {
    recordAccess(root, CUBE, []);
    recordAccess(root, CUBE, ["", "   "]);
    expect(fs.existsSync(logFile())).toBe(false);
  });

  it("lastAt 取最近一次，不被旧时间戳覆盖", () => {
    recordAccess(root, CUBE, ["a"]);
    resetAccessCache();
    const first = readAccessStats(root, CUBE).get("a")!.lastAt;
    fs.appendFileSync(
      logFile(),
      `${JSON.stringify({ t: "2020-01-01T00:00:00.000Z", ids: ["a"] })}\n`,
    );
    resetAccessCache();
    const after = readAccessStats(root, CUBE).get("a")!;
    expect(after.count).toBe(2);
    expect(after.lastAt).toBe(first);
  });

  it("写入失败不抛异常（目标路径被文件占据）", () => {
    fs.writeFileSync(path.join(root, CUBE), "not a directory");
    expect(() => recordAccess(root, CUBE, ["a"])).not.toThrow();
  });
});

describe("readAccessStats", () => {
  it("日志不存在时返回空 map，不抛异常", () => {
    expect(readAccessStats(root, "never_used").size).toBe(0);
    expect(readAccessStats("/nonexistent/path", CUBE).size).toBe(0);
  });

  it("跳过坏行，保留同一文件里的好行（撕裂自愈）", () => {
    fs.mkdirSync(path.join(root, CUBE), { recursive: true });
    fs.writeFileSync(
      logFile(),
      [
        JSON.stringify({ t: "2026-01-01T00:00:00.000Z", ids: ["good"] }),
        '{"t":"2026-01-01T00:00:00.000Z","ids":["torn', // 撕裂行
        "not json at all",
        "",
        JSON.stringify({ t: "2026-01-02T00:00:00.000Z", ids: ["good"] }),
      ].join("\n"),
    );
    const stats = readAccessStats(root, CUBE);
    expect(stats.get("good")?.count).toBe(2);
    expect(stats.size).toBe(1);
  });

  it("忽略结构不合法的行", () => {
    fs.mkdirSync(path.join(root, CUBE), { recursive: true });
    fs.writeFileSync(
      logFile(),
      [
        JSON.stringify({ ids: ["no-timestamp"] }),
        JSON.stringify({ t: "2026-01-01T00:00:00.000Z" }),
        JSON.stringify({ t: "2026-01-01T00:00:00.000Z", ids: "not-an-array" }),
        JSON.stringify([1, 2, 3]),
        JSON.stringify(null),
        JSON.stringify({ t: "2026-01-01T00:00:00.000Z", ids: ["real"] }),
      ].join("\n"),
    );
    const stats = readAccessStats(root, CUBE);
    expect([...stats.keys()]).toEqual(["real"]);
  });

  it("缓存生效后同一次读取不重复解析，但内容变化会失效", () => {
    recordAccess(root, CUBE, ["a"]);
    expect(readAccessStats(root, CUBE).get("a")?.count).toBe(1);
    // recordAccess 内部会清缓存，所以第二次记账立刻可见。
    recordAccess(root, CUBE, ["a"]);
    expect(readAccessStats(root, CUBE).get("a")?.count).toBe(2);
  });
});

describe("压实", () => {
  const fillLines = (n: number): void => {
    fs.mkdirSync(path.join(root, CUBE), { recursive: true });
    const rows = [];
    for (let i = 0; i < n; i += 1) {
      rows.push(
        JSON.stringify({ t: "2026-01-01T00:00:00.000Z", ids: [`id-${i % 7}`] }),
      );
    }
    fs.writeFileSync(logFile(), `${rows.join("\n")}\n`);
  };

  it("超过阈值后压实为单行，统计总量不变", () => {
    fillLines(501);
    resetAccessCache();
    const before = readAccessStats(root, CUBE);
    const beforeTotal = [...before.values()].reduce(
      (sum, s) => sum + s.count,
      0,
    );

    recordAccess(root, CUBE, ["id-0"]); // 触发压实
    resetAccessCache();

    expect(lines()).toHaveLength(1);
    const after = readAccessStats(root, CUBE);
    expect([...after.values()].reduce((sum, s) => sum + s.count, 0)).toBe(
      beforeTotal + 1,
    );
    expect(after.size).toBe(before.size);
  });

  it("压实后仍可继续追加并累加", () => {
    fillLines(501);
    recordAccess(root, CUBE, ["id-0"]);
    const compacted = readAccessStats(root, CUBE).get("id-0")!.count;
    recordAccess(root, CUBE, ["id-0"]);
    expect(readAccessStats(root, CUBE).get("id-0")?.count).toBe(compacted + 1);
    expect(lines()).toHaveLength(2);
  });

  it("未超阈值时不压实", () => {
    fillLines(10);
    recordAccess(root, CUBE, ["id-0"]);
    expect(lines()).toHaveLength(11);
  });

  it("快照行里的坏条目被跳过", () => {
    fs.mkdirSync(path.join(root, CUBE), { recursive: true });
    fs.writeFileSync(
      logFile(),
      `${JSON.stringify({
        t: "2026-01-01T00:00:00.000Z",
        snapshot: {
          ok: [5, "2026-01-01T00:00:00.000Z"],
          "no-array": 3,
          "bad-count": ["x", "2026-01-01T00:00:00.000Z"],
          "zero-count": [0, "2026-01-01T00:00:00.000Z"],
          "no-date": [2, ""],
        },
      })}\n`,
    );
    const stats = readAccessStats(root, CUBE);
    expect([...stats.keys()]).toEqual(["ok"]);
    expect(stats.get("ok")?.count).toBe(5);
  });

  it("不留下 .tmp 残file", () => {
    fillLines(501);
    recordAccess(root, CUBE, ["id-0"]);
    const leftovers = fs
      .readdirSync(path.join(root, CUBE))
      .filter((f) => f.endsWith(".tmp"));
    expect(leftovers).toEqual([]);
  });
});

// 端到端：记账 → 读取 → 影响排序。
// 单测各自绿灯不代表接线正确 —— 这一组把「侧车数据真的进了打分」钉住。
describe("与 quality policy 的联动", () => {
  const node = (id: string): MemoryNode => ({
    id,
    memory: `[DECISION] ${id} 的内容各不相同以避免被近重复折叠 ${id.repeat(6)}`,
    metadata: {
      relativity: 0.8,
      confidence: 0.8,
      type: "DECISION",
      status: "activated",
      updated_at: new Date().toISOString(),
    },
  });

  const rank = (ids: string[]): string[] => {
    const out = applyMemoryQualityPolicy(
      { text_mem: [{ cube_id: CUBE, memories: ids.map(node) }] },
      { accessStats: readAccessStats(root, CUBE) },
    );
    return (out.text_mem![0].memories as MemoryNode[]).map((m) => m.id!);
  };

  it("被显式读取过的记忆排到同等条件的记忆之前", () => {
    expect(rank(["cold", "warm"])).toEqual(["cold", "warm"]); // 无记账时保持输入序
    for (let i = 0; i < 5; i += 1) recordAccess(root, CUBE, ["warm"]);
    expect(rank(["cold", "warm"])[0]).toBe("warm");
  });

  it("不传 accessStats 时侧车数据不生效（选项是唯一入口）", () => {
    for (let i = 0; i < 5; i += 1) recordAccess(root, CUBE, ["warm"]);
    const out = applyMemoryQualityPolicy({
      text_mem: [{ cube_id: CUBE, memories: [node("cold"), node("warm")] }],
    });
    const ranked = out.text_mem![0].memories as MemoryNode[];
    expect(ranked.map((m) => m.metadata?.access_count)).toEqual([undefined, undefined]);
  });

  it("记录自带的 access_count 优先于侧车（后端将来可自行提供）", () => {
    recordAccess(root, CUBE, ["x"]);
    const withOwn = { ...node("x"), metadata: { ...node("x").metadata, access_count: 99 } };
    const out = applyMemoryQualityPolicy(
      { text_mem: [{ cube_id: CUBE, memories: [withOwn] }] },
      { accessStats: readAccessStats(root, CUBE) },
    );
    expect((out.text_mem![0].memories as MemoryNode[])[0].metadata?.access_count).toBe(99);
  });

  it("侧车统计写入 metadata，便于排查", () => {
    recordAccess(root, CUBE, ["x"]);
    const out = applyMemoryQualityPolicy(
      { text_mem: [{ cube_id: CUBE, memories: [node("x")] }] },
      { accessStats: readAccessStats(root, CUBE) },
    );
    const m = (out.text_mem![0].memories as MemoryNode[])[0].metadata!;
    expect(m.access_count).toBe(1);
    expect(typeof m.last_accessed_at).toBe("string");
  });
});
