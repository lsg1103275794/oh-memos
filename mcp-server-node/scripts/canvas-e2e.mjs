// End-to-end smoke test for memos_canvas over real MCP stdio.
// Exercises the four actions plus the traversal guard, against a temp cubes dir.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, readFileSync, existsSync, rmSync } from "node:fs";
import { join } from "node:path";
import { scratchDir } from "./_scratch.mjs";

const root = scratchDir("canvas-e2e-");
const cube = "e2e_probe_cube";
mkdirSync(join(root, cube), { recursive: true });
writeFileSync(join(root, cube, "config.json"), "{}", "utf8");

const child = spawn(process.execPath, ["dist/index.js"], {
  stdio: ["pipe", "pipe", "pipe"],
  env: {
    ...process.env,
    MEMOS_URL: "http://localhost:18000",
    MEMOS_USER: "dev_user",
    MEMOS_DEFAULT_CUBE: cube,
    MEMOS_CUBES_DIR: root,
    MEMOS_ENV_FILE: join(root, "nonexistent.env"),
  },
});

let stderr = "";
child.stderr.on("data", (d) => {
  stderr += d.toString();
});

let buf = "";
const pending = new Map();
child.stdout.on("data", (chunk) => {
  buf += chunk.toString();
  let nl;
  while ((nl = buf.indexOf("\n")) !== -1) {
    const line = buf.slice(0, nl).trim();
    buf = buf.slice(nl + 1);
    if (!line) continue;
    try {
      const msg = JSON.parse(line);
      const resolve = pending.get(msg.id);
      if (resolve) {
        pending.delete(msg.id);
        resolve(msg);
      }
    } catch {
      /* not a JSON-RPC line */
    }
  }
});

let nextId = 1;
function rpc(method, params) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => reject(new Error(`timeout on ${method}`)),
      25000,
    );
    pending.set(id, (msg) => {
      clearTimeout(timer);
      resolve(msg);
    });
    child.stdin.write(
      JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n",
    );
  });
}

const text = (r) =>
  r.result?.content?.map((c) => c.text).join("\n") ??
  JSON.stringify(r.error ?? r);

let failures = 0;
function check(label, cond, detail = "") {
  if (cond) {
    console.log(`  ok   ${label}`);
  } else {
    console.log(`  FAIL ${label}${detail ? ` — ${detail}` : ""}`);
    failures++;
  }
}

try {
  await rpc("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "canvas-e2e", version: "0" },
  });
  child.stdin.write(
    JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) +
      "\n",
  );

  const tools = await rpc("tools/list", {});
  const names = (tools.result?.tools ?? []).map((t) => t.name);
  check(
    "memos_canvas is advertised",
    names.includes("memos_canvas"),
    names.join(","),
  );

  const canvasTool = (tools.result?.tools ?? []).find(
    (t) => t.name === "memos_canvas",
  );
  check(
    "declared as a write tool",
    canvasTool?.annotations?.readOnlyHint === false,
    JSON.stringify(canvasTool?.annotations),
  );

  const call = (args) =>
    rpc("tools/call", { name: "memos_canvas", arguments: args });

  const empty = text(await call({ action: "list", cube_id: cube }));
  check(
    "list is empty initially",
    empty.includes("No canvases yet"),
    empty.slice(0, 120),
  );

  const opened = text(
    await call({ action: "open", goal: "wire up the canvas", cube_id: cube }),
  );
  check(
    "open creates 000-wire-up-the-canvas",
    opened.includes("000-wire-up-the-canvas"),
    opened.slice(0, 200),
  );

  const name = "000-wire-up-the-canvas";
  const n1 = text(
    await call({
      action: "update",
      name,
      cube_id: cube,
      summary: "read the source",
      status: "done",
      ref: "note:done already",
    }),
  );
  check("first append gets 000-N1", n1.includes("000-N1"), n1.slice(0, 160));

  const n2 = text(
    await call({
      action: "update",
      name,
      cube_id: cube,
      summary: "write the tests",
      status: "doing",
    }),
  );
  check("second append gets 000-N2", n2.includes("000-N2"), n2.slice(0, 160));

  const edited = text(
    await call({
      action: "update",
      name,
      cube_id: cube,
      node_id: "000-N2",
      status: "done",
    }),
  );
  check(
    "node_id edits in place, no N3",
    edited.includes("000-N2") && !edited.includes("000-N3"),
    edited.slice(0, 200),
  );

  const badRef = text(
    await call({
      action: "update",
      name,
      cube_id: cube,
      summary: "x",
      ref: "/etc/passwd",
    }),
  );
  check(
    "schemeless ref rejected",
    badRef.includes("must start with a scheme"),
    badRef.slice(0, 160),
  );

  const badStatus = text(
    await call({
      action: "update",
      name,
      cube_id: cube,
      summary: "x",
      status: "sideways",
    }),
  );
  check(
    "invalid status rejected",
    badStatus.toLowerCase().includes("status"),
    badStatus.slice(0, 160),
  );

  const traversal = text(
    await call({
      action: "show",
      name: "../../../../etc/passwd",
      cube_id: cube,
    }),
  );
  check(
    "traversal refused",
    /bare name|no usable characters|not a path/i.test(traversal),
    traversal.slice(0, 200),
  );

  const missing = text(
    await call({ action: "show", name: "000-nope", cube_id: cube }),
  );
  check(
    "missing canvas reported",
    missing.includes("not found"),
    missing.slice(0, 160),
  );

  const shown = text(await call({ action: "show", name, cube_id: cube }));
  check(
    "show renders both nodes",
    shown.includes("000-N1") && shown.includes("000-N2"),
    shown.slice(0, 240),
  );
  check("show reports 2 done", shown.includes("2 done"), shown.slice(0, 240));

  const listed = text(await call({ action: "list", cube_id: cube }));
  check("list shows the canvas", listed.includes(name), listed.slice(0, 200));

  const onDisk = join(root, cube, "canvas", `${name}.mmd`);
  check("file written to cube canvas dir", existsSync(onDisk), onDisk);
  if (existsSync(onDisk)) {
    const raw = readFileSync(onDisk, "utf8");
    check(
      "file is mermaid with meta header",
      raw.startsWith("%%{") && raw.includes("graph LR"),
      raw.slice(0, 90),
    );
    check(
      "ref persisted",
      raw.includes("note:done already"),
      raw.slice(0, 300),
    );
  }

  // A ref carrying a quote is the case the old escaping mangled: `"` had to
  // leave the Mermaid label, but it must come back verbatim through `show`.
  const quoted = text(
    await call({
      action: "update",
      name,
      cube_id: cube,
      summary: "quote round trip",
      ref: 'note:returned "No canvases yet."',
    }),
  );
  check(
    "quoted ref echoed verbatim",
    quoted.includes('note:returned "No canvases yet."'),
    quoted.slice(0, 240),
  );
  const reShown = text(await call({ action: "show", name, cube_id: cube }));
  check(
    "quoted ref survives a reload",
    reShown.includes('note:returned "No canvases yet."'),
    reShown.slice(0, 400),
  );
  check(
    "no escape leaked into output",
    !reShown.includes("u0022"),
    reShown.slice(0, 400),
  );

  // delete: an unfinished canvas is refused, then accepted with confirm.
  const openWork = text(
    await call({ action: "open", goal: "unfinished work", cube_id: cube }),
  );
  check(
    "second canvas opens as 001",
    openWork.includes("001-unfinished-work"),
    openWork.slice(0, 200),
  );
  const name2 = "001-unfinished-work";
  await call({
    action: "update",
    name: name2,
    cube_id: cube,
    summary: "still going",
    status: "doing",
  });

  const refused = text(
    await call({ action: "delete", name: name2, cube_id: cube }),
  );
  check(
    "delete refuses unfinished canvas",
    /unfinished node/i.test(refused),
    refused.slice(0, 240),
  );
  check(
    "refusal names the confirm escape hatch",
    refused.includes("confirm=true"),
    refused.slice(0, 240),
  );
  check(
    "refused delete left the file",
    existsSync(join(root, cube, "canvas", `${name2}.mmd`)),
  );

  const confirmed = text(
    await call({ action: "delete", name: name2, cube_id: cube, confirm: true }),
  );
  check(
    "confirm=true deletes it",
    /deleted canvas/i.test(confirmed),
    confirmed.slice(0, 240),
  );
  check(
    "file removed from disk",
    !existsSync(join(root, cube, "canvas", `${name2}.mmd`)),
  );

  const goneList = text(await call({ action: "list", cube_id: cube }));
  check(
    "deleted canvas leaves the listing",
    !goneList.includes(name2),
    goneList.slice(0, 240),
  );
  check(
    "surviving canvas still listed",
    goneList.includes(name),
    goneList.slice(0, 240),
  );

  const deleteMissing = text(
    await call({ action: "delete", name: "099-never-existed", cube_id: cube }),
  );
  check(
    "delete reports a missing canvas",
    deleteMissing.includes("not found"),
    deleteMissing.slice(0, 200),
  );

  const deleteTraversal = text(
    await call({
      action: "delete",
      name: "../../../../etc/passwd",
      cube_id: cube,
    }),
  );
  check(
    "delete refuses traversal",
    /bare name|no usable characters|not a path/i.test(deleteTraversal),
    deleteTraversal.slice(0, 200),
  );

  // A canvas with nothing unfinished needs no confirm — that asymmetry is the
  // point of the gate, so pin it.
  const doneOnly = text(
    await call({ action: "open", goal: "all done here", cube_id: cube }),
  );
  const name3 = "002-all-done-here";
  check(
    "third canvas opens as 002",
    doneOnly.includes(name3),
    doneOnly.slice(0, 200),
  );
  await call({
    action: "update",
    name: name3,
    cube_id: cube,
    summary: "finished",
    status: "done",
  });
  const noConfirm = text(
    await call({ action: "delete", name: name3, cube_id: cube }),
  );
  check(
    "finished canvas deletes without confirm",
    /deleted canvas/i.test(noConfirm),
    noConfirm.slice(0, 240),
  );

  const emptyDelete = text(await call({ action: "delete", cube_id: cube }));
  check(
    "delete without name is rejected",
    /name.*required/i.test(emptyDelete),
    emptyDelete.slice(0, 200),
  );

  // A goal long enough that prefix + slug would overflow the slug cap. The name
  // `open` reports has to be the name `list` shows and the file that exists —
  // previously `open` returned one character more than any of those.
  const longGoal =
    "verify canvas delete and ref escaping over a live mcp connection today";
  const longOpened = text(
    await call({ action: "open", goal: longGoal, cube_id: cube }),
  );
  const longName = (longOpened.match(/Canvas `([^`]+)` created/) || [])[1];
  check(
    "long goal reports a name",
    Boolean(longName),
    longOpened.slice(0, 200),
  );
  if (longName) {
    check(
      "long name fits the slug cap",
      longName.length <= 60,
      `${longName} (${longName.length})`,
    );
    check(
      "long name exists on disk as reported",
      existsSync(join(root, cube, "canvas", `${longName}.mmd`)),
      longName,
    );
    const longListed = text(await call({ action: "list", cube_id: cube }));
    check(
      "list shows the same name open reported",
      longListed.includes(`\`${longName}\``),
      longListed.slice(0, 400),
    );
    const longShown = text(
      await call({ action: "show", name: longName, cube_id: cube }),
    );
    // Passes with or without the composition fix, because canvasPath truncates
    // idempotently — kept so that "fixing" this by making canvasPath throw on a
    // lossy name would be caught as the regression it would be.
    check(
      "reported name still routes to its canvas",
      longShown.includes(longGoal),
      longShown.slice(0, 240),
    );
    check(
      "reported name still routes to delete",
      /deleted canvas/i.test(
        text(await call({ action: "delete", name: longName, cube_id: cube })),
      ),
    );
  }

  // The action enum is enforced by the SDK's schema validation, so a bad action
  // never reaches the handler. Assert the rejection, not the handler's message.
  const unknown = text(await call({ action: "teleport", cube_id: cube }));
  check(
    "unknown action rejected",
    /validation|invalid/i.test(unknown),
    unknown.slice(0, 120),
  );
} catch (err) {
  console.log(`  FAIL harness error — ${err.message}`);
  console.log(`  stderr: ${stderr.slice(0, 600)}`);
  failures++;
} finally {
  child.kill();
  // The killed server may still hold a file for a moment; the scratch sweep
  // removes anything left behind after a day.
  try {
    rmSync(root, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
  } catch {}
}

console.log(
  failures === 0
    ? "\nall canvas e2e checks passed"
    : `\n${failures} check(s) failed`,
);
process.exit(failures === 0 ? 0 : 1);
