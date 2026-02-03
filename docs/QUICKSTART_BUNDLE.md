# MemOS 整合包快速开始 | Quick Start Guide

> 让小白用户也能轻松使用 MemOS 项目记忆系统
> Easy setup for MemOS project memory system

---

## 系统要求 | System Requirements

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11 (64-bit) 或 Linux (x86_64) |
| 内存 | 最低 4GB，推荐 8GB+ |
| 磁盘空间 | ~3GB（运行时 + 数据） |
| 网络 | 首次安装需要网络（下载运行时组件） |

---

## 快速安装 | Quick Install

### Windows

```cmd
:: 1. 解压整合包到任意目录
:: 2. 双击运行安装脚本
scripts\bundle\install.bat

:: 3. 编辑 .env 配置你的 LLM API Key
notepad .env

:: 4. 配置 MCP 到 Claude Code
scripts\bundle\configure_mcp.bat

:: 5. 启动所有服务
scripts\bundle\start.bat
```

### Linux / macOS

```bash
# 1. 解压整合包
# 2. 运行安装脚本
chmod +x scripts/bundle/*.sh
bash scripts/bundle/install.sh

# 3. 编辑 .env 配置你的 LLM API Key
nano .env

# 4. 配置 MCP 到 Claude Code
bash scripts/bundle/configure_mcp.sh

# 5. 启动所有服务
bash scripts/bundle/start.sh
```

---

## 详细步骤 | Detailed Steps

### Step 1: 安装 | Install

运行 `install.bat`（Windows）或 `install.sh`（Linux），脚本会自动：

1. 检查并下载 Miniconda（Python 3.11）
2. 检查并下载 OpenJDK 17（Neo4j 依赖）
3. 检查并下载 Neo4j Community Edition
4. 检查并下载 Qdrant 向量数据库
5. 安装 Python 依赖包

如果某个组件已存在，会自动跳过。

### Step 2: 配置 LLM | Configure LLM

编辑项目根目录下的 `.env` 文件，配置 LLM API：

**选项 A: 使用 OpenAI / 兼容 API**此选项可以参考# "G:\test\MemOSlocal_backup\docs\Free-API\Free api.md"里的关于免费API提供选项

```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1
MOS_CHAT_MODEL=gpt-4o-mini
MOS_EMBEDDER_API_KEY=sk-your-api-key-here
```

**选项 B: 使用本地 Ollama（免费）**

```env
MOS_CHAT_MODEL_PROVIDER=ollama
MOS_CHAT_MODEL=llama3
MOS_EMBEDDER_BACKEND=ollama
MOS_EMBEDDER_MODEL=nomic-embed-text
```

> 使用 Ollama 需要先安装 [Ollama](https://ollama.com/) 并下载模型：
> ```bash
> ollama pull llama3
> ollama pull nomic-embed-text
> ```

### Step 3: 配置 MCP | Configure MCP

运行 `configure_mcp.bat`（Windows）或 `configure_mcp.sh`（Linux），按照提示将 MCP 配置添加到 Claude Code。

MCP 服务名称为 `memoslocal`，配置示例：

```json
{
  "mcpServers": {
    "memoslocal": {
      "command": "/path/to/runtime/conda/python",
      "args": ["/path/to/mcp-server/memos_mcp_server.py"],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_CUBES_DIR": "/path/to/data/memos_cubes"
      }
    }
  }
}
```

### Step 4: 启动 | Start

运行 `start.bat`（Windows）或 `start.sh`（Linux），脚本会按顺序启动：

1. **Qdrant** - 向量数据库（端口 6333）
2. **Neo4j** - 知识图谱（端口 7474/7687）
3. **MemOS API** - 核心 API（端口 18000）

### Step 5: 使用 | Usage

在 Claude Code 中即可使用以下记忆工具：

| 工具 | 功能 |
|------|------|
| `memos_search` | 搜索项目记忆 |
| `memos_save` | 保存新记忆 |
| `memos_list` | 列出已有记忆 |
| `memos_list_cubes` | 列出 Memory Cubes |
| `memos_suggest` | 智能搜索建议 |
| `memos_search_context` | 上下文感知搜索 |
| `memos_get_graph` | 查看记忆关系图 |
| `memos_trace_path` | 追踪记忆关联路径 |

---

## 服务地址 | Service URLs

| 服务 | 地址 |
|------|------|
| MemOS API | http://localhost:18000/docs |
| Neo4j Browser | http://localhost:7474 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---

## 停止服务 | Stop Services

```cmd
:: Windows
scripts\bundle\stop.bat

:: Linux / macOS
bash scripts/bundle/stop.sh
```

---

## 常见问题 | FAQ

### Q: 安装时下载速度很慢？

**A:** 可以手动下载组件放到 `runtime/` 目录：
- `runtime/conda/` - Miniconda
- `runtime/jre/` - OpenJDK 17 JRE
- `runtime/neo4j/` - Neo4j Community
- `runtime/qdrant/` - Qdrant

### Q: Neo4j 启动失败？

**A:** 检查：
1. Java 是否正确安装：`runtime\jre\bin\java -version`
2. 端口 7687/7474 是否被占用
3. Neo4j 日志：`runtime\neo4j\logs\neo4j.log`

### Q: Qdrant 启动失败？

**A:** 检查：
1. 端口 6333 是否被占用
2. Qdrant 是否有执行权限（Linux: `chmod +x runtime/qdrant/qdrant`）

### Q: MemOS API 启动失败？

**A:** 检查：
1. `.env` 文件是否存在且格式正确
2. Python 依赖是否安装完整：`runtime\conda\python -m pip list`
3. Neo4j 和 Qdrant 是否已启动

### Q: Claude Code 中看不到 memos 工具？

**A:** 检查：
1. MCP 配置是否正确添加（运行 `configure_mcp.bat` 查看配置）
2. MemOS 服务是否已启动（访问 http://localhost:18000/docs）
3. 重启 Claude Code

### Q: 如何升级 MemOS？

**A:**
1. 备份 `data/` 目录
2. 下载新版本整合包
3. 将 `data/` 目录复制到新版本中
4. 运行 `install.bat` 更新依赖

### Q: 如何更换 Memory Cube？

**A:** 编辑 `data/memos_cubes/` 下的 cube 目录，或在 `.env` 中修改 `MOS_CUBE_PATH`。

---

## 目录结构 | Directory Structure

```
MemOS-Bundle/
├── scripts/bundle/           # 整合包脚本
│   ├── install.bat/.sh       # 一键安装
│   ├── start.bat/.sh         # 一键启动
│   ├── stop.bat/.sh          # 一键停止
│   ├── configure_mcp.bat/.sh # 配置 MCP
│   └── download_runtime.bat/.sh  # 下载运行时
│
├── runtime/                  # 运行时组件（自动下载）
│   ├── conda/                # Miniconda (Python 3.11)
│   ├── neo4j/                # Neo4j Community
│   ├── jre/                  # OpenJDK 17
│   └── qdrant/               # Qdrant
│
├── src/                      # MemOS 源码
├── mcp-server/               # MCP Server
├── config/                   # 配置文件
├── data/                     # 数据存储
│   ├── memos_cubes/          # Memory Cubes
│   ├── qdrant/               # Qdrant 数据
│   └── logs/                 # 日志文件
│
├── .env                      # 环境配置（从 .env.bundle.example 复制）
├── .env.bundle.example       # 配置模板
└── docs/QUICKSTART_BUNDLE.md # 本文档
```

---

## 技术支持 | Support

- GitHub Issues: https://github.com/anthropics/claude-code/issues
- 项目文档: `docs/` 目录
