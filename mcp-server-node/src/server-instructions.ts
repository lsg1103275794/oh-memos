/**
 * Always-on guidance: the server instructions and the tools kept loaded up
 * front instead of behind tool search.
 *
 * With tool search on, Claude Code loads only tool names and server
 * instructions at session start; a deferred tool's description arrives only
 * after the model searches for it. Codex reads server instructions at
 * initialize and suggests the first 512 characters stand on their own.
 * MEMOS_ALWAYS_LOAD=false turns both off and restores the earlier behaviour.
 */

export const SERVER_INSTRUCTIONS = `oh-memos keeps this project's memory across sessions and clients.

When resuming earlier work, after context compaction, or when the user refers to past work, check memos_context_resume or memos_search before asking them to repeat it. Pass the project root as project_path. Save decisions, fixes and gotchas worth keeping with memos_save.`;

export const ALWAYS_LOAD_TOOLS: ReadonlySet<string> = new Set(["memos_save", "memos_search"]);

export function serverOptions(alwaysLoad: boolean): { instructions?: string } {
  return alwaysLoad ? { instructions: SERVER_INSTRUCTIONS } : {};
}

export function toolMeta(name: string, alwaysLoad: boolean): Record<string, unknown> | undefined {
  return alwaysLoad && ALWAYS_LOAD_TOOLS.has(name) ? { "anthropic/alwaysLoad": true } : undefined;
}
