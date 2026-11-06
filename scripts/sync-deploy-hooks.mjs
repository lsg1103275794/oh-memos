#!/usr/bin/env node
/**
 * Sync the deploy bundle's hook set from the canonical project-memory/hooks/.
 *
 * The bundle under oh-memos-deploy/.claude/skills/project-memory/hooks/ is a
 * copy that ships to users, and it drifted: it still carried the dead
 * expression-matcher and the pre-fix exit code, and it lacked the built-in
 * memory guard entirely. Copying by hand is what let it drift, so this does it.
 *
 * Usage:
 *   node scripts/sync-deploy-hooks.mjs           # report drift, exit 1 if any
 *   node scripts/sync-deploy-hooks.mjs --write   # copy canonical -> bundle
 */

import {
  readFileSync,
  writeFileSync,
  readdirSync,
  existsSync,
  copyFileSync,
} from "node:fs";
import { join } from "node:path";

const SRC = "project-memory/hooks";
const DST = "oh-memos-deploy/.claude/skills/project-memory/hooks";
const write = process.argv.includes("--write");

if (!existsSync(DST)) {
  console.error(`deploy bundle not found at ${DST}`);
  process.exit(1);
}

const drift = [];

// 1. Hook scripts: every canonical node/ script must exist in the bundle, byte-identical.
const srcScripts = readdirSync(join(SRC, "node")).filter((f) =>
  f.endsWith(".js"),
);
for (const name of srcScripts) {
  const a = join(SRC, "node", name);
  const b = join(DST, "node", name);
  if (!existsSync(b)) {
    drift.push({
      what: `missing script: node/${name}`,
      fix: () => copyFileSync(a, b),
    });
    continue;
  }
  if (readFileSync(a, "utf8") !== readFileSync(b, "utf8")) {
    drift.push({
      what: `stale script: node/${name}`,
      fix: () => copyFileSync(a, b),
    });
  }
}

// 2. README.md: the bundle's copy documents the same scripts, so it must match.
// It was not checked before and fell behind (it lacked oh_memos_block_memory_write.js).
const readme = "README.md";
if (readFileSync(join(SRC, readme), "utf8") !== readFileSync(join(DST, readme), "utf8")) {
  drift.push({
    what: `stale ${readme}`,
    fix: () => copyFileSync(join(SRC, readme), join(DST, readme)),
  });
}

// 3. settings-template.json: matchers and handler set must match the canonical file.
const tplName = "settings-template.json";
const srcTpl = JSON.parse(readFileSync(join(SRC, tplName), "utf8"));
const dstPath = join(DST, tplName);
const dstTpl = JSON.parse(readFileSync(dstPath, "utf8"));

// The bundle uses its own <MEMOS_PATH>-relative prefix; compare structure, not paths.
const shape = (tpl) =>
  Object.fromEntries(
    Object.entries(tpl.hooks).map(([ev, arr]) => [
      ev,
      arr.map((e) => ({
        matcher: e.matcher ?? null,
        scripts: (e.hooks ?? [])
          .map((h) => (h.command.match(/([a-z0-9_]+\.js)/i) || [])[1] ?? "?")
          .sort(),
      })),
    ]),
  );

if (JSON.stringify(shape(srcTpl)) !== JSON.stringify(shape(dstTpl))) {
  drift.push({
    what: `${tplName} differs in matchers or handler set`,
    fix: () => {
      // Rewrite the bundle template from canonical, retargeting script paths to
      // the bundle's own layout so <MEMOS_PATH> stays correct for users.
      const next = JSON.parse(JSON.stringify(srcTpl));
      for (const arr of Object.values(next.hooks)) {
        for (const entry of arr) {
          for (const h of entry.hooks ?? []) {
            h.command = h.command.replace(
              /<MEMOS_PATH>\/project-memory\/hooks\//g,
              "<MEMOS_PATH>/.claude/skills/project-memory/hooks/",
            );
          }
        }
      }
      writeFileSync(dstPath, JSON.stringify(next, null, 2) + "\n");
    },
  });
}

if (drift.length === 0) {
  console.log(
    `deploy bundle in sync (${srcScripts.length} scripts + ${readme} + ${tplName})`,
  );
  process.exit(0);
}

if (!write) {
  console.error("deploy bundle has drifted from project-memory/hooks/:\n");
  for (const d of drift) console.error(`  - ${d.what}`);
  console.error("\nRun: node scripts/sync-deploy-hooks.mjs --write");
  process.exit(1);
}

for (const d of drift) {
  d.fix();
  console.log(`  synced: ${d.what}`);
}
console.log(`\n${drift.length} item(s) synced.`);
