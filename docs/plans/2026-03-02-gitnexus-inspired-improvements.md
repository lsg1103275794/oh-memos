# GitNexus-Inspired Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 借鉴 GitNexus 的三个核心设计，提升 MemOS 的搜索性能、自动上下文注入能力和记忆可追溯性。

**Architecture:**
- Task 1：纯 Node.js hook，拦截 Claude Code 的 Grep/Glob/Read/Edit 工具调用，自动注入相关记忆上下文（零后端改动）。
- Task 2：在 MemOS 的 reranker 层新增 `rrf` backend，本地 Python 计算 Reciprocal Rank Fusion，替代需要外部 HTTP 调用的 BGE Reranker。
- Task 3：新增 `memos_impact` MCP 工具，对给定记忆 ID 做"影响范围"分析，封装现有 `trace_path` + `get_graph`。

**Tech Stack:** Node.js (hooks), Python (reranker), TypeScript types (已有), Neo4j Cypher (已有)

---

## 背景速查

### 文件路径地图

| 层 | 关键文件 |
|---|---|
| Hook 存放 | `project-memory/hooks/node/` |
| Hook 配置模板 | `project-memory/hooks/settings-template.json` |
| Reranker 基类 | `src/memos/reranker/base.py` |
| Reranker 工厂 | `src/memos/reranker/factory.py` |
| Reranker Noop 参考 | `src/memos/reranker/noop.py` |
| 搜索管道 | `src/memos/memories/textual/tree_text_memory/retrieve/recall.py` |
| MCP 工具注册 | `mcp-server/tools_registry.py` |
| MCP Graph Handler | `mcp-server/handlers/graph.py` |
| Dev cube 配置 | `data/memos_cubes/dev_cube/config.json` |

### RRF 公式

```
score(d) = Σ  1 / (k + rank_i(d))
           i
k = 60  (文献标准值，抑制低排名项的极端影响)
```

不需要分数归一化，只需要各路召回的排名顺序。

---

## Task 1: PreToolUse 自动记忆注入 Hook

**目标**：Claude 执行 Grep/Glob/Read/Edit 前，自动查一次相关记忆并注入 `additionalContext`，无需 Claude 主动调用 `memos_search`。

**影响范围**：
- Create: `project-memory/hooks/node/memos_context_inject.js`
- Modify: `project-memory/hooks/settings-template.json`

---

### Step 1-1: 写失败测试（手动验证脚本）

创建 `project-memory/hooks/node/_test_context_inject.js`：

```javascript
#!/usr/bin/env node
// 手动测试：模拟 PreToolUse 输入，验证 hook 输出正确格式
const { execSync } = require('child_process');

const mockInput = JSON.stringify({
  tool_name: 'Grep',
  tool_input: { pattern: 'WebSocket', path: '/mnt/g/Cyber/AudioCraft Studio' },
  cwd: '/mnt/g/Cyber/AudioCraft Studio',
  session_id: 'test-123'
});

// 通过 stdin 传入 mock 数据
const result = execSync(
  'node project-memory/hooks/node/memos_context_inject.js',
  { input: mockInput, cwd: '/mnt/g/test/MemOS', encoding: 'utf8', timeout: 8000 }
);

const parsed = JSON.parse(result);
console.assert(parsed.continue === true, 'Must have continue:true');
console.assert(typeof parsed.suppressOutput === 'boolean', 'Must have suppressOutput');
// 当 API 在线时应该有 additionalContext
if (parsed.additionalContext) {
  console.assert(parsed.additionalContext.includes('Memory'), 'Context should mention Memory');
}
console.log('PASS:', JSON.stringify(parsed).slice(0, 200));
```

运行验证当前失败（hook 文件不存在）：
```bash
cd /mnt/g/test/MemOS
node project-memory/hooks/node/_test_context_inject.js
# Expected: Error: Cannot find module / ENOENT
```

---

### Step 1-2: 实现 hook

创建 `project-memory/hooks/node/memos_context_inject.js`：

```javascript
#!/usr/bin/env node
/**
 * MemOS Hook: PreToolUse - Auto Memory Context Injection
 *
 * Inspired by GitNexus's PreToolUse hook pattern.
 * Intercepts Grep/Glob/Read/Edit tool calls and injects relevant
 * memories as additionalContext — no explicit memos_search needed.
 *
 * Fires on: Grep, Glob, Read, Edit, Write
 * Skips: memory-unrelated tools, empty queries, API offline
 */

'use strict';

const http = require('http');
const { execSync } = require('child_process');

// ── Configuration ─────────────────────────────────────────────────────────
const MEMOS_API = process.env.MEMOS_URL || 'http://localhost:18000';
const MEMOS_USER = process.env.MEMOS_USER || 'dev_user';
const TIMEOUT_MS = 4000;  // Must stay well below hook timeout (5s)
const MAX_CONTEXT_CHARS = 800;  // Keep additionalContext concise

// Tools worth searching for (file ops that benefit from memory context)
const RELEVANT_TOOLS = new Set(['Grep', 'Glob', 'Read', 'Edit', 'Write']);

// ── Input ──────────────────────────────────────────────────────────────────
let input = '';
process.stdin.on('data', chunk => (input += chunk));
process.stdin.on('end', async () => {
  try {
    const data = JSON.parse(input);
    const toolName = data.tool_name || '';
    const toolInput = data.tool_input || {};
    const cwd = data.cwd || process.cwd();

    // Skip irrelevant tools immediately
    if (!RELEVANT_TOOLS.has(toolName)) {
      return pass();
    }

    // Extract search keyword from tool input
    const keyword = extractKeyword(toolName, toolInput);
    if (!keyword || keyword.length < 3) return pass();

    // Derive cube_id from cwd (matches MemOS cube routing logic)
    const cubeId = cwdToCubeId(cwd);

    // Search memories
    const memories = await searchMemories(keyword, cubeId);
    if (!memories.length) return pass();

    // Format concise context
    const context = formatContext(memories, keyword);

    output({
      continue: true,
      suppressOutput: false,
      additionalContext: context
    });
  } catch (_) {
    pass();
  }
});

// ── Helpers ────────────────────────────────────────────────────────────────

function pass() {
  output({ continue: true, suppressOutput: true });
}

function output(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function extractKeyword(toolName, toolInput) {
  switch (toolName) {
    case 'Grep':    return toolInput.pattern || toolInput.query || '';
    case 'Glob':    return toolInput.pattern || '';
    case 'Read':    return pathToKeyword(toolInput.file_path || '');
    case 'Edit':
    case 'Write':   return pathToKeyword(toolInput.file_path || '');
    default:        return '';
  }
}

function pathToKeyword(filePath) {
  // Extract meaningful filename part: /a/b/UserService.ts → UserService
  const base = filePath.split(/[/\\]/).pop() || '';
  return base.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ');
}

/**
 * Derive MemOS cube_id from cwd.
 * Rule: basename → lowercase → replace -/./space with _ → append _cube
 * Example: /mnt/g/Cyber/AudioCraft Studio → audiocraft_studio_cube
 */
function cwdToCubeId(cwd) {
  const parts = cwd.replace(/\\/g, '/').split('/').filter(Boolean);
  const name = parts[parts.length - 1] || 'dev';
  return name.toLowerCase().replace(/[-.\s]+/g, '_') + '_cube';
}

function searchMemories(query, cubeId) {
  return new Promise((resolve) => {
    const body = JSON.stringify({
      user_id: MEMOS_USER,
      query,
      install_cube_ids: [cubeId],
      top_k: 3
    });

    const url = new URL('/product/search', MEMOS_API);
    const req = http.request(
      { hostname: url.hostname, port: url.port || 80, path: url.pathname,
        method: 'POST', headers: { 'Content-Type': 'application/json',
                                    'Content-Length': Buffer.byteLength(body) },
        timeout: TIMEOUT_MS },
      (res) => {
        let raw = '';
        res.on('data', c => (raw += c));
        res.on('end', () => {
          try {
            const d = JSON.parse(raw);
            const nodes = d?.data?.text_mem?.[0]?.memories?.nodes || [];
            resolve(nodes.slice(0, 3));
          } catch { resolve([]); }
        });
      }
    );
    req.on('error', () => resolve([]));
    req.on('timeout', () => { req.destroy(); resolve([]); });
    req.write(body);
    req.end();
  });
}

function formatContext(memories, keyword) {
  const lines = [`📌 Related memories for "${keyword}":`];
  let total = lines[0].length;

  for (const mem of memories) {
    const text = (mem.memory || '').replace(/\s+/g, ' ').trim();
    const key  = mem.key || mem.metadata?.key || '';
    const line = key ? `• [${key}] ${text.slice(0, 120)}` : `• ${text.slice(0, 140)}`;
    if (total + line.length > MAX_CONTEXT_CHARS) break;
    lines.push(line);
    total += line.length;
  }

  return lines.join('\n');
}
```

---

### Step 1-3: 运行测试验证通过

```bash
cd /mnt/g/test/MemOS
# 先确保 MemOS API 在线
curl -s http://localhost:18000/health | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])"

# 运行测试
node project-memory/hooks/node/_test_context_inject.js
# Expected: PASS: {"continue":true,"suppressOutput":false,"additionalContext":"📌 Related..."}
# 或 API 离线时: PASS: {"continue":true,"suppressOutput":true}
```

---

### Step 1-4: 更新 settings-template.json

在 `project-memory/hooks/settings-template.json` 的 `PreToolUse` 数组中添加：

```json
{
  "matcher": "Grep|Glob|Read|Edit|Write",
  "hooks": [
    {
      "type": "command",
      "command": "node <MEMOS_PATH>/project-memory/hooks/node/memos_context_inject.js",
      "timeout": 5
    }
  ]
}
```

完整 PreToolUse 节后应有三个 matcher：
1. `Edit|Write` → `memos_block_sensitive.js`
2. `Bash` + mkdir → `memos_block_mkdir_memory.js`
3. `Grep|Glob|Read|Edit|Write` → `memos_context_inject.js` （新增）

---

### Step 1-5: Commit

```bash
cd /mnt/g/test/MemOS
git add project-memory/hooks/node/memos_context_inject.js project-memory/hooks/settings-template.json
git commit -m "feat: add PreToolUse hook for automatic memory context injection

Inspired by GitNexus's PreToolUse hook pattern. Intercepts Grep/Glob/
Read/Edit/Write tool calls, searches MemOS for related memories, and
injects them as additionalContext — zero explicit memos_search needed."
```

---

## Task 2: RRF 本地 Reranker（替代 HTTP BGE）

**目标**：新增 `rrf` reranker backend，基于 Reciprocal Rank Fusion 在本地计算排名，消除对 SiliconFlow HTTP Reranker 的依赖，搜索延迟减少约 200-400ms。

**影响范围**：
- Create: `src/memos/reranker/rrf.py`
- Modify: `src/memos/reranker/factory.py`（注册新 backend）
- Modify: `data/memos_cubes/dev_cube/config.json`（切换默认）

---

### Step 2-1: 写失败测试

创建 `src/memos/reranker/test_rrf.py`（临时测试文件，之后可移到 tests/）：

```python
"""Quick sanity test for RRFReranker."""
import sys
sys.path.insert(0, 'src')

from memos.reranker.rrf import RRFReranker
from memos.memories.textual.item import TextualMemoryItem, TextualMemoryMetadata

def make_item(text: str) -> TextualMemoryItem:
    return TextualMemoryItem(
        memory=text,
        metadata=TextualMemoryMetadata(user_id="test")
    )

def test_rrf_preserves_top_k():
    rrf = RRFReranker(k=60)
    items = [make_item(f"memory {i}") for i in range(10)]
    results = rrf.rerank("query", items, top_k=3)
    assert len(results) == 3, f"Expected 3, got {len(results)}"
    print("PASS: top_k=3 returns 3 items")

def test_rrf_scores_descending():
    rrf = RRFReranker(k=60)
    items = [make_item(f"memory {i}") for i in range(5)]
    results = rrf.rerank("query", items, top_k=5)
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True), "Scores must be descending"
    print("PASS: scores are descending")

def test_rrf_score_formula():
    """First item (rank=1) should have score 1/(60+1) = 0.01639..."""
    rrf = RRFReranker(k=60)
    items = [make_item("only item")]
    results = rrf.rerank("q", items, top_k=1)
    expected = 1.0 / (60 + 1)
    assert abs(results[0][1] - expected) < 1e-6, f"Score mismatch: {results[0][1]} != {expected}"
    print(f"PASS: RRF score formula correct ({results[0][1]:.6f})")

if __name__ == "__main__":
    test_rrf_preserves_top_k()
    test_rrf_scores_descending()
    test_rrf_score_formula()
    print("All tests passed!")
```

运行验证失败：
```bash
cd /mnt/g/test/MemOS
.venv/Scripts/python.exe src/memos/reranker/test_rrf.py
# Expected: ModuleNotFoundError: No module named 'memos.reranker.rrf'
```

---

### Step 2-2: 实现 RRFReranker

创建 `src/memos/reranker/rrf.py`：

```python
# memos/reranker/rrf.py
"""
Reciprocal Rank Fusion (RRF) Reranker

Local, zero-HTTP alternative to cross-encoder rerankers.
Uses the standard RRF formula:  score(d) = Σ 1/(k + rank_i(d))

Background:
- Same approach as Elasticsearch, Pinecone, GitNexus hybrid search
- k=60 is the standard value from the original RRF paper (Cormack 2009)
- Higher k gives more weight to lower-ranked results (less top-heavy)
- No score normalization needed — rank positions are the only input

Usage in cube config.json:
  "reranker": {
    "backend": "rrf",
    "config": { "k": 60 }
  }
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from memos.utils import timed
from .base import BaseReranker

if TYPE_CHECKING:
    from memos.memories.textual.item import TextualMemoryItem


class RRFReranker(BaseReranker):
    """
    Reciprocal Rank Fusion reranker.

    Treats the *position* of each item in the merged recall list as its
    rank. Since recall.py already merges BM25 + vector + graph results
    (each group internally ordered by score), position in the merged list
    is a reasonable proxy for per-source rank.

    Formula:  rrf_score(item at rank r) = 1 / (k + r)
    where r is 1-based position in the input list.
    """

    def __init__(self, k: int = 60):
        """
        Args:
            k: RRF constant (default 60, from Cormack et al. 2009).
               Higher k → less aggressive top-ranking bias.
        """
        self.k = k

    @timed
    def rerank(
        self,
        query: str,
        graph_results: list[TextualMemoryItem],
        top_k: int,
        search_filter: dict | None = None,
        **kwargs,
    ) -> list[tuple[TextualMemoryItem, float]]:
        """
        Apply RRF scoring and return top_k (item, score) pairs sorted descending.

        Args:
            query: Not used directly (RRF is rank-based, not query-dependent).
            graph_results: Merged recall results in their natural order.
            top_k: Maximum number of results to return.
            search_filter: Ignored (filtering is upstream responsibility).

        Returns:
            List of (TextualMemoryItem, rrf_score) sorted by score descending.
        """
        k = self.k
        scored = [
            (item, 1.0 / (k + rank))
            for rank, item in enumerate(graph_results, start=1)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
```

---

### Step 2-3: 运行测试验证通过

```bash
cd /mnt/g/test/MemOS
.venv/Scripts/python.exe src/memos/reranker/test_rrf.py
# Expected:
# PASS: top_k=3 returns 3 items
# PASS: scores are descending
# PASS: RRF score formula correct (0.016393)
# All tests passed!
```

---

### Step 2-4: 注册到 factory

修改 `src/memos/reranker/factory.py`，在现有 backend 判断链中加入 `rrf`：

```python
# 在 factory.py 的 build_reranker 函数中，找到现有的 if/elif 链，添加：
elif cfg.backend == "rrf":
    from memos.reranker.rrf import RRFReranker
    k = c.get("k", 60)
    return RRFReranker(k=k)
```

找到精确插入位置（在 `noop` 判断之前或之后）：
```bash
grep -n "noop\|NoopReranker\|backend ==" /mnt/g/test/MemOS/src/memos/reranker/factory.py
```

---

### Step 2-5: 更新 dev_cube 配置

修改 `data/memos_cubes/dev_cube/config.json`，将 reranker 改为 rrf：

```json
"reranker": {
  "backend": "rrf",
  "config": {
    "k": 60
  }
}
```

> ⚠️ 注意：`audiocraft_studio_cube/config.json` 也有 `http_bge`，可选择同步修改。
> 修改后需重启 MemOS API（`start.bat`）才生效。

验证 API 重启后搜索正常：
```bash
curl -s -X POST http://localhost:18000/product/search \
  -H "Content-Type: application/json" \
  -d '{"user_id":"dev_user","query":"WebSocket","install_cube_ids":["dev_cube"],"top_k":3}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['message'], len(d.get('data',{}).get('text_mem',[])))"
# Expected: ok 1
```

---

### Step 2-6: Commit

```bash
cd /mnt/g/test/MemOS
git add src/memos/reranker/rrf.py src/memos/reranker/factory.py data/memos_cubes/dev_cube/config.json
git commit -m "feat: add RRF local reranker to eliminate HTTP reranker dependency

Implements Reciprocal Rank Fusion (Cormack 2009) as a zero-HTTP
reranker backend. Replaces SiliconFlow API call with local Python math,
reducing search latency by ~200-400ms. Register with backend='rrf'."
```

---

## Task 3: `memos_impact` MCP 工具

**目标**：新增 `memos_impact` 工具，输入记忆 ID，输出"这条记忆触发了哪些后续事件/决策"（CAUSE+FOLLOWS 前向追踪），展示影响范围（blast radius）。

**影响范围**：
- Modify: `mcp-server/tools_registry.py`（注册工具）
- Modify: `mcp-server/handlers/graph.py`（实现 handler）
- Modify: `mcp-server/memos_mcp_server.py`（路由到 handler）

---

### Step 3-1: 写失败测试

```bash
# 验证工具当前不存在
cd /mnt/g/test/MemOS
.venv/Scripts/python.exe - << 'EOF'
import sys
sys.path.insert(0, 'mcp-server')
from tools_registry import get_tool_definitions
tools = [t['name'] for t in get_tool_definitions()]
assert 'memos_impact' not in tools, f"Tool already exists: {tools}"
print("PASS: memos_impact not yet registered (expected)")
EOF
```

---

### Step 3-2: 注册工具定义

在 `mcp-server/tools_registry.py` 末尾（或在 `memos_trace_path` 定义之后）添加：

```python
{
    "name": "memos_impact",
    "description": (
        "Analyze the forward impact of a memory — what events, decisions, "
        "or milestones were caused or followed by this memory. "
        "Returns a grouped 'blast radius' view (direct → indirect hops). "
        "Use after memos_search or memos_get_graph to get a memory_id."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "memory_id": {
                "type": "string",
                "description": "ID of the source memory to analyze impact from"
            },
            "cube_id": {
                "type": "string",
                "description": "Memory cube ID (auto-derived from project_path if omitted)"
            },
            "project_path": {
                "type": "string",
                "description": "Project root path — auto-derives cube_id"
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum hops to trace forward (default: 3, max: 6)",
                "default": 3
            }
        },
        "required": ["memory_id"]
    }
},
```

---

### Step 3-3: 实现 handler

在 `mcp-server/handlers/graph.py` 末尾添加 `handle_memos_impact` 函数：

```python
async def handle_memos_impact(
    client: httpx.AsyncClient,
    arguments: dict[str, Any]
) -> list[TextContent]:
    """Analyze forward impact (blast radius) of a memory node."""
    cube_id = get_cube_id_from_args(arguments)
    memory_id = arguments.get("memory_id", "")
    max_depth = min(int(arguments.get("max_depth", 3)), 6)

    if not memory_id:
        return error_response(
            "memory_id is required",
            error_code=ERR_PARAM_MISSING,
            suggestions=["Get memory_id from memos_search or memos_get_graph results"]
        )

    if not NEO4J_HTTP_URL or not NEO4J_USER or not NEO4J_PASSWORD:
        return error_response("Neo4j configuration missing", error_code=ERR_NEO4J_CONFIG)

    neo4j_auth = (NEO4J_USER, NEO4J_PASSWORD)

    # Forward traversal: follow CAUSE and FOLLOWS edges outward
    cypher = f"""
    MATCH (source:Memory {{id: $source_id}})
    CALL apoc.path.subgraphNodes(source, {{
        relationshipFilter: 'CAUSE>|FOLLOWS>',
        maxLevel: {max_depth}
    }}) YIELD node
    WHERE node.id <> $source_id
    MATCH p = shortestPath((source)-[:CAUSE|FOLLOWS*1..{max_depth}]->(node))
    RETURN node.id AS id, node.key AS key, node.memory AS memory,
           length(p) AS depth
    ORDER BY depth ASC
    LIMIT 30
    """

    # Fallback if APOC not available: use variable-length path
    cypher_simple = f"""
    MATCH (source:Memory {{id: $source_id}})-[:CAUSE|FOLLOWS*1..{max_depth}]->(node:Memory)
    WITH node, min(length(shortestPath(
        (source)-[:CAUSE|FOLLOWS*1..{max_depth}]->(node)
    ))) AS depth
    RETURN node.id AS id, node.key AS key, node.memory AS memory, depth
    ORDER BY depth ASC
    LIMIT 30
    """

    # Try simple query first (no APOC dependency)
    neo4j_resp = await client.post(
        NEO4J_HTTP_URL,
        json={"statements": [{"statement": cypher_simple,
                               "parameters": {"source_id": memory_id}}]},
        auth=neo4j_auth
    )

    results = ["## 💥 Memory Impact Analysis"]
    results.append("")

    if neo4j_resp.status_code != 200:
        return api_error_response("Impact analysis", f"Neo4j HTTP {neo4j_resp.status_code}")

    neo4j_data = neo4j_resp.json()
    errors = neo4j_data.get("errors", [])
    rows = neo4j_data.get("results", [{}])[0].get("data", [])

    if errors:
        results.append(f"*Neo4j query error: {errors[0].get('message', 'unknown')}*")
        return [TextContent(type="text", text="\n".join(results))]

    if not rows:
        results.append("*No forward impact found — this memory has no CAUSE or FOLLOWS successors.*")
        results.append("")
        results.append("Suggestions:")
        results.append("- Verify the memory_id is correct")
        results.append("- The memory may be a leaf node with no downstream dependencies")
        return [TextContent(type="text", text="\n".join(results))]

    # Group by depth
    by_depth: dict[int, list[dict]] = {}
    for row in rows:
        r = row.get("row", [])
        if len(r) >= 4:
            depth = int(r[3])
            by_depth.setdefault(depth, []).append({
                "id": r[0], "key": r[1] or "", "memory": r[2] or ""
            })

    total = sum(len(v) for v in by_depth.values())
    results.append(f"**Blast Radius**: {total} downstream {'memory' if total == 1 else 'memories'} across {len(by_depth)} hop(s)")
    results.append("")

    depth_labels = {1: "Direct Impact (1 hop)", 2: "Indirect (2 hops)", 3: "Downstream (3+ hops)"}
    for depth in sorted(by_depth.keys()):
        label = depth_labels.get(depth, f"{depth} hops")
        nodes = by_depth[depth]
        results.append(f"### {label} — {len(nodes)} nodes")
        results.append("")
        for node in nodes[:8]:  # cap per depth
            key = node["key"]
            mem_preview = node["memory"][:80].replace("\n", " ")
            if key:
                results.append(f"- **{key}**  `{node['id'][:8]}`")
                results.append(f"  {mem_preview}...")
            else:
                results.append(f"- `{node['id'][:8]}` {mem_preview}...")
        if len(nodes) > 8:
            results.append(f"  *...and {len(nodes) - 8} more*")
        results.append("")

    return [TextContent(type="text", text="\n".join(results))]
```

---

### Step 3-4: 路由到 handler

在 `mcp-server/memos_mcp_server.py` 中找到工具路由的 if/elif 链（处理 `memos_get_graph`、`memos_trace_path` 的地方），添加：

```python
elif tool_name == "memos_impact":
    return await handle_memos_impact(client, arguments)
```

同时在文件顶部的 import 中添加 `handle_memos_impact`：
```python
from handlers.graph import (
    handle_memos_export_schema,
    handle_memos_get_graph,
    handle_memos_impact,     # ← 新增
    handle_memos_trace_path,
)
```

---

### Step 3-5: 验证工具注册

```bash
cd /mnt/g/test/MemOS
.venv/Scripts/python.exe - << 'EOF'
import sys
sys.path.insert(0, 'mcp-server')
from tools_registry import get_tool_definitions
tools = [t['name'] for t in get_tool_definitions()]
assert 'memos_impact' in tools, f"memos_impact not found in: {tools}"
print("PASS: memos_impact registered")

# 验证 handler 可导入
from handlers.graph import handle_memos_impact
print("PASS: handle_memos_impact importable")
EOF
```

---

### Step 3-6: 功能验证（用真实数据）

```bash
# 用之前找到的 AudioCraft Studio 中已知有 CAUSE 关系的节点
# source: d9247683 (AudioCraft Studio 技术架构设计)
# 需要完整 UUID，通过 Neo4j 查一下
curl -s -u neo4j:12345678 \
  -X POST http://localhost:7474/db/neo4j/tx/commit \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"MATCH (n:Memory {user_name:\"audiocraft_studio_cube\"}) WHERE n.key=\"AudioCraft Studio 技术架构设计\" RETURN n.id LIMIT 1"}]}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['results'][0]['data'][0]['row'][0])"
# 得到完整 UUID 后在 Claude Code 中调用 memos_impact 验证
```

---

### Step 3-7: Commit

```bash
cd /mnt/g/test/MemOS
git add mcp-server/tools_registry.py mcp-server/handlers/graph.py mcp-server/memos_mcp_server.py
git commit -m "feat: add memos_impact tool for forward blast radius analysis

Inspired by GitNexus's 'impact' tool concept. Traverses CAUSE and
FOLLOWS edges forward from a source memory node, groups results by
hop depth, and returns a blast-radius summary of downstream memories."
```

---

## 执行顺序总结

```
Task 1 (Hook)      ← 最快，30min，零风险，立刻有感知收益
   ↓
Task 2 (RRF)       ← 中等，1h，降低外部依赖
   ↓
Task 3 (Impact)    ← 中等，1h，提升图谱查询体验
```

每个 Task 独立可交付，可按顺序单独执行，失败不影响其他 Task。

---

## 测试命令速查

```bash
# Task 1: hook 单元测试
node project-memory/hooks/node/_test_context_inject.js

# Task 2: RRF reranker 单元测试
.venv/Scripts/python.exe src/memos/reranker/test_rrf.py

# Task 2: 搜索端到端验证（重启 API 后）
curl -s -X POST http://localhost:18000/product/search \
  -H "Content-Type: application/json" \
  -d '{"user_id":"dev_user","query":"test","install_cube_ids":["dev_cube"],"top_k":3}'

# Task 3: 工具注册验证
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'mcp-server'); from tools_registry import get_tool_definitions; print([t['name'] for t in get_tool_definitions()])"
```
