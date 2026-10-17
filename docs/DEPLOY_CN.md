# 原生 Windows 部署指南

在 Windows 上以本地 Python 进程运行 oh-memos。

> **推荐方式是 Docker**（见 [README](../README_CN.md#快速开始)）：一条命令拉起 API、Neo4j 和 Qdrant，配置面更小。
> 本文档面向需要直接调试 Python 代码，或不便运行 Docker 的场景。
>
> 已有 Windows 部署想迁到 Docker，见本文末尾的[数据迁移](#数据迁移windows--docker)。

---

## 目录

- [环境要求](#环境要求)
- [快速部署](#快速部署)
- [环境变量配置](#环境变量配置)
  - [必填项](#必填项)
  - [数据库](#数据库)
  - [LLM 与嵌入模型](#llm-与嵌入模型)
- [完整配置示例](#完整配置示例)
- [服务管理](#服务管理)
- [Web 记忆管理界面](#web-记忆管理界面)
- [数据迁移（Windows → Docker）](#数据迁移windows--docker)
- [常见问题](#常见问题)

---

## 环境要求

| 组件 | 最低要求 | 说明 |
|------|---------|------|
| 操作系统 | Windows 10 | Windows 10/11 |
| 内存 | 8GB | tree_text 模式需同时运行 Neo4j 与 Qdrant |
| 磁盘空间 | 5GB+ | 依赖约 1.5GB，其余为记忆数据 |
| Python | 3.10+ | 推荐 3.11 |
| Neo4j | 5.x | `tree_text` 模式必需 |
| Qdrant | 1.16+ | 本地二进制或 Docker |

`general_text` 模式（仅向量检索）不需要 Neo4j。

---

## 快速部署

### 第一步：创建 Python 环境

```cmd
VENV_scripts\setup_venv.bat
```

环境会创建在项目下的 `.venv\`，可执行文件位于 `.venv\Scripts\python.exe`。

### 第二步：安装依赖并启动

```cmd
install_run.bat
```

首次运行安装全部依赖，之后用 `run.bat` 启动即可。

### 第三步：验证

```powershell
Invoke-RestMethod http://localhost:18000/health/detail
```

`tree_text` 模式下 `neo4j` 与 `qdrant` 两个组件都应为 `ok`。API 文档在
<http://localhost:18000/docs>。

> `/health` 即使某个组件不可用也会返回 HTTP 200 —— 判断依据是响应体里的
> `data.status`，不是状态码。

---

## 环境变量配置

配置文件是项目根目录的 `.env`，从模板复制：

```powershell
Copy-Item .env.example .env
```

`.env.example` 每一项都有中文注释，下面只列必须动的部分。

> **变量名必须与下表完全一致。** 服务只读取这些名字，写错的变量会被静默忽略，
> 表现为「配置了但不生效」，然后回落到默认值。

### 必填项

| 变量 | 说明 |
|------|------|
| `MEMOS_CUBES_DIR` | cube 目录的**绝对路径**，例如 `G:/test/oh-memos/data/oh-memos_cubes` |
| `MEMOS_USER` | 默认用户 ID，通常保持 `dev_user` |
| `MEMOS_DEFAULT_CUBE` | 默认 cube，通常保持 `dev_cube` |
| `MOS_TEXT_MEM_TYPE` | `tree_text`（知识图谱）或 `general_text`（仅向量） |

### 数据库

```env
# Neo4j —— tree_text 模式必填
NEO4J_BACKEND=neo4j-community
NEO4J_URI=bolt://localhost:7687
NEO4J_HTTP_URL=http://localhost:7474/db/neo4j/tx/commit
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DB_NAME=neo4j

# Qdrant 本地模式
QDRANT_HOST=localhost
QDRANT_PORT=16333

# Qdrant 云模式（设置 QDRANT_URL 后 HOST/PORT 会被忽略）
# QDRANT_URL=https://your-cluster.cloud.qdrant.io
# QDRANT_API_KEY=your_api_key
```

Qdrant 默认端口用 16333 而非 6333，是为了避开 Windows 的动态端口排除范围。

### LLM 与嵌入模型

LLM 用于记忆提炼（提取 key、tags、置信度评分），`tree_text` 模式必需。

```env
# 聊天 / 提炼模型（OpenAI 兼容接口即可，包括本地中转）
MOS_CHAT_MODEL_PROVIDER=openai
MOS_CHAT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-your_key
OPENAI_API_BASE=https://api.openai.com/v1

# 嵌入模型
EMBEDDING_DIMENSION=1024
MOS_EMBEDDER_BACKEND=universal_api
MOS_EMBEDDER_PROVIDER=openai
MOS_EMBEDDER_MODEL=text-embedding-3-small
MOS_EMBEDDER_API_BASE=https://api.openai.com/v1
MOS_EMBEDDER_API_KEY=sk-your_key
```

改用本地 Ollama 嵌入：

```env
MOS_EMBEDDER_BACKEND=ollama
MOS_EMBEDDER_MODEL=nomic-embed-text:latest
MOS_EMBEDDER_API_BASE=http://localhost:11434
EMBEDDING_DIMENSION=768
```

> **`EMBEDDING_DIMENSION` 必须与模型实际输出维度一致**，且**不能在已有数据后更改** ——
> Qdrant collection 的维度在创建时固定，改了会导致既有向量无法检索。
> 换模型前先确认维度：`text-embedding-3-small` 是 1536，`BAAI/bge-m3` 是 1024，
> `nomic-embed-text` 是 768。

---

## 完整配置示例

以本地 Neo4j + 云端嵌入为例：

```env
# ---- 基础 ----
MEMOS_CUBES_DIR=G:/test/oh-memos/data/oh-memos_cubes
MEMOS_USER=dev_user
MEMOS_DEFAULT_CUBE=dev_cube
MEMOS_BASE_PATH=.
TZ=Asia/Shanghai

# ---- 记忆模式 ----
MOS_TEXT_MEM_TYPE=tree_text
MOS_ENABLE_REORGANIZE=true
ASYNC_MODE=sync
MOS_TOP_K=7

# ---- Neo4j ----
NEO4J_BACKEND=neo4j-community
NEO4J_URI=bolt://localhost:7687
NEO4J_HTTP_URL=http://localhost:7474/db/neo4j/tx/commit
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DB_NAME=neo4j

# ---- Qdrant ----
QDRANT_HOST=localhost
QDRANT_PORT=16333

# ---- LLM ----
MOS_CHAT_MODEL_PROVIDER=openai
MOS_CHAT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-your_key
OPENAI_API_BASE=https://api.openai.com/v1
MOS_CHAT_TEMPERATURE=0.8
MOS_MAX_TOKENS=6000

# ---- 嵌入 ----
EMBEDDING_DIMENSION=1024
MOS_EMBEDDER_BACKEND=universal_api
MOS_EMBEDDER_PROVIDER=openai
MOS_EMBEDDER_MODEL=BAAI/bge-m3
MOS_EMBEDDER_API_BASE=https://api.siliconflow.cn/v1
MOS_EMBEDDER_API_KEY=sk-your_key

# ---- 自动归档 ----
MEMOS_AUTO_ARCHIVE=true
MEMOS_ARCHIVE_TTL_DAYS=7
MEMOS_ARCHIVE_TYPES=PROGRESS
```

---

## 服务管理

| 操作 | 命令 |
|------|------|
| 启动全部（数据库 + API） | `scripts\local\start.bat` |
| 仅启动数据库 | `scripts\local\start_db_silent.bat` |
| 停止数据库 | `scripts\local\stop_db_silent.bat` |
| 查看状态 | `scripts\local\oh_memos_status.bat` |
| 关闭后台写任务后启动 API | `scripts\local\start_api_no_bg.bat` |

`start.bat` 里的 `NEO4J_HOME` 与 `QDRANT_HOME` 是本机路径，需按实际安装位置修改。

`start_api_no_bg.bat` 用于**与 Docker 栈共享同一套数据库**的场景：它禁用归档与
图谱重组，并让该实例的 `POST /archive/run` 返回 409。两侧共享数据库时，写入必须
只走一侧 —— 详见 [README 的部署边界](../README_CN.md#部署与安全边界)。

---

## Web 记忆管理界面

多项目并行时，用 Web GUI 人工浏览和清理记忆：

```cmd
memory-admin.bat
```

访问 <http://127.0.0.1:18010>。它直连 Neo4j 与 Qdrant，API 未启动时同样可用。
功能与截图见 [README](../README_CN.md#web-记忆管理界面)。

---

## 数据迁移（Windows → Docker）

已有 Windows 部署要搬进 Docker 卷，用分阶段迁移脚本，默认不删任何数据：

```powershell
# 0. 从现有 .env 生成迁移配置（密钥自动继承，localhost 自动改为 host.docker.internal）
powershell -File scripts/migrate/build_migration_env.ps1

# 1. 检查前置条件并输出源数据清单（只读）
powershell -File scripts/migrate/migrate_win_to_docker.ps1 -Stage preflight

# 2. 停服务、产出备份与 hash manifest
powershell -File scripts/migrate/migrate_win_to_docker.ps1 -Stage backup

# 3. 灌进 Docker 卷
powershell -File scripts/migrate/migrate_win_to_docker.ps1 -Stage restore

# 4. 与 manifest 逐项对账
powershell -File scripts/migrate/migrate_win_to_docker.ps1 -Stage verify

# 5. 删除 Windows 源数据（不可逆）
powershell -File scripts/migrate/migrate_win_to_docker.ps1 -Stage cleanup -ConfirmWindowsPurge
```

三个必须注意的点：

- **Neo4j 要先对齐版本再升级**。迁移用与源同版本的 Docker Neo4j 载入；成功后才单独
  升级到目标版本。新版本打开旧 store 会做一次不可逆的 store 迁移，两件事同时做会让
  失败无法定位。原始 dump 是唯一回滚点。
- **Qdrant 不能降级**。目标版本必须 ≥ 源版本，旧版本不保证能打开新版本的 storage。
- **`cleanup` 是永久删除**，备份保留在 `OH_MEMOS_MIGRATION_DIR`（默认
  `D:\oh-memos-migration`）。执行前确认 `verify` 全绿。

迁移后 cube 目录路径不变，MCP 与第三方接入无需改配置。

---

## 常见问题

### Q: 启动提示 "Python not found"

先运行 `VENV_scripts\setup_venv.bat` 创建 `.venv` 环境。

### Q: 配置了但不生效

检查变量名是否与[环境变量配置](#环境变量配置)完全一致。写错的名字会被静默忽略并
回落到默认值 —— 最常见的表现是 embedder 明明配了云端却仍去连本地 Ollama。

另外注意 `.env` 的行内注释：值与 `#` 之间要有空格，否则注释会被当成值的一部分。

### Q: Neo4j 连接失败

1. 确认服务在跑：`scripts\local\oh_memos_status.bat`
2. Neo4j 5.x 需要 Java 17+，确认 `JAVA_HOME` 已设置
3. 首次启动需要改初始密码，且要与 `.env` 中的 `NEO4J_PASSWORD` 一致

### Q: Qdrant 连接失败

1. 确认 `QDRANT_PORT` 与 Qdrant 实际监听端口一致（本项目默认 16333，不是 6333）
2. 云模式确认 `QDRANT_URL` 与 `QDRANT_API_KEY`，此时 `QDRANT_HOST`/`PORT` 会被忽略
3. 若数据库跑在 Docker 里而客户端在宿主机，把 `localhost` 换成 `127.0.0.1` ——
   Windows 11 会把 `localhost` 优先解析为 IPv6 `::1`，而 Docker 只监听 IPv4，
   每次请求会白等约 5 秒连接超时

### Q: 嵌入模型报错

用 Ollama 时确认服务在跑并已拉取模型：

```bash
ollama list
ollama pull nomic-embed-text
```

同时确认 `EMBEDDING_DIMENSION` 与模型输出维度一致。

### Q: 端口 18000 被占用

先确认占用者：

```powershell
netstat -ano | findstr ":18000 "
```

若被 Docker 栈占用，两者不能同时绑定同一端口。**Docker Desktop 在端口已被占用时会
静默跳过绑定**，此时 `http://127.0.0.1:18000` 返回的是另一个进程 —— 用
`docker port oh-memos-api` 核对实际绑定。

### Q: 记忆数据存储在哪里？

| 数据 | 位置 |
|------|------|
| 图节点与关系 | Neo4j |
| 向量 | Qdrant |
| 用户与 cube 注册表 | `{MEMOS_BASE_PATH}/.memos/memos_users.db` |
| cube 配置与任务画布 | `{MEMOS_CUBES_DIR}/{cube_id}/` |

---

## 相关链接

- [README](../README_CN.md) · [架构说明](../ARCHITECTURE.md)
- [MCP 配置指南](MCP_GUIDE.md)
- [更新日志](CHANGELOG.md)
- [Qdrant Cloud](https://cloud.qdrant.io/) · [Ollama](https://ollama.ai/)
