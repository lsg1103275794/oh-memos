/**
 * Temp directories for tests and smoke scripts.
 *
 * Contract: .agents/contracts/common/artifacts.md. Test temp files go under
 * <repo>/runtime/scratch/node/ instead of the system temp dir, so they stay in
 * one ignored place. Callers still remove their own directories; leftovers
 * from crashed runs older than a day are swept when this module loads.
 */
import { mkdirSync, mkdtempSync, readdirSync, rmSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("../..", import.meta.url)));
export const SCRATCH = join(ROOT, "runtime", "scratch", "node");
const STALE_MS = 864e5;

export function scratchDir(prefix) {
  mkdirSync(SCRATCH, { recursive: true });
  return mkdtempSync(join(SCRATCH, prefix));
}

/** Removes entries older than a day; a concurrent run's fresh directory is kept. */
export function sweepStale(now = Date.now()) {
  let names;
  try {
    names = readdirSync(SCRATCH);
  } catch {
    return;
  }
  for (const name of names) {
    const path = join(SCRATCH, name);
    try {
      if (now - statSync(path).mtimeMs > STALE_MS) rmSync(path, { recursive: true, force: true });
    } catch {
      // Another process may have removed it first.
    }
  }
}

sweepStale();
