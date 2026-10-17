# oh-memos-mcp

[![npm version](https://img.shields.io/npm/v/oh-memos-mcp.svg)](https://www.npmjs.com/package/oh-memos-mcp)
[![Node.js >= 20](https://img.shields.io/badge/node-%3E%3D20-brightgreen)](https://nodejs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

MCP Server for **oh-memos** — Intelligent Persistent Memory for AI Assistants.

Pure Node.js. No Python required.

> **3.0:** requires Node.js 20+, serves legacy 2025-era and MCP `2026-07-28`
> clients from the same stdio package, and requires no data migration. Still on
> Node 18? Pin `oh-memos-mcp@2` until you can upgrade the runtime.

---

## Prerequisites

- **Node.js 20 or newer**

```bash
npm i -g oh-memos-mcp       # 3.x, npm latest — needs Node.js 20+
npm i -g oh-memos-mcp@2     # 2.x maintenance line — still runs on Node.js 18
```

oh-memos backend API must be running before connecting this MCP server:

- **oh-memos API** on `http://localhost:18000`
- **Neo4j** on `localhost:7687` (Knowledge Graph)
- **Qdrant** on `localhost:6333` (Vector Search)

> Start all services: run `scripts\local\start.bat` from the [oh-memos repo](https://github.com/lsg1103275794/oh-memos).

---

## Quick Start

Install once, then point the client at the installed entry point:

```bash
npm install -g oh-memos-mcp
npm root -g          # prints the directory used in "args" below
```

```json
{
  "mcpServers": {
    "oh-memos": {
      "command": "node",
      "args": ["<npm root -g>/oh-memos-mcp/dist/index.js"],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "/path/to/oh-memos/data/oh-memos_cubes",
        "MEMOS_ENV_FILE": "/path/to/oh-memos/.env"
      }
    }
  }
}
```

To upgrade, reinstall globally — the config needs no edit:

```bash
npm install -g oh-memos-mcp@latest
```

Then restart the client. A running MCP server is never swapped mid-session: the
stdio pipe is bound when the client starts, so an upgrade takes effect only after
the client restarts.

### Why not `npx`

`npx -y oh-memos-mcp@<version>` also works and is fine for a one-off trial, but it
costs two extra processes per client — `cmd`/`sh` → `npx-cli` (node) → `cmd`/`sh` →
server (node), versus a direct launch's two. With several MCP clients open at once
that overhead is measurable: on one Windows machine running seven clients, the npx
wrappers alone held ~360 MB. `npx` also pins the version inside every client
config, so upgrading means editing each one.

| | `npx -y oh-memos-mcp@x.y.z` | `node <npm root -g>/oh-memos-mcp/dist/index.js` |
|---|---|---|
| Processes per client | 4 | 2 |
| Upgrade | edit every config | `npm i -g oh-memos-mcp@latest` |
| Version source | the config | the global install |

A third option is to point `args` at a checkout's `dist/index.js`. That is the
lowest-overhead choice for working *on* oh-memos — `npm run build` takes effect on
the next client restart, with no publish — but the client then breaks if the
checkout moves or its build output is stale.

Or use a `.env` file in your working directory (the server auto-discovers it when
the working directory is the project root):

```bash
cp node_modules/oh-memos-mcp/.env.example .env
# Edit .env with your paths
node "$(npm root -g)/oh-memos-mcp/dist/index.js"
```

---

## Configuration Examples

The `args` path below assumes npm's **default** global prefix for each platform.
A custom prefix (nvm, fnm, Volta, a hand-set `prefix`) puts the package
elsewhere, so confirm with `npm root -g` and use what it prints:

```bash
node -e "console.log(require('path').join(process.argv[1],'oh-memos-mcp/dist/index.js'))" "$(npm root -g)"
```

### Linux / macOS

```json
{
  "mcpServers": {
    "oh-memos": {
      "command": "node",
      "args": ["/usr/local/lib/node_modules/oh-memos-mcp/dist/index.js"],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "/home/user/oh-memos/data/oh-memos_cubes",
        "MEMOS_ENV_FILE": "/home/user/oh-memos/.env"
      }
    }
  }
}
```

### Windows

```json
{
  "mcpServers": {
    "oh-memos": {
      "command": "node",
      "args": ["C:/Users/you/AppData/Roaming/npm/node_modules/oh-memos-mcp/dist/index.js"],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "G:/test/oh-memos/data/oh-memos_cubes",
        "MEMOS_ENV_FILE": "G:/test/oh-memos/.env"
      }
    }
  }
}
```

### WSL2

```json
{
  "mcpServers": {
    "oh-memos": {
      "command": "node",
      "args": ["/usr/lib/node_modules/oh-memos-mcp/dist/index.js"],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "/mnt/g/test/oh-memos/data/oh-memos_cubes",
        "MEMOS_ENV_FILE": "/mnt/g/test/oh-memos/.env"
      }
    }
  }
}
```

### With `alwaysAllow` (skip per-tool confirmation)

`alwaysAllow` matches **tool names**, so a call form like
`memos_admin(action=list_cubes)` matches nothing — list the bare name and every
action of that tool is auto-approved.

`memos_delete` is deliberately absent below. Auto-approving it means memories can
be deleted without a prompt; add it only if you have decided you want that.

```json
{
  "mcpServers": {
    "oh-memos": {
      "type": "stdio",
      "command": "node",
      "args": ["<npm root -g>/oh-memos-mcp/dist/index.js"],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_USER": "dev_user",
        "MEMOS_DEFAULT_CUBE": "dev_cube",
        "MEMOS_CUBES_DIR": "/path/to/oh-memos/data/oh-memos_cubes",
        "MEMOS_ENV_FILE": "/path/to/oh-memos/.env"
      },
      "alwaysAllow": [
        "memos_context_resume",
        "memos_search",
        "memos_save",
        "memos_list_v2",
        "memos_get",
        "memos_suggest",
        "memos_think",
        "memos_graph",
        "memos_admin",
        "memos_export_wiki",
        "memos_canvas"
      ]
    }
  }
}
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MEMOS_URL` | Yes | — | oh-memos API base URL |
| `MEMOS_USER` | Yes | — | Default user ID |
| `MEMOS_DEFAULT_CUBE` | Yes | — | Default memory cube ID |
| `MEMOS_CUBES_DIR` | Yes | — | Absolute path to cubes storage directory |
| `MEMOS_TIMEOUT_TOOL` | No | `300` | Tool call timeout (seconds) |
| `MEMOS_TIMEOUT_STARTUP` | No | `30` | API startup wait timeout (seconds) |
| `MEMOS_TIMEOUT_HEALTH` | No | `5` | Health check timeout (seconds) |
| `MEMOS_API_WAIT_MAX` | No | `60` | Max time to wait for API on startup (seconds) |
| `MEMOS_ENABLE_DELETE` | No | `false` | Enable `memos_delete` tool |
| `NEO4J_HTTP_URL` | No | — | Neo4j HTTP endpoint (for direct graph queries) |
| `NEO4J_USER` | No | — | Neo4j username |
| `NEO4J_PASSWORD` | No | — | Neo4j password |
| `MEMOS_ENV_FILE` | No | — | Explicit path to a `.env` file. Highest priority — see below |

### Mode and provider

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MEMOS_MODE` | No | `full` | `lite` runs the local JSONL provider with no API, Python, Neo4j, or Qdrant. `full` uses the HTTP backend |
| `MEMOS_PROVIDER` | No | `local` when `MEMOS_MODE=lite`, else `api` | Storage backend. Set explicitly only to override the mode-derived default |
| `MEMOS_LOG_LEVEL` | No | `info` | `debug` / `info` / `warning` / `error`. Logs go to stderr so they never corrupt the stdio JSON-RPC stream |

`MEMOS_URL` is required for Full mode and unused in Lite.

### Save acknowledgement and background parsing

In Full mode with the `tree_text` backend, `memos_save` returns after the
original text and its vector have been confirmed in storage. LLM extraction
continues in the background, even when a model call takes several minutes.
The response contains the stored ID; the API adds `vector_saved: true`,
`enrichment_status: "pending"`, and `queued: false`. Here `queued` describes
the memory write, which has already completed.

Parsing adds the key, tags, background, and extracted facts to that same record.
It preserves the original text, vector, ID, creation time, and explicit source
metadata. Graph conflict handling links these originals instead of merging or
deleting them. Identical retries target the same ID.

Two background consumers process persisted tasks. A failed parse leaves the
saved memory available and retries after 30 and 60 seconds; three completed
failed attempts stop automatic retries. Interrupted attempts can resume after
restart, including local projects restored from the cube registry. Parse status
and the exception type are stored as `enrichment_*` metadata.

This API path does not depend on `MOS_TYPED_SAVE_FAST` or the memory scheduler.
Existing library, chat/document ingestion, and Lite behavior remain available.
Upgrade/restart the API and reconnect MCP clients after rebuilding the Node
server. Older APIs without the additive fields remain compatible. An explicit
unconfirmed vector result is rejected; response timeouts report `API_TIMEOUT`
and do not automatically replay writes.

### Retrieval behaviour (3.1.x)

These change what search returns. All are off or conservative by default, so
upgrading never silently changes ranking.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MEMOS_SPREAD_ACTIVATION` | No | `false` | One-hop graph spreading activation. When on, a search also returns memories reachable from its direct hits over `CAUSE` / `CONDITION` / `RELATE` edges, annotated ` · via CAUSE from <first 8 chars of the source id>`. Full mode only — it queries Neo4j directly, so `NEO4J_HTTP_URL`, `NEO4J_USER`, and `NEO4J_PASSWORD` must all resolve |
| `MEMOS_SHOW_WORKING_MEMORY` | No | `false` | Show the scheduler's `WorkingMemory` tier. Chat/document and legacy ingestion can create short-term copies alongside long-term memories; hiding this tier avoids displaying those pairs. Vector-first content saves create one original record. Debugging only |
| `MEMOS_AUTO_CAPTURE` | No | `false` | Accept auto-captured memories. Auto-captured records are also ranked below explicit saves |

> **Spreading activation degrades silently without Neo4j credentials.** Retrieval
> still returns memories and logs nothing unusual — you simply get no ` via `
> annotations. If you enabled the switch and see no annotations, check that the
> Neo4j variables actually reach the server (under `npx`, that means
> `MEMOS_ENV_FILE`), not that the feature is missing.

Ranking that needs no configuration: per-type exponential decay (a `PROGRESS`
note ages out in weeks, a `DECISION` stays relevant for years), access
reinforcement, and near-duplicate folding with per-type thresholds. Folded
duplicates are reported as ` · folded N: <ids>` rather than dropped.

### Lite embeddings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MEMOS_LITE_EMBED` | No | `auto` | `off` forces lexical search. `auto` uses Ollama embeddings when reachable and falls back to lexical |
| `MEMOS_LITE_EMBED_URL` | No | `http://localhost:11434` | Ollama endpoint |
| `MEMOS_LITE_EMBED_MODEL` | No | `nomic-embed-text` | Embedding model |

### Read from `.env`, not from the client config

The server reads these when building a cube, and they are conventionally kept in
`.env` rather than repeated in every client config. `MOS_CHAT_MODEL` is
**required** — cube registration dies on it first, surfacing as a cube that
"registers" and immediately reports itself unregistered.

| Variable | Description |
|----------|-------------|
| `MOS_CHAT_MODEL` | Chat model for memory extraction. Required |
| `MOS_EMBEDDER_BACKEND` / `_PROVIDER` / `_MODEL` / `_API_BASE` | Embedder wiring |
| `MOS_ENABLE_REORGANIZE` | Background memory reorganization |
| `NEO4J_BACKEND` / `NEO4J_URI` / `NEO4J_DB_NAME` | Graph DB connection for cube construction |
| `NEO4J_AUTO_CREATE` / `NEO4J_USE_MULTI_DB` | Cube creation policy |

> **On locating `.env`**: without `MEMOS_ENV_FILE`, the file is found by guessing
> from position (working directory, two levels above the package, then dotenv's
> upward search). That works from a checkout but **not from a global install or
> `npx`**, where the package sits outside the project and every candidate misses —
> so no variable loads at all. Set `MEMOS_ENV_FILE` (or pass `--memos-env-file`)
> when the client's working directory and the install location are both outside the
> project. A path that does not exist warns on stderr rather than failing silently.
>
> Copy `.env.example` to get started.

> **`MEMOS_ENV_FILE` wins over the client config.** It is loaded with
> `override: true`, so a value in that file beats the same key in the MCP client's
> `env` block. The positional fallbacks are the opposite — they only fill gaps and
> never override the launcher. This is deliberate: an explicitly named env file is
> meant to be authoritative, while a `.env` that merely happens to sit nearby is
> not. The practical consequence is that switches like
> `MEMOS_SHOW_WORKING_MEMORY` cannot be flipped from the client config once
> `.env` sets them — edit the env file instead.

---

## Tools (17)

The package defines 17 tool schemas. `memos_delete` is exposed by `tools/list`
only when `MEMOS_ENABLE_DELETE=true`; the other 16 are available by default.

<!-- mcp-tool-inventory:start -->
| Tool | Description |
|------|-------------|
| `memos_context_resume` | Recover project context after compaction (recent 24h + project state) |
| `memos_search` | Semantic search with keyword reranking. Pass `context` (recent turns) to enable LLM intent analysis and query expansion |
| `memos_save` | Save memories with explicit type (BUGFIX, DECISION, MILESTONE, SYNTHESIS…) |
| `memos_list_v2` | List memories with auto-compaction |
| `memos_get` | Get full memory details by ID |
| `memos_suggest` | Smart search query suggestions + `memory_type` decision tree |
| `memos_think` | Evidence pack for a question: retrieval + contradiction/staleness flags + gap analysis. The caller synthesizes the answer and may persist it as `SYNTHESIS` |
| `memos_graph` | Explainable graph queries plus strict Graphify node-link validation — `mode`: `related` / `path` / `impact` / `schema` / `import` |
| `memos_admin` | Maintenance — `action`: `list_cubes` / `register_cube` / `create_user` / `validate_cubes` / `stats` / `calendar` |
| `memos_export_wiki` | Export a cube as an interlinked markdown wiki (page per memory + index + mermaid graph) |
| `memos_import_wiki` | Import an exported wiki back into a cube; supports dry-run and versioning edited pages, never deletes memories |
| `memos_canvas` | Symbolic task canvas — short-term task state that survives context compaction. `action`: `open` / `update` / `show` / `list` / `delete` (a canvas with unfinished nodes needs `confirm=true`). Nodes carry greppable ids (`000-N1`) and a `ref` anchoring them to evidence: `mem:<memory_id>` / `file:<path>` / `note:<text>` |
| `memos_distill_skill` | Create an inert, reviewable Skill candidate under `<project_path>/skill-candidates`; it never installs the candidate automatically |
| `memos_list_skill_candidates` | List generated Skill candidates without modifying or installing them |
| `memos_review_skill_candidate` | Approve or reject a candidate with reviewer audit metadata; approval does not install |
| `memos_install_skill_candidate` | Install an approved candidate only into `.claude/skills/<slug>/SKILL.md`, without overwrite or script execution |
| `memos_delete` | Delete selected or all memories. Disabled by default and requires explicit user confirmation when enabled |
<!-- mcp-tool-inventory:end -->

### `memos_graph` modes

| Mode | Main input | Result |
|------|------------|--------|
| `related` | `query` | Related memories and edges, with provenance explanations when available |
| `path` | `source_id`, `target_id` | A bounded path between two graph nodes, including relationship evidence |
| `impact` | `memory_id`, optional `max_depth` | Forward blast radius from one memory |
| `schema` | Optional `sample_size` | Graph structure and statistics |
| `import` | `graph_json`, optional `project_key` | Deterministic validation and dry-run plan for Graphify NetworkX node-link JSON |

`import` accepts at most 5 MB of JSON and rejects duplicate node ids, dangling
edges, unsafe source paths, invalid confidence values, and oversized graphs. It
does **not** write Code Graph nodes to Neo4j, Qdrant, or a memory cube.

---

## How .env Loading Works

Priority order for configuration values (highest first):

1. **CLI configuration flags** such as `--memos-url`
2. **Explicit env file** selected by `--memos-env-file` or inherited `MEMOS_ENV_FILE`
3. **Inherited process environment** — this is where MCP client `env` values belong
4. **Auto-discovered `process.cwd()/.env`** — provides only missing defaults
5. **Auto-discovered package-root `.env`** — provides only missing defaults
6. **dotenv upward fallback**, then built-in defaults

The automatic file search never overrides explicit MCP/launcher environment values. Use `MEMOS_ENV_FILE` only when the selected file should deliberately be authoritative; this is also the reliable option for `npx` installs.

---

## Development

```bash
git clone https://github.com/lsg1103275794/oh-memos.git
cd oh-memos/mcp-server-node
npm install
npm run dev    # Run with tsx (no build needed)
npm run build  # Compile to dist/
```

---

## Requirements

- Node.js >= 20.0.0
- oh-memos backend API running (`scripts\local\start.bat`)
