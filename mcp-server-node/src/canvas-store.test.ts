/**
 * canvas-store tests.
 *
 * The security-relevant unit here is `canvasPath`: it turns caller-supplied text
 * into a filesystem path, so it is the one place where a traversal could land.
 * It is a pure function of (root, cubeId, name), which is what makes it testable
 * without touching disk.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { rmSync, writeFileSync, mkdirSync, readFileSync } from "node:fs";
import { join, sep } from "node:path";

import {
  canvasPath,
  deleteCanvas,
  listCanvases,
  loadCanvas,
  nextPrefix,
  saveCanvas,
  CanvasPathError,
} from "./canvas-store.js";
import { renderCanvas, type Canvas } from "./canvas-format.js";
import { scratchDir } from "../scripts/_scratch.mjs";

const CUBE = "oh_memos_cube";

let root: string;

beforeEach(() => {
  root = scratchDir("canvas-test-");
});

afterEach(() => {
  rmSync(root, { recursive: true, force: true });
});

function canvas(overrides: Partial<Canvas> = {}): Canvas {
  return {
    prefix: "000",
    taskGoal: "goal",
    createdTime: "2026-08-13T10:00:00.000Z",
    updatedTime: "2026-08-13T10:00:00.000Z",
    nodes: [{ id: "000-N1", status: "todo", summary: "s", ref: null }],
    ...overrides,
  };
}

// ============================================================================
// canvasPath — containment
// ============================================================================

describe("canvasPath", () => {
  it("builds a path under the cube's canvas dir", () => {
    const p = canvasPath(root, CUBE, "000-my-task");
    expect(p.startsWith(root)).toBe(true);
    expect(p).toContain(`${sep}canvas${sep}`);
    expect(p.endsWith(".mmd")).toBe(true);
  });

  it("rejects a traversal attempt in the canvas name", () => {
    expect(() => canvasPath(root, CUBE, "../../../etc/passwd")).toThrow(
      CanvasPathError,
    );
  });

  it("rejects an absolute path as the canvas name", () => {
    expect(() => canvasPath(root, CUBE, "C:/Windows/System32/x")).toThrow(
      CanvasPathError,
    );
    expect(() => canvasPath(root, CUBE, "/etc/shadow")).toThrow(
      CanvasPathError,
    );
  });

  it("rejects a traversal attempt in the cube id", () => {
    // cube_id reaches us from a derived project path, so it is caller data too.
    expect(() => canvasPath(root, "../../evil", "000-x")).toThrow(
      CanvasPathError,
    );
  });

  it("rejects a separator smuggled into the name", () => {
    expect(() => canvasPath(root, CUBE, "sub/dir")).toThrow(CanvasPathError);
    expect(() => canvasPath(root, CUBE, "sub\\dir")).toThrow(CanvasPathError);
  });

  it("rejects a name that slugifies to nothing", () => {
    expect(() => canvasPath(root, CUBE, "///")).toThrow(CanvasPathError);
    expect(() => canvasPath(root, CUBE, "")).toThrow(CanvasPathError);
  });

  it("rejects a NUL byte", () => {
    expect(() => canvasPath(root, CUBE, "a\u0000b")).toThrow(CanvasPathError);
  });

  it("is deterministic for the same input", () => {
    expect(canvasPath(root, CUBE, "000-x")).toBe(
      canvasPath(root, CUBE, "000-x"),
    );
  });
});

// ============================================================================
// save / load
// ============================================================================

describe("saveCanvas / loadCanvas", () => {
  it("round trips through disk", () => {
    const c = canvas();
    saveCanvas(root, CUBE, "000-task", c);
    expect(loadCanvas(root, CUBE, "000-task")).toEqual(c);
  });

  it("creates the canvas directory on first save", () => {
    saveCanvas(root, CUBE, "000-task", canvas());
    expect(loadCanvas(root, CUBE, "000-task")).not.toBeNull();
  });

  it("returns null for a canvas that does not exist", () => {
    expect(loadCanvas(root, CUBE, "000-absent")).toBeNull();
  });

  it("overwrites an existing canvas in place", () => {
    saveCanvas(root, CUBE, "000-task", canvas({ taskGoal: "first" }));
    saveCanvas(root, CUBE, "000-task", canvas({ taskGoal: "second" }));
    expect(loadCanvas(root, CUBE, "000-task")?.taskGoal).toBe("second");
  });

  it("leaves no temp file behind after a save", () => {
    saveCanvas(root, CUBE, "000-task", canvas());
    const names = listCanvases(root, CUBE).map((e) => e.name);
    expect(names.some((n) => n.includes(".tmp"))).toBe(false);
  });

  it("propagates a path error rather than writing somewhere else", () => {
    expect(() => saveCanvas(root, CUBE, "../escape", canvas())).toThrow(
      CanvasPathError,
    );
  });

  it("recovers a canvas whose file was damaged, without throwing", () => {
    const dir = join(root, CUBE, "canvas");
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, "000-broken.mmd"), "not a canvas", "utf8");
    const loaded = loadCanvas(root, CUBE, "000-broken");
    expect(loaded).not.toBeNull();
    expect(loaded?.nodes).toEqual([]);
  });

  it("writes utf8 so a CJK goal survives", () => {
    const c = canvas({ taskGoal: "实现符号化画布" });
    saveCanvas(root, CUBE, "000-cjk", c);
    expect(loadCanvas(root, CUBE, "000-cjk")?.taskGoal).toBe("实现符号化画布");
  });

  it("writes the rendered form verbatim", () => {
    const c = canvas();
    const p = saveCanvas(root, CUBE, "000-task", c);
    expect(readFileSync(p, "utf8")).toBe(renderCanvas(c));
  });
});

// ============================================================================
// deleteCanvas
// ============================================================================

describe("deleteCanvas", () => {
  it("removes a saved canvas and reports it did", () => {
    saveCanvas(root, CUBE, "000-task", canvas());
    expect(deleteCanvas(root, CUBE, "000-task")).toBe(true);
    expect(loadCanvas(root, CUBE, "000-task")).toBeNull();
  });

  it("reports false for a canvas that was never there", () => {
    // The handler distinguishes "removed" from "nothing to remove", so a
    // missing file must not look like a successful delete.
    expect(deleteCanvas(root, CUBE, "000-absent")).toBe(false);
  });

  it("is idempotent — a second delete is simply false", () => {
    saveCanvas(root, CUBE, "000-task", canvas());
    expect(deleteCanvas(root, CUBE, "000-task")).toBe(true);
    expect(deleteCanvas(root, CUBE, "000-task")).toBe(false);
  });

  it("refuses a traversal-shaped name rather than unlinking outside the dir", () => {
    expect(() => deleteCanvas(root, CUBE, "../../../etc/passwd")).toThrow(
      CanvasPathError,
    );
  });

  it("refuses an absolute path", () => {
    expect(() => deleteCanvas(root, CUBE, "C:/Windows/System32/x")).toThrow(
      CanvasPathError,
    );
  });

  it("refuses a traversal-shaped cube id", () => {
    expect(() => deleteCanvas(root, "../../evil", "000-x")).toThrow(
      CanvasPathError,
    );
  });

  it("leaves the cube's other canvases untouched", () => {
    saveCanvas(root, CUBE, "000-a", canvas());
    saveCanvas(root, CUBE, "001-b", canvas({ prefix: "001" }));
    deleteCanvas(root, CUBE, "000-a");
    expect(listCanvases(root, CUBE).map((e) => e.name)).toEqual(["001-b"]);
  });

  it("does not hand the deleted canvas's prefix to the next one", () => {
    // Prefixes are spent, not recycled: `000-N3` may be cited from a commit
    // message or a memory body, and reissuing 000 would silently repoint it at
    // a different canvas's node.
    saveCanvas(root, CUBE, "000-a", canvas({ prefix: "000" }));
    deleteCanvas(root, CUBE, "000-a");
    expect(nextPrefix(root, CUBE)).toBe("001");
  });

  it("does not reissue a prefix after the whole cube is emptied", () => {
    saveCanvas(root, CUBE, "000-a", canvas({ prefix: "000" }));
    saveCanvas(root, CUBE, "001-b", canvas({ prefix: "001" }));
    deleteCanvas(root, CUBE, "000-a");
    deleteCanvas(root, CUBE, "001-b");
    expect(listCanvases(root, CUBE)).toEqual([]);
    expect(nextPrefix(root, CUBE)).toBe("002");
  });

  it("does not reissue the prefix of a canvas that predates the watermark", () => {
    // A cube written before the watermark existed has no `.prefix-hwm`. Deleting
    // its only canvas leaves nothing on disk naming the prefix, so the delete
    // itself has to record it — otherwise allocation restarts at 000 and the new
    // canvas mints ids that collide with the deleted one's.
    saveCanvas(root, CUBE, "000-legacy", canvas({ prefix: "000" }));
    rmSync(join(root, CUBE, "canvas", ".prefix-hwm"), { force: true });
    deleteCanvas(root, CUBE, "000-legacy");
    expect(nextPrefix(root, CUBE)).toBe("001");
  });

  it("keeps the watermark out of the canvas listing", () => {
    saveCanvas(root, CUBE, "000-a", canvas());
    deleteCanvas(root, CUBE, "000-a");
    // The watermark file lives in the same directory; it must not read as a
    // canvas named ".prefix-hwm".
    expect(listCanvases(root, CUBE)).toEqual([]);
  });
});

// ============================================================================
// listCanvases
// ============================================================================

describe("listCanvases", () => {
  it("returns empty when the cube has no canvas dir", () => {
    expect(listCanvases(root, CUBE)).toEqual([]);
  });

  it("lists saved canvases", () => {
    saveCanvas(root, CUBE, "000-a", canvas({ prefix: "000" }));
    saveCanvas(root, CUBE, "001-b", canvas({ prefix: "001", nodes: [] }));
    expect(
      listCanvases(root, CUBE)
        .map((e) => e.name)
        .sort(),
    ).toEqual(["000-a", "001-b"]);
  });

  it("ignores files that are not canvases", () => {
    const dir = join(root, CUBE, "canvas");
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, "notes.txt"), "hello", "utf8");
    saveCanvas(root, CUBE, "000-a", canvas());
    expect(listCanvases(root, CUBE).map((e) => e.name)).toEqual(["000-a"]);
  });

  it("carries the parsed canvas so the caller need not re-read", () => {
    saveCanvas(root, CUBE, "000-a", canvas({ taskGoal: "carried" }));
    expect(listCanvases(root, CUBE)[0].canvas.taskGoal).toBe("carried");
  });

  it("sorts by name so output is stable across calls", () => {
    saveCanvas(root, CUBE, "002-c", canvas());
    saveCanvas(root, CUBE, "000-a", canvas());
    saveCanvas(root, CUBE, "001-b", canvas());
    expect(listCanvases(root, CUBE).map((e) => e.name)).toEqual([
      "000-a",
      "001-b",
      "002-c",
    ]);
  });

  it("does not throw for a traversal-shaped cube id", () => {
    expect(listCanvases(root, "../../evil")).toEqual([]);
  });
});

// ============================================================================
// nextPrefix
// ============================================================================

describe("nextPrefix", () => {
  it("starts at 000 for an empty cube", () => {
    expect(nextPrefix(root, CUBE)).toBe("000");
  });

  it("increments past the highest existing prefix", () => {
    saveCanvas(root, CUBE, "000-a", canvas({ prefix: "000" }));
    saveCanvas(root, CUBE, "001-b", canvas({ prefix: "001" }));
    expect(nextPrefix(root, CUBE)).toBe("002");
  });

  it("does not reuse a prefix after a gap", () => {
    saveCanvas(root, CUBE, "000-a", canvas({ prefix: "000" }));
    saveCanvas(root, CUBE, "005-b", canvas({ prefix: "005" }));
    expect(nextPrefix(root, CUBE)).toBe("006");
  });

  it("stays three digits", () => {
    saveCanvas(root, CUBE, "042-a", canvas({ prefix: "042" }));
    expect(nextPrefix(root, CUBE)).toBe("043");
  });

  it("does not overflow past 999", () => {
    saveCanvas(root, CUBE, "999-a", canvas({ prefix: "999" }));
    expect(nextPrefix(root, CUBE)).toBeNull();
  });

  it("stays exhausted after the 999th canvas is deleted", () => {
    // Otherwise deleting the last canvas would reopen 999 and mint a second
    // batch of 999-N* ids.
    saveCanvas(root, CUBE, "999-a", canvas({ prefix: "999" }));
    deleteCanvas(root, CUBE, "999-a");
    expect(nextPrefix(root, CUBE)).toBeNull();
  });

  it("falls back to the files when the watermark is missing", () => {
    // A cube created before the watermark existed must still allocate sanely.
    saveCanvas(root, CUBE, "000-a", canvas({ prefix: "000" }));
    saveCanvas(root, CUBE, "003-b", canvas({ prefix: "003" }));
    rmSync(join(root, CUBE, "canvas", ".prefix-hwm"), { force: true });
    expect(nextPrefix(root, CUBE)).toBe("004");
  });

  it("falls back to the files when the watermark is corrupt", () => {
    saveCanvas(root, CUBE, "002-a", canvas({ prefix: "002" }));
    writeFileSync(
      join(root, CUBE, "canvas", ".prefix-hwm"),
      "not a number",
      "utf8",
    );
    expect(nextPrefix(root, CUBE)).toBe("003");
  });

  it("ignores a watermark outside the valid range", () => {
    saveCanvas(root, CUBE, "001-a", canvas({ prefix: "001" }));
    writeFileSync(join(root, CUBE, "canvas", ".prefix-hwm"), "4242", "utf8");
    expect(nextPrefix(root, CUBE)).toBe("002");
  });

  it("takes the higher of watermark and files", () => {
    // A canvas copied in by hand can exceed the watermark; it must still win.
    saveCanvas(root, CUBE, "001-a", canvas({ prefix: "001" }));
    const dir = join(root, CUBE, "canvas");
    writeFileSync(
      join(dir, "007-pasted.mmd"),
      renderCanvas(canvas({ prefix: "007" })),
      "utf8",
    );
    expect(nextPrefix(root, CUBE)).toBe("008");
  });
});
