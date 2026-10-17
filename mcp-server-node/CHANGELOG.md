# Changelog

All notable changes to `oh-memos-mcp` are documented here.

This project follows [Semantic Versioning](https://semver.org/).

---

## [3.1.10] - 2026-10-18

配套 API / Docker 镜像版本为 3.1.10。MCP server 代码无改动。

- 仓库迁回 `lsg1103275794/oh-memos`：`package.json` 的 repository / bugs / homepage 与 README 链接同步更新。
- 配套 API 导入时不再加载 torch / transformers / sklearn，内存降低约 2/3；Docker 镜像不再安装 torch。MCP 调用方式不变。

## [3.1.9] - 2026-09-16

配套 API / Docker 镜像版本为 3.1.9。保存先确认原文与向量已持久化，再返回记忆 ID；
LLM 解析由 API 在后台自动完成，即使模型调用耗时数分钟，也不阻塞 MCP 保存回执。

- 识别 `vector_saved` 与 `enrichment_status`，明确显示向量已保存和后台解析状态，兼容旧 API。
- 未确认向量保存或缺少实际 ID 时返回 MCP `isError: true`，且不写入去重缓存。
- 请求和响应正文超时归类为 `API_TIMEOUT`，不再误报 API 离线；结果未知的 POST 不自动重放。
- 显式传递 `memory_type`；Wiki 导入同样拒绝未确认的向量写入。
- 完整详情使用原始创建时间，避免将后台解析的更新时间误标为创建时间。

验证：582 项 Node 测试、旧版及 v2 MCP 协议检查通过。配套 API 的 118 项 Python 回归通过。
真实 MCP 首次保存 596ms 返回，LLM 约 225 秒后补齐同一 ID 的元数据；重复保存 362ms，
原文、ID 和已有解析结果均保留。

## [3.1.8] - 2026-08-27

仅 MCP server（npm `oh-memos-mcp`）。Python 包与容器镜像无改动，仍为 3.1.5。

### 🏷️ `memos_get` 报 root 无权限，而 root 从未被传入

`memos_get` 打自己项目的 cube 时回：

```
❌ [API_ERROR] Get failed: User 'root' does not have access to cube
   'jincaizhaopin_cube'. Please register the cube first or request access.
```

但 `MEMOS_USER=dev_user`，root 不在任何调用参数里。

root 来自后端的默认回退：`start_api.py` 的 `get_memory(mem_cube_id, memory_id,
user_id=None)` 把 `user_id` 声明为可选，缺失时 `core.py` 的 `get()` 回退到
`self.user_id`（MOS 实例自己的用户，即 root）。而 `ensureCubeRegistered` 注册的是
`MEMOS_USER`，于是 root 对该 cube 无授权，`_validate_cube_access` 抛 ValueError，
被 ValueError handler 映射成 400。

**`handleMemosGet` 是唯一漏传 `user_id` 的调用点** —— save / list / search /
stats / calendar / siblings 全都传了，admin 的 delete 路径也拼了查询串。

`apiCallWithRetry` 的 400 分支救不回来：它把 400 当「cube 未加载」，重注册后重试
—— 但重注册仍按 `MEMOS_USER` 注册，重试请求仍然不带 `user_id`，第二次照样落到 root。

实测对照（同一个不存在的 id，`jincaizhaopin_cube`）：

```
不带 user_id        -> User 'root' does not have access to cube 'jincaizhaopin_cube'
带 user_id=dev_user -> Memory with ID ... not found        ← 正常语义
```

为什么以前没人踩到：cube 的**归属**决定是否触发。root 名下的 cube（`dev_cube`、
`claude_cube`、`memos_cube` 等）不受影响；只有 owner 是 `MEMOS_USER` 的项目 cube
才会报错 —— 也就是每一个用 `project_path` 自动派生出来的 cube。

同源缺陷也修了 `wiki-import.ts` 的 `getStoredMemory`。那里更隐蔽：该消息既不含
`not found` 也不是 404，会被当成真实故障，把整页 import 判成失败而不是「记忆不存在」。

`apiErrorResponse` 另加了对 `does not have access` 的识别。该消息同时含 `user` 和
cube 字样，却不匹配任何既有分支，此前只能给通用的「查 health / 看日志」。新提示先
指向 `user_id`，因为最常见的成因是调用方漏传它，而不是用户或 cube 不存在。

回归测试 `get-user-id-param.test.ts` 的 fetch stub **按 `user_id` 是否存在分流**
应答，复刻上面的实测对照。无条件回 not-found 的 stub 守不住这个缺陷 —— 变异验证
（把 params 改回 `{}`）时三条断言必须全红，写测试时实际拿它验过。

## [3.1.7] - 2026-08-27

仅 MCP server（npm `oh-memos-mcp`）。Python 包与容器镜像无改动，仍为 3.1.5。

### 🏷️ `open` 报出的画布名，`list` 找不到

goal 足够长时，`actionOpen` 报出的名字比磁盘上真实存在的多一个字符：

```
open  reports: 000-verify-3-1-6-canvas-delete-and-ref-escaping-over-live-mcp  (61)
list  shows  : 000-verify-3-1-6-canvas-delete-and-ref-escaping-over-live-mc   (60)
on disk      : ...-live-mc.mmd
```

`actionOpen` 先 `slugify(goal)` 拿到最多 `SLUG_MAX`（60）字符，再拼 `${prefix}-`，
总长可达 64。`saveCanvas` → `canvasPath` 在落盘路上又 slugify 一次，砍回 60。
**前缀那 4 个字符的预算从来没被算进去。**

`canvasPath` 里那处「slug 与原名不同就拒绝」的检查本该拦住它，但它只在名字
「像路径」（含 `/`、`\` 或 `..`）时抛错 —— 截断不像路径，于是静默放过。

影响是**报错的句柄，不是损坏的数据**：前缀仍让每个画布互不相同，
两个前 60 字符相同的长 goal 得到 `000-`/`001-` 两个独立文件，各自节点都在；
`update`/`delete` 传 `open` 报的长名字也照样能用，因为 `canvasPath` 的截断是幂等的。
坏的只有一件事：调用方拿到的名字，`list` 永远不会显示，磁盘上也不存在。

修法是把名字组装收进 `canvas-format.ts` 的新函数 `canvasName(prefix, goal)` ——
让它紧挨着自己必须遵守的那个上限，而不是让 handler 去做预算算术：

```ts
export function canvasName(prefix: string, goal: string): string {
  const head = `${prefix}-`;
  const slug = slugify(goal, SLUG_MAX - head.length);
  return slug ? `${head}${slug}` : `${head}task`;
}
```

`slugify` 因此多一个可选的 `maxLength`，**向内钳制到 `SLUG_MAX`** ——
调用方能收紧上限，不能放宽它，否则「每个画布文件名都装得进 `SLUG_MAX`」
这个不变量就成了各调用点的自选项。截断后仍走一次尾部连字符清理，
所以 `000-abc-.mmd` 这种名字不会出现。

### 🧪 测试

canvas-format 单测 41 → 50，canvas e2e 34 → 40 项。

核心断言是**不动点**而不是长度：`slugify(canvasName(p, g)) === canvasName(p, g)`，
跨 3 个前缀 × 6 种 goal（超长、纯 CJK、尾部连字符诱饵、前 60 字符相同的两个变体）。
长度只是症状 —— `canvasPath` 会再 slugify 一次，任何不是不动点的名字都是
「告诉了调用方、但文件系统从没见过」的名字。

e2e 补的 5 项跨 open/list/show/delete 与磁盘：`open` 报的名字必须等于
`list` 显示的名字、等于磁盘上存在的文件。反向验证还原实现后 3 项变红
（长度 64、磁盘上无此名、`list` 显示另一个名字）。

另两项（`reported name still routes to its canvas` / `... to delete`）
在修复前后都通过 —— `canvasPath` 截断幂等使然。**保留但改名如实**：
它们守的是「如果有人改用『让 `canvasPath` 对有损名字抛错』来修这个缺陷，
这条回归会被抓到」，不是这次的不变量。

门禁：vitest 520 passed、tsc、canvas e2e 40 项、pack 契约 104 文件、
schema budget +0.8%、semantic 快照 17 工具、protocol legacy + v2、
lite smoke、host-env smoke、spread smoke。

---

## [3.1.6] - 2026-08-26

仅 MCP server（npm `oh-memos-mcp`）。Python 包与容器镜像无改动，仍为 3.1.5。

### 🔤 `memos_canvas` 的 ref 里，引号读不回来

`ref` 走 JSON 转义而非标签转义，因为 Windows 路径的反斜杠必须逐字返回，
否则锚点失效。但 `renderRef` 在 `JSON.stringify` 之后又替换了一次裸引号：

```js
JSON.stringify(ref).slice(1, -1).replace(/"/g, "\\u0022")   // 旧
```

`JSON.stringify` 已经把 `"` 写成 `\"`。那个 `replace` 只匹配裸引号，
**JSON 留下的反斜杠还在前面**，于是落盘成 `\\u0022`；`parseRef` 走 `JSON.parse`，
`\\` 解成一个字面反斜杠，取回 `"` 而不是 `"`。少匹配了一个反斜杠。

现在匹配 `\"` 整体：`.replace(/\\"/g, "\\u0022")`。引号仍须离开标签 ——
`"` 会提前终止它所在的 Mermaid `["..."]` —— 但这次是**替换**已转义的序列，
不是在它上面再叠一层。

反斜杠一侧一直是对的：`\\` 就是 JSON 在磁盘上的正确表示，`parseRef` 会解回单反斜杠。
只有引号这一条路径坏了。

### 🗑️ `memos_canvas` 新增 `delete` 动作

此前只有 open/update/show/list，清理必须手动删 `.mmd`。而画布的定位是**短期**状态，
注定会产生废弃文件 —— 加之全局规则禁止手工改动记忆文件，等于没有合法的清理路径。

`action="delete"` 在有未完成节点（doing/todo/blocked）时**拒绝**并给出逃生口，
全 done 或空画布直接删：

```
❌ Canvas '000-x' still has 1 unfinished node (0 doing · 0 todo · 1 blocked)
   Review it first: memos_canvas(action="show", name="000-x")
   Delete anyway:   memos_canvas(action="delete", name="000-x", confirm=true)
```

**没有套用 `MEMOS_ENABLE_DELETE`**。那道门是保护长期记忆的：走 API、有 embedding 成本、
且 Lite 模式下整个禁用。画布是本地文件、不走 API，而 Lite 模式下它恰恰是少数可用功能之一 ——
套上那道门等于在最需要清理的模式里砍掉清理能力。`confirm` 这种「拒绝并给出下一步」
与 `MAX_NODES`、非法 status 是同一个既有模式。

删除是硬删，不做回收站：画布存在的意义就是任务收尾后被丢弃，
回收站只会攒下它本该清掉的文件。`deleteCanvas` 复用 `canvasPath`，遍历防护自动继承。

### 🔢 前缀水位线：`delete` 破坏了「前缀永不复用」

加上 delete 之后有两个 e2e 断言失败。**不是断言写错** —— `nextPrefix` 用现存文件算
`max+1`，在只增不减的世界里「前缀永不复用」自动成立，delete 打破了这个不变量：
删掉最高前缀的画布后，那个前缀会被重新发放。

后果正是 `nextPrefix` 自己注释里警告过的：前缀嵌在它铸出的每个节点 id 里，
commit message 或记忆正文引用的 `001-N3` 会变得指向两个不同画布的节点。

修法是 `{cube}/canvas/.prefix-hwm` 水位线文件，`saveCanvas` 与 `deleteCanvas` 都抬升它，
只增不减。delete 侧必须抬升：文件是该前缀唯一的记录，删掉后若水位线仍低于它，
就会被重新发放。旧 cube 没有这个文件时（`readPrefixHwm` 返回 -1），
从现存文件恢复下限，所以升级不会因为水位线缺失而复用前缀。

水位线损坏或不可读时退回扫描文件，与 `parseCanvas` 一致 ——
画布是恢复态，读取时机正是刚丢失上下文的那一刻，抛异常是最坏的选择。

### 🧪 测试

canvas 单测 41 → 45（format）、28 → 44（store），canvas e2e 18 → 34 项。
两个修复都做了反向验证，还原实现后对应用例确实变红：转义 3 项、水位线 1 项（含 delete 侧那次抬升）。

e2e 补了「旧 cube（无水位线）删除后不复用前缀」这条真实升级路径 ——
它跨 store 与 handler，单测碰不到。

顺带改掉一个自己写坏的用例：名字叫 "does not free the prefix it used"，
断言却在验证前缀被释放了。名字与断言矛盾的测试比没有测试更坏。

`memos_canvas` 的 schema 改了（action enum 加 `delete`，新增 `confirm`），
两处冻结的哈希同步重算：`schema-semantic-baseline.json` 与
`protocol-contract.test.ts` 的 `EXPECTED_SCHEMA_HASHES`。

门禁：vitest 511 passed、tsc、canvas e2e 34 项、pack 契约 104 文件、
schema budget +0.8%（限 5%）、semantic 快照 17 工具、protocol v2、lite smoke。

---

## [3.1.5] - 2026-08-26

3.1.1～3.1.4 都是「仅 MCP server」的版本，Python 包与容器镜像停在 3.1.0。
**3.1.5 两侧同时有改动**，三个版本串（npm 包、`pyproject.toml`、`src/oh_memos/__init__.py`）
因此重新对齐到 3.1.5。Python/容器侧的内容见仓库根的 `docs/CHANGELOG.md`。

### 🧾 `memos_get` 的 not-found 文案指向真正的成因

旧文案让用户「核对 id 是否正确（从 `memos_search` 结果复制）」，但实测中最常见的成因恰恰是
**从搜索结果复制来的 id 过一会儿就失效**：`POST /search` 返回的是 `WorkingMemory` 层的副本 id，
该层按 `user_name` 只保留 20 条（后端 `manager.py` 的 `memory_size["WorkingMemory"]`），
每次检索都重写并淘汰最旧的。实测 `oh_memos_cube` 的那 20 条只覆盖 22 分钟。

因此新文案把 `memos_list_v2` 指出来是有实质区别的：它返回 `LongTermMemory` 的 id，
那一层不淘汰（实测同一批 id 隔天仍可取回）。措辞上不把淘汰断言成事实 ——
Lite 模式（本地 JSONL）没有 `WorkingMemory` 层，那里的 not-found 就是单纯的 id 不存在。

`notFoundText` 同时改为导出，便于测试直接断言文案而不经由 handler。

### 🌐 API 客户端保留 400 响应体

`apiCallWithRetry` 此前把非 2xx 一律丢弃响应体，于是后端在 400 里给出的
校验错误说明拿不到，工具层只能报一个无信息的失败。现在 400 单独放行并解析 JSON，
后端的错误描述可以原样呈现给调用方。

### 🔒 分层过滤的强制机制

同一个缺陷已复发 7 次：新增一条检索路径，忘了把 `WorkingMemory` 短期副本滤掉，
于是把一个几分钟后就失效的 id 交给了 agent。每次都靠 review 抓到，这次改成结构性拦截。

**为什么普通单测拦不住**：实测把所有层级过滤切断后，319 项 vitest 依然全绿。
单测问的是"过滤函数算得对不对"，而缺陷形态是"过滤函数没被调用" —— 两个问题不同。

新增 `src/memory-tier-boundary.ts`（清单）与同名 `.test.ts`（守卫，18 项）。
清单把 `handlers/index.ts` 的 28 条分派路由逐条分类并附实测证据，守卫扫描源码与分派表做双向比对。
四条 fail-closed 棘轮，均以变异测试验证过确实会红：

- 分派表新增路由却没在清单里分类 → 失败；清单有而分派表已无（陈旧条目）→ 也失败
- 静默新增已知缺口 → 失败（`KNOWN_GAPS` 为冻结集合，计数上限硬编码）
- 修好缺口却忘了从 `KNOWN_GAPS` 移除 → 失败，否则集合会膨胀成一张无人清理的豁免名单
- `CYPHER_PROJECTION_BASELINE` 按严格相等断言，修好了不调基线同样失败 —— 棘轮只能往紧的方向走

**覆盖了第二种复发形态**：过滤接上了，但构造 metadata 时漏掉 `memory_type`，
判定函数恒读到 `undefined` 并判为可见。`search.ts` 曾因此让四个调用点的过滤同时空转，
而没有任何测试失败。守卫现在会检查投影记忆的 Cypher `RETURN` 是否带出该字段。

**已记录但尚未修的缺口**（`memos_think`、`memos_graph` 的三条路由）：
`think.ts` 上朴素过滤会把语义召回从 15 条砍到 5 条，正确解法是按 `metadata.key`
换成持久层孪生节点的 id，而不是加过滤。不变式的准确表述是"永不把易失 id 交给 agent"，
"过滤掉 `WorkingMemory`" 只是其中一种（有损的）满足方式。

门禁：vitest 491 通过（新增 18），`tsc --noEmit` 无输出。

## [3.1.4] - 2026-08-24

### 🐛 修复：同源节点列表混入 scheduler 短期副本

3.1.3 上线后实测：同源列表里每个 `key` **成对出现** —— 一条被切成 6 段的记忆列出了 12 条同源。

后端对每条抽取结果写两个节点：一个 `WorkingMemory` 短期副本 + 一个 `LongTermMemory`
（少数为 `UserMemory`）持久节点，`key` 与 `created_at` 逐字相同。`findSiblings` 没有滤层级，
于是短期副本一并列出。

**这不是新决策，是 3.1.0 已经做过的决定**（`memory-tier.ts`）。`memos_search` 与
`memos_list_v2` 早已在滤，`findSiblings` 是 3.1.2 新增的路径 —— 又漏了一处。
同一形态在本项目已出现五次：**新写的检索路径必须继承既有的分层过滤决定。**

逃生开关 `MEMOS_SHOW_WORKING_MEMORY=true` 时不滤，与 `filterEphemeralTier` 语义一致。
缺 `memory_type` 视为可见 —— Lite 的 JSONL 不写该字段。

#### 测试

新增 5 项分层断言（共 48 项），三个变异全部被捕获：不滤层级（回到本次缺陷）、
忽略逃生开关、忽略 limit。其中「limit 在滤层级之后生效」用交错排列的候选集断言 ——
顺序反了会让 limit 被随即隐藏的副本吃掉，只返回一半。

门禁：vitest 447 passed、tsc、pack 契约、schema budget +0.0%、semantic 快照 17 工具、
protocol v2、lite smoke、host-env smoke。

## [3.1.3] - 2026-08-24

### 🐛 修复：同源碎片区块从不出现 —— `sources` 有两种线上形态

3.1.2 上线后实测：原文能正确返回，但「同源碎片」区块**从不出现**。根因是同一个字段
在两个端点上形态不同：

| 端点 | `sources[0]` 的形态 |
|---|---|
| `GET /memories/{cube}/{id}`（单条） | **对象** `{type, role, chat_time, content}` |
| `GET /memories`（列表） | **JSON 字符串** `'{"type":...,"content":"..."}'` |

`verbatimOf` 初版只处理对象形态。单条取回走对象 → 原文正常；同源查找的候选集来自
列表端点 → 全部返回 null → 永远匹配不到。**原文层可用，配对层静默失效。**

单测没抓住的原因很直接：fixture 只造了对象形态，两种形态里只测了一种。

修法：抽出 `contentOf(entry)` 同时接受对象与 JSON 字符串。非 JSON 字符串返回 null
而**不猜它是裸原文** —— 否则任意字符串都会被当原文，把无关记忆归成同源。
坏 JSON 按无 content 处理不抛异常：这是展示层，脏数据不该让 `memos_get` 失败。

#### 测试

新增 6 项断言与一个 list 形态 fixture（共 43 项）。三个变异全部被捕获，
其中「不处理字符串形态」即回到本次修复前的行为，另两个覆盖「非 JSON 当裸原文」
与「坏 JSON 抛异常」。跨形态指纹一致性单独断言 —— 否则单条与列表永远配不上。

门禁：vitest 442 passed、tsc、pack 契约、schema budget +0.0%、semantic 快照 17 工具、
protocol v2、lite smoke、host-env smoke。

## [3.1.2] - 2026-08-23

### 📄 `memos_get` 返回原文，不再只返回 LLM 概括

开启 LLM 抽取（后端 `MOS_TYPED_SAVE_FAST=false`）时，后端把一次写入拆成多条细粒度记忆：
每条的 `memory` 字段是 LLM 概括，而**逐字原文完整保留在 `metadata.sources[0].content`**。
实测一条 1056 字的写入被拆成 5 条，每条 `memory` 约 244 字，5 条共享同一份原文。
`memos_get` 此前只读 `memory`，于是完整上下文取不回来。

这不是取舍问题 —— 库里本来就是两份数据，各有各的用途：

| 层 | 内容 | 用途 |
|---|---|---|
| `memory` | LLM 概括（细粒度） | 向量化输入、建边对象 → 决定图谱节点与联想质量 |
| `metadata.sources[].content` | 逐字原文 | `memos_get` 的完整上下文来源 |

**新输出结构**（有原文时）：原文作为 `### Content` 正文；LLM 概括降级到
`### 抽取概括` 区块并保留 —— 它是向量化与建边的实际输入，看得见才能判断图谱节点切得对不对；
`### 同源碎片` 列出由同一次写入抽出的其他记忆（id + key），从而能看出 LLM 的切分方式。
无原文时（fast-path 写入）输出与此前完全一致。

同源判定用原文全文，不用 `session_id` —— 同一会话里的无关写入会被错误归组。

新增 `src/verbatim-source.ts`：`verbatimOf` / `sourceFingerprint` / `findSiblings` /
`renderVerbatimSections`，四个纯函数，handler 与测试调用同一份实现。
Full 与 Lite 两条路径都已接线（Lite 的 JSONL 无同源概念，列表恒空）。
同源查询失败时返回空列表，不影响原文返回。

#### 测试

新增 `src/verbatim-source.test.ts`（37 项）。**变异验证抓出三个断言缺乏判别力**，
每一个都是「测试写了但等于没写」的形态：

- 接线守卫数两条路径**合计**调用次数 `>= 2`，而 Lite 路径自身就有 2 次，
  砍掉 Full 路径那次仍然通过。改为按路径分别断言。
- 「原文不截断」用 30 字测试原文，而变异截断到 200 字 —— 改不动它。
  测试原文改为 600+ 字并加尾部标记。**这条正是本次要修的缺陷，却最后才抓住。**
- `"not-an-array"[0]` 是字符 `"n"`、无 `.content`，宽松实现也返回 null。
  改用伪装成数组的对象才有判别力。

顺带删除 `sourceFingerprint` 的长度前缀：变异验证时构造不出它能防住的碰撞，
无测试支撑的防御代码比没有更糟。

12 个变异被捕获（W1「Full 路径不读原文」即回到本次修复前的行为）。
门禁：vitest 436/436、tsc、pack 契约、schema budget +0.0%、semantic 快照 17 工具、
protocol v2、lite smoke。

## [3.1.1] - 2026-08-22

### 🐛 修复：`memos_context_resume` 每条记忆成对出现

3.1.0 装好后 `memos_search` 与 `memos_list_v2` 都已正确隐藏 `WorkingMemory` 短期副本，
但 `memos_context_resume` 仍成对显示（10 条 = 5 对，内容逐字相同、UUID 不同）。

**根因不止是漏接一条路径。** temporal 查询的 Cypher 不返回 `memory_type`，
构造出的 metadata 只有 `relativity`/`temporal_rank`/`source` —— 于是分层判定永远
读到 `undefined` 并判为可见，**下游任何过滤对 temporal 记忆都是空转**。
受影响的是四个调用点，不只是 `memos_context_resume`：

| 路径 | 3.1.0 的状态 |
|---|---|
| `memos_context_resume` | 成对显示（用户实测发现） |
| `memos_search` temporal intent（两处） | 有过滤代码，但读不到字段 |
| `memos_think` | 同上 |

后三处一直漏着且不易察觉 —— 过滤代码存在且看起来合理，只是作用对象缺字段。

修法：在 Cypher 里排除 `WorkingMemory` 并返回 `memory_type`。这是唯一对四处都成立的做法，
且 `LIMIT` 在过滤之后 —— 要 N 条就得 N 条真记忆，无需超额取数。
`memos_context_resume` 的 API 回退路径由服务端施加 limit，无法先过滤，故超额取 3 倍。

逃生开关 `MEMOS_SHOW_WORKING_MEMORY=true` 仍然有效：为真时不加排除条件，
但仍返回 `memory_type` —— 开关只关过滤，不关可观测性。

#### 测试

新增 `src/context-resume.test.ts`（22 项），**9 个变异全部被捕获**，
其中 W1「API 路径不过滤」即回到本次报告的原缺陷。

新增 `npm run test:host-env-smoke`：用 MCP host 配置里的**原样环境**驱动 server，
且不继承外层环境变量。已有的 spread smoke 自带硬编码 Neo4j 凭据兜底，
因此「host 读不到凭据」这一失败形态它测不出来 —— 实测该形态下检索照常返回记忆、
但联想标注为 0，属静默降级。

门禁：vitest 416/416、tsc、pack 契约、schema budget +0.0%、semantic 快照 17 工具、
protocol v2、lite smoke、spread smoke、host-env smoke。

## [3.1.0] - 2026-08-22

### 🧠 检索排序：衰减、强化、分档去重与图扩散联想

本版把检索侧的排序从「纯相似度」改为「相似度 + 时间衰减 + 访问强化」，并加入按类型分档的
近重复折叠与一跳图扩散联想。

#### 记忆层级：`WorkingMemory` 默认隐藏

后端 scheduler 会为每条持久记忆写一份 `WorkingMemory` 短期副本，该层按用户仅保留最近 20 条、
每次检索都会重写淘汰。把这些 id 交给 agent 意味着它拿到的引用几分钟后就失效。
新增 `src/memory-tier.ts`，`memos_search` 与 `memos_list_v2` 默认滤掉该层；
逃生开关 `MEMOS_SHOW_WORKING_MEMORY=true` 可关闭过滤。缺 `memory_type` 视为可见
（Lite 的 JSONL 不写该字段）。

#### 衰减与强化

排序分数加入按 `created_at` 的时间衰减与按访问次数的强化项，两者都可用环境变量关掉，
默认开启。访问计数由 `src/access-tracker.ts` 本地维护，不写回后端。

#### 近重复折叠（按类型分档）

同类型内容高度重合的记忆折叠为一条并标注折叠数。分档按 `memory_type` ——
不同类型的相似文本（一条 `DECISION` 与一条 `BUGFIX`）不应互相折叠。

#### 一跳图扩散联想（`MEMOS_SPREAD_ACTIVATION`，默认关闭）

命中记忆沿知识图谱做一跳扩散，把强关联但关键词不匹配的记忆带进结果并标注来源。
默认关闭，因为它需要可用的 Neo4j 凭据；读不到凭据时静默返回 0 条联想。

#### 检索期注解

结果里标注衰减后分数、访问次数与折叠数，使排序结果可解释而非黑箱。

#### graph schema 四处缺陷修复

`memos_graph` 的 schema 模式修正四处：节点计数口径、边类型去重、孤立节点统计与采样上限。

## [3.0.1] - 2026-08-19

### 🩹 修复 3.0.0 打包出的多余依赖与失效仓库链接

3.0.0 的 npm 包声明了两个与运行时无关的依赖，并且 npm 页面上的仓库链接全部指向一个不存在的仓库。
功能没有受影响，但每个用户都要多下载约 17 MB，且 issue/homepage 链接是死链。

#### 修复

- **移除 `ci@^2.3.0` 与 `npm@^11.19.0`**。两者都不被 `dist/` 里的任何代码 import，属纯安装期膨胀：
  `npm` 是完整的 npm CLI（16 MB），`ci` 是无关的第三方工具（17 KB）。安装体积从约 30 MB 回到约 13 MB。
  根因是发布前工作区里未提交的依赖漂移被打进了 tarball；仓库提交本身一直只有三个依赖。
- **`repository` / `bugs` / `homepage` 从 `github.com/xigou/oh-memos` 改为 `github.com/lsg1103275794/oh-memos`**。
  前者返回 404，导致 npm 页面上的仓库、issue 和主页链接全部失效。`mcp-server-node/README.md`
  里的 clone 命令与仓库链接同步修正。

#### 不变

运行时行为、工具名、输入 schema、协议协商和持久化格式与 3.0.0 完全一致，仅包元数据与依赖清单变化。
从 3.0.0 升级只需重新安装，无需任何迁移。

## [3.0.0] - 2026-08-19

### Breaking

- **Node.js 20 is now the minimum runtime.** Node 18 users must stay on
  `oh-memos-mcp@2` (`npx -y oh-memos-mcp@2`) until they can upgrade their
  runtime. The entry point exits with an actionable message on Node 18 instead
  of failing with an opaque module error.
- The MCP runtime now uses the role-split `@modelcontextprotocol/server@2` and
  Zod 4 instead of the monolithic v1 SDK and Zod 3.

### Added

- **Dual-era stdio serving.** The same package accepts legacy 2025-era
  initialize clients and clients pinned to MCP `2026-07-28` through
  `serveStdio(..., { legacy: "serve" })`.
- Stringified `tools/call` arguments are normalized before era classification
  and schema validation, preserving the existing client compatibility path.
- Protocol, lifecycle, semantic-schema and package-boundary release gates now
  cover legacy/auto/modern clients, Full/Lite providers, 16/17 tools, large
  requests, probe fallback and graceful process shutdown.

### Migration

- Install with `npx -y oh-memos-mcp` (npm `latest`) or pin `oh-memos-mcp@3.0.0`.
- No memory, cube or Lite JSONL migration is required. Existing Full and Lite
  data formats, tool names and input schemas remain unchanged, so Agent
  configurations only need the package reference updated.
- Clients that still negotiate the 2025-era wire keep working unchanged; no
  client-side protocol migration is required to adopt 3.0.

### Rollback

- Pin Agent configurations to `npx -y oh-memos-mcp@2.1.0`. No data rollback is
  necessary because this release does not change persisted formats.
- `2.x` remains installable from npm; this release does not unpublish or
  deprecate it.

## [2.1.0] - 2026-08-16

### Fixed

- **Auto-discovered `.env` no longer overrides launcher environment.** A `.env`
  found in the working directory or package root now only fills missing values,
  so MCP client `env` blocks and shell exports such as `MEMOS_PROVIDER=local`
  stay in effect. A file selected explicitly through `MEMOS_ENV_FILE` or
  `--memos-env-file` remains authoritative.

### Added

- **Local Lite provider.** `MEMOS_PROVIDER=local` (implied by `MEMOS_MODE=lite`)
  serves `memos_save`, `memos_get`, `memos_list_v2`, `memos_search`, and
  `memos_context_resume` from a per-cube `memories.jsonl` with deterministic
  lexical ranking, durable appends, and a cross-process lock. Graph, Think,
  Wiki, and admin tools report `LOCAL_PROVIDER_UNSUPPORTED` rather than
  pretending a graph backend exists.

- **Skill candidate lifecycle.** `memos_review_skill_candidate` records
  approve/reject with reviewer audit metadata, and
  `memos_install_skill_candidate` installs only approved candidates into
  `.claude/skills/<slug>/SKILL.md` without overwriting, following symlinks, or
  executing anything.

- **Explainable graph provenance.** `memos_graph(mode="related"|"path"|"impact")`
  now reports normalized evidence categories (`EXTRACTED`, `INFERRED`,
  `AMBIGUOUS`, or `UNKNOWN`) and includes confidence, evidence references,
  source file/location, extractor version and verification time when those
  fields exist. Legacy graph data without provenance remains readable and is
  reported as `UNKNOWN` rather than assigned invented evidence.

- **`memos_graph(mode="import")` Graphify boundary.** Accepts up to 5 MB of
  Graphify/NetworkX node-link JSON through `graph_json`, validates `nodes` plus
  `links` (or the `edges` alias), and produces a deterministic import plan with
  portable stable Code Graph ids. Duplicate ids, dangling edges, unsafe source
  paths, invalid confidence values and oversized graphs are rejected before
  any persistence boundary. This mode is intentionally **dry-run only**: it
  never writes to Neo4j, Qdrant or a memory cube.

- **`memos_canvas`** — a symbolic task canvas: short-term task state that survives
  context compaction. One Mermaid file per task under
  `{MEMOS_CUBES_DIR}/{cube_id}/canvas/`, whose nodes carry a greppable id
  (`000-N1`) and an optional `ref` anchoring them to evidence:
  `mem:<memory_id>` (a memory in the graph), `file:<path>` (any file, including
  the large tool results the harness already offloads), or `note:<text>`.

  `action`: `open` (needs `goal`) · `update` (appends a node; `node_id` edits one
  in place) · `show` · `list`.

  Canvases are deliberately **not** written to Neo4j or Qdrant. A canvas changes
  several times an hour, and paying an embedding round trip for a `doing→done`
  flip would be absurd. Durable facts still go through `memos_save`; the canvas
  points at them with a `mem:` ref.

  This is **not** a token-saving feature. The design it borrows from
  ([TencentDB-Agent-Memory](https://github.com/TencentCloud/TencentDB-Agent-Memory))
  achieves its reduction by intercepting and replacing tool output before the
  model sees it, which a Claude Code hook cannot do — `PreToolUse` can rewrite a
  tool's *input* via `updatedInput`, but no hook can rewrite its *output*. What
  this offers instead is task state that survives compaction, and a path from a
  summary back to the evidence behind it.

  Node ids and canvas prefixes are allocated as max+1 and **never reuse a gap**:
  a deleted `000-N2` may still be cited from a commit message, a memory body or
  another node's ref, and handing that id to a new node would silently repoint
  every one of those citations.

- `memos_context_resume` now lists **unfinished** canvases first — headlines and
  counts only, a few dozen tokens — so the first thing visible after a compaction
  is the open work rather than a memory feed. Injecting canvas bodies here would
  rebuild the very context bloat the canvas exists to avoid; the model opens what
  it needs with `show`.

- **Test infrastructure.** This package previously had none: no test script, no
  `*.test.ts`. Adds vitest and `npm test`, with 65 unit tests covering the
  parse/render round trip, node-id allocation, Mermaid label injection, path
  traversal refusal and atomic writes. `scripts/canvas-e2e.mjs` adds 18 checks
  driven over real MCP stdio rather than mocks.

- `MEMOS_ENV_FILE` env var and `--memos-env-file` flag, to point the server at an
  explicit `.env`. Previously the file was located only by guessing from position
  (cwd, two levels above the package, dotenv's upward search) — which works from
  a checkout and never works under `npx`, where the package root sits in the npm
  cache and every candidate misses, loading not one variable. A path that does
  not exist now warns on stderr rather than falling through silently.

### Fixed

- `toLocalPath()` rewrote Windows cube paths to `/mnt/...` unconditionally. That
  mapping only resolves inside WSL; under native Windows Node the result is not
  absolute, so it resolved against the current drive and every cube write landed
  in a phantom tree while the API kept reading the real path. Registration
  reported success, then `/search` and `/memories` failed 400 — the loaded cube
  had no memory backend.

### Security

- `canvasPath` is the one place caller text becomes a filesystem path. It uses a
  **whitelist** (`[a-z0-9-]`) rather than a blacklist of dangerous characters,
  because a blacklist is always missing an entry. `.` is outside the whitelist,
  so `..` cannot survive it — traversal is structurally impossible rather than
  merely checked for — and a post-resolve containment check backs that up
  independently. `cube_id` is treated as untrusted too, since it is derived from
  a caller-supplied `project_path`.

### Documentation

- The `alwaysAllow` example carried two defects. `memos_search` appeared twice,
  and several entries were **call forms** — `memos_admin(action=list_cubes)` and
  the like. `alwaysAllow` matches tool names, so those entries matched nothing:
  a reader would believe those calls were pre-approved and still be prompted for
  every one. Replaced with bare tool names, which auto-approve every action of
  the tool.
- `memos_delete` was dropped from that example, which also set
  `MEMOS_ENABLE_DELETE: "true"` — together they auto-approve deleting memories
  with no prompt. Enabling that is a decision worth making deliberately.
- The `.env` note claimed the working directory's file loads "automatically with
  highest priority". Under `npx` no file loads at all. Documented `MEMOS_ENV_FILE`
  and what actually happens.

### Notes

- Tool surface grew 12488 B → 13680 B (+9.5%), past the +5% drift budget, and the
  baseline was re-frozen. This is the cost of a new tool rather than description
  drift; the description was trimmed from 1333 B to 1192 B first, moving detail
  into `show`'s output (the same move `memos_suggest` made with the memory-type
  decision tree).
- `tsconfig.json` now excludes `src/**/*.test.ts`. Without it the test files
  compile into `dist` and ship with `npm publish`.

---

## [2.0.1] — 2026-08-02

### Fixed

- MCP `serverInfo` was hardcoded in `server.ts` and reported
  `{name: "memos-memory", version: "1.0.1"}` — a name matching neither the
  package (`oh-memos-mcp`) nor the conventional server key (`oh-memos`), and a
  version that 2.0.0 shipped stale. Clients display this during the handshake.
  It is now read from `package.json` at startup, so it cannot drift again.

---

## [2.0.0] — 2026-08-02

### ⚠️ Breaking — tool surface consolidated from 18 to 10

Eleven tools were merged into three dispatching tools. **There is no compatibility
shim**: the MCP SDK only dispatches registered tools, so calling a removed name now
returns `Unknown tool`.

If your MCP client config pins tool names (e.g. Claude Code's `alwaysAllow` list),
you must update it before upgrading.

#### Migration

| 1.x tool | 2.0 replacement |
|----------|-----------------|
| `memos_search_context` | `memos_search` — pass the `context` array (recent turns) |
| `memos_get_graph` | `memos_graph(mode="related")` |
| `memos_trace_path` | `memos_graph(mode="path")` |
| `memos_impact` | `memos_graph(mode="impact")` |
| `memos_export_schema` | `memos_graph(mode="schema")` |
| `memos_list_cubes` | `memos_admin(action="list_cubes")` |
| `memos_register_cube` | `memos_admin(action="register_cube")` |
| `memos_create_user` | `memos_admin(action="create_user")` |
| `memos_validate_cubes` | `memos_admin(action="validate_cubes")` |
| `memos_get_stats` | `memos_admin(action="stats")` |
| `memos_calendar` | `memos_admin(action="calendar")` |

Unchanged: `memos_context_resume`, `memos_search`, `memos_save`, `memos_list_v2`,
`memos_get`, `memos_suggest`, `memos_delete`.

`alwaysAllow` for 2.0:

```json
"alwaysAllow": [
  "memos_context_resume", "memos_search", "memos_save",
  "memos_list_v2", "memos_get", "memos_suggest",
  "memos_think", "memos_graph", "memos_admin", "memos_export_wiki"
]
```

### Added

- **`memos_think`** — evidence pack for a question. Runs semantic retrieval plus a
  recent-72h temporal pass, deduplicates, and returns numbered evidence with graph
  relationships between items, contradiction/evolution candidates, staleness
  candidates, and gap analysis. Synthesis is deliberately left to the calling model;
  the server emits no prose. Results can be persisted back as `SYNTHESIS`.
- **`memos_export_wiki`** — export a cube as an interlinked markdown wiki: one page
  per memory (YAML frontmatter, `[[wikilink]]` relations), plus `index.md` and a
  mermaid `graph.md`. Only files carrying the generator marker are ever replaced;
  foreign files in the output directory are preserved. Defaults to
  `<project_path>/docs/memory-wiki`.
- **`SYNTHESIS`** memory type, for answers synthesized from retrieved evidence.

### Changed

- Tool-surface cost dropped ~51%: `tools/list` payload 22.9 KB → 11.2 KB
  (≈5850 → ≈2856 tokens). Shared `project_path` / `cube_id` parameter descriptions
  were deduplicated; the full cube-routing rules are now stated once, on
  `memos_save` and `memos_search`.
- Runtime error `suggestions` now name the 2.0 call forms, so a model reading a
  failure message is no longer told to call a tool that does not exist.

### Fixed

- `memos_admin`'s `cube_id` no longer carries a `MEMOS_DEFAULT_CUBE` default.
  Previously, calling `register_cube` without `cube_id` would silently register the
  default cube instead of failing.

---

## [1.0.0] — 2026-03-04

Initial npm release. 18 tools, Node-only MCP server for oh-memos — no Python
required, runs via `npx`.
