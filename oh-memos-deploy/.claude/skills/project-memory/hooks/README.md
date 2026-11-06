# oh-memos Hooks

Claude Code hooks that wire oh-memos into your session — context injection, intent
detection, milestone prompts, and guardrails against hand-rolled memory directories.

## Quick Start

Hook configuration lives in a single file: **[`settings-template.json`](settings-template.json)**.

Copy its `hooks` section into your `~/.claude/settings.json` (or the project's
`.claude/settings.json`), then replace every `<MEMOS_PATH>` with your oh-memos
install path.

```bash
# 查看模板
cat project-memory/hooks/settings-template.json

# 把 <MEMOS_PATH> 替换成你的安装路径，例如：
#   Linux / WSL   →  /mnt/g/test/oh-memos
#   Windows       →  G:/test/oh-memos
```

The hooks are Node.js scripts and run unchanged on Windows, WSL, Linux and macOS —
`node` on PATH is the only requirement.

## 已接入模板的 Hooks

| Hook | 事件 | 功能 |
|------|------|------|
| `oh_memos_session_start.js` | SessionStart | 输出 CWD → cube_id 映射 |
| `oh_memos_user_prompt.js` | UserPromptSubmit | 意图检测（历史 / 报错 / 决策）→ 建议 `memos_search` |
| `oh_memos_context_inject.js` | PreToolUse `Grep\|Glob\|Read\|Edit\|Write` | 按工具参数检索记忆，命中时写进 `hookSpecificOutput.additionalContext` 送给模型；没命中或出错时什么都不输出。读 `MEMOS_URL`、`MEMOS_USER`（默认 `http://localhost:18000`、`dev_user`） |
| `oh_memos_block_sensitive.js` | PreToolUse `Edit\|Write` | 编辑 `.env` / credentials 等敏感文件前告警 |
| `oh_memos_block_mkdir_memory.js` | PreToolUse `Bash` | 拦截 `mkdir.*memory`，强制走 MCP 工具 |
| `oh_memos_block_memory_write.js` | PreToolUse `Write\|Edit\|MultiEdit\|NotebookEdit` | 拦截 Claude Code **内置 file-based memory** 写入，并在 stderr 指明改用 `oh_memos_save` |
| `oh_memos_log_commands.js` | PostToolUse `Bash` | 记录命令历史备查 |
| `oh_memos_auto_save.js` | PostToolUse `Bash\|Edit\|Write` | 建议 `memory_type` 与 `project_path` |
| `oh_memos_notify_milestone.js` | PostToolUse `Edit\|Write` | 改动重要文件时提示存 MILESTONE |
| `oh_memos_pre_compact.js` | PreCompact | 提醒用 MCP 工具而非 `mkdir` 重建记忆 |
| `oh_memos_auto_capture.js` | PreCompact | **默认关闭**；`MEMOS_AUTO_CAPTURE=true` 后把有界会话 checkpoint 低置信度写入 API，失败开放且按 session/event 去重 |

The automatic capture hook is deliberately opt-in:

```text
MEMOS_AUTO_CAPTURE=true
MEMOS_AUTO_CAPTURE_MAX_CHARS=6000
MEMOS_AUTO_CAPTURE_TIMEOUT_MS=2500
```

It accepts a Claude hook JSON payload on stdin, keeps only bounded `summary`/
`context`/checkpoint text, and calls the existing `/memories` API. The API remains
the credential-redaction boundary. `MEMOS_MODE=lite` disables capture even when the
flag is set. API failures never block the assistant. The hook stores a hash marker
under the operating system temp directory so repeated PreCompact events do not
write the same checkpoint twice. It does not capture every PostToolUse result and
it never installs skills automatically.


| Hook | 说明 |
|------|------|
| `oh_memos_suggest_compact.js` | 上下文用量监控，70% / 90% 时告警。文件存在但未写进 `settings-template.json`，需要的话自行添加 |

## 文件结构

```
project-memory/hooks/
├── README.md
├── settings-template.json        ← 唯一配置入口，用 <MEMOS_PATH> 占位符
│
├── node/                         ← 跨平台实现（Windows / WSL / Linux / macOS）
│   ├── oh_memos_session_start.js
│   ├── oh_memos_user_prompt.js
│   ├── oh_memos_context_inject.js
│   ├── oh_memos_block_sensitive.js
│   ├── oh_memos_block_mkdir_memory.js
│   ├── oh_memos_block_memory_write.js
│   ├── oh_memos_log_commands.js
│   ├── oh_memos_auto_save.js
│   ├── oh_memos_notify_milestone.js
│   ├── oh_memos_pre_compact.js
│   ├── oh_memos_auto_capture.js
│   └── oh_memos_suggest_compact.js
│
└── powershell/                   ← 纯 Windows 的部分实现（无配置模板，需手写）
    ├── oh_memos_user_prompt.ps1
    ├── oh_memos_user_prompt.cmd
    ├── oh_memos_block_sensitive.ps1
    ├── oh_memos_log_commands.ps1
    └── oh_memos_notify_milestone.ps1
```

> `powershell/` 只覆盖 4 个 hook，且不再随附 `settings.json`。它存在的前提是你不想装
> Node —— 但 oh-memos 的 MCP server 本身就需要 Node，所以绝大多数情况直接用 `node/`
> 即可。

## 内置 file-based memory 与 MCP oh-memos 的冲突

Claude Code 2.x 自带一套 **file-based memory**。它的 system prompt 直接指示 agent 往

```
~/.claude/projects/<encoded-project>/memory/*.md
```

写 markdown（带 `name` / `description` / `metadata.type` frontmatter，外加 `MEMORY.md` 索引），
并明确说"目录已存在，直接 Write，不要 mkdir、不要检查存在性"。

这和"所有记忆走 MCP oh-memos"的项目规则直接冲突，而 **system prompt 优先级高于 CLAUDE.md**，
所以光在 CLAUDE.md 里写禁令是拦不住的 —— agent 不是无视项目规则，是在服从更高优先级的指令。

`oh_memos_block_memory_write.js` 补的就是这个缺口。它刻意不做纯阻断：exit 2 的同时在 stderr
里点名 `oh_memos_save(project_path=<cwd>)` 和可选的 `memory_type`，让 agent 收到反馈后**换工具**，
而不是按 system prompt 反复重试同一个 Write、白烧 turn。

作用域刻意收窄，只认内置 memory 目录：

| 路径 | 行为 |
|------|------|
| `~/.claude/projects/<proj>/memory/note.md` | 拦 |
| `~/.claude/projects/<proj>/memory/MEMORY.md` | 拦 |
| `~/.claude/projects/<proj>/memory/data.json` | 放行（非 markdown） |
| 项目内 `project-memory/SKILL.md` | 放行 |
| 项目内 `docs/memory-wiki/index.md` | 放行 |

> matcher 必须覆盖 `Edit`，不能只写 `Write` —— 否则 agent 改用 Edit 就绕过去了。

## matcher 语法陷阱

`matcher` **只对工具名求值**。按[官方文档](https://code.claude.com/docs/en/hooks)：

| matcher 取值 | 求值方式 |
|---|---|
| `"*"` / `""` / 省略 | 匹配全部 |
| 只含字母数字 `_` `-` 空格 `,` `\|` | 精确字符串，或用 `\|` / `,` 分隔的列表 |
| **含任何其他字符** | **当作非锚定 JavaScript 正则** |

所以这种写法是**静默失效**的，没有任何报错：

```json
"matcher": "tool == \"Bash\" && tool_input.command matches \"mkdir.*memory\""
```

含 `=` `"` `&` → 整串被当正则去匹配工具名 `Bash` → 永远匹配不上 → hook 一次都不触发。

正确做法是 matcher 只写工具名，参数级条件放到脚本里判断（本目录所有 hook 都这么做），
或者用单个 handler 上的 `if` 字段（permission rule 语法，如 `"Edit(*.ts)"`）。

自查一行：

```js
const ok = /^[A-Za-z0-9_\-, |*]*$/.test(matcher);  // false → 被当正则 → 极可能失效
```

### CI 门禁

两道门禁守着这类问题，CI 的 `hooks` job 会跑，本地也能直接跑：

```bash
node scripts/lint-hook-matchers.mjs    # 所有已跟踪 hook 配置的 matcher 合规性
node scripts/sync-deploy-hooks.mjs     # deploy bundle 与本目录是否同步
node scripts/sync-deploy-hooks.mjs --write   # 同步过去
```

`lint-hook-matchers.mjs` 只扫**已跟踪**文件 —— 发出去的才算数，编辑器本地配置
（`.vscode/settings.json` 是 JSONC 不是 JSON，`.trae/` 整个被 ignore）不该产生噪音。
它同时校验模板引用的脚本真实存在，避免改名后模板指向空文件。

`oh-memos-deploy/.claude/skills/project-memory/hooks/` 是随发布走的副本。它曾经
drift 过（留着旧 exit code、缺 memory 守卫），所以现在是**校验**而不是信任。

`mcp-server-node/src/block-memory-write-hook.test.ts` 另有 16 项断言覆盖 hook 行为
与本目录模板的 matcher。

## 阻断必须用 exit 2

PreToolUse 阻断工具调用**只有 exit 2 有效**。`exit 1` 是非阻断错误，工具照样执行 ——
这是个很容易写错且不会报错的地方。

```js
process.exit(2);  // 阻断
process.exit(1);  // ✗ 不阻断，只是记个错
```

也可以 exit 0 配 JSON `{hookSpecificOutput:{hookEventName:"PreToolUse",
permissionDecision:"deny",permissionDecisionReason:"..."}}`，但 exit 2 是文档保证的硬阻断，
不依赖客户端对 `permissionDecision` 的支持，更稳。

## 测试 hook 的坑

用 shell 的 `echo` 喂 JSON 测 Windows 路径**不可信**：

```bash
# ✗ bash 会吃掉一层反斜杠，JSON 解析失败，hook 走 fail-open，
#   于是你得到一个假的"没拦住"结论
echo '{"tool_input":{"file_path":"C:\\Users\\x\\.claude\\..."}}' | node hook.js
```

正确做法是绕开 shell 转义层，用 `execFileSync` 的 `input` 直接喂：

```js
execFileSync(process.execPath, [hook], { input: JSON.stringify(payload), encoding: "utf8" });
```

路径也别写字面量，用 `String.fromCharCode(92)` 拼，源码层面就没有转义歧义。
参考 `mcp-server-node/src/block-memory-write-hook.test.ts`。

注意 exit 2 会让 `execFileSync` 抛异常，要 catch 后读 `err.status`，否则测试会误报。

## 自定义

**添加敏感文件模式** — 编辑 `node/oh_memos_block_sensitive.js`：

```javascript
const sensitivePatterns = [
  '.env',
  'credentials',
  'your_pattern_here'
];
```

**添加里程碑文件** — 编辑 `node/oh_memos_notify_milestone.js`：

```javascript
const milestoneFiles = [
  'README.md',
  'your_file_here'
];
```

## 调试

```bash
claude --debug
```

## 相关文档

- [MCP Guide](../../docs/MCP_GUIDE.md) — MCP 记忆工具
- [CLAUDE.md](../../CLAUDE.md) — 项目配置
