# MemOS Windows 部署指南

基于便携式 Python 环境的 MemOS 快速部署方案。

## 快速开始

### 一键启动

```cmd
双击运行 run.bat
```

服务地址：
- API: http://localhost:18000
- 文档: http://localhost:18000/docs

### 首次安装

```cmd
双击运行 install_run.bat
```

自动完成：创建目录 → 安装依赖 → 复制配置 → 启动服务

## 环境要求

- Windows 10/11
- 便携式 Python 环境 (`conda_venv/`)
- 或系统 Python 3.10+

## 配置文件

编辑项目根目录 `.env` 文件：

### LLM 配置（必填）

```env
# OpenAI 兼容 API
OPENAI_API_KEY=sk-your-api-key
OPENAI_API_BASE=https://api.openai.com/v1
MOS_CHAT_MODEL=gpt-4o-mini
```

### 嵌入模型（推荐 Ollama 本地）

```env
MOS_EMBEDDER_BACKEND=ollama
MOS_EMBEDDER_MODEL=nomic-embed-text
OLLAMA_API_BASE=http://localhost:11434
EMBEDDING_DIMENSION=768
```

### 向量数据库（可选）

```env
# Qdrant 云服务
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-api-key

# 或本地 Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### 图数据库（可选）

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

## 目录结构

```
MemOS/
├── run.bat                 # 启动脚本
├── install_run.bat         # 安装+启动脚本
├── conda_venv/             # 便携式 Python 环境
├── .env                    # 环境配置（需自行创建）
├── .env.windows.example    # 配置模板
├── src/                    # 源代码
│   ├── .env                # 运行时配置（自动同步）
│   └── memos/
└── data/
    └── memos_cubes/        # 记忆数据（⚠️ 已 gitignore）
```

## API 测试

### 聊天测试

```bash
curl -X POST http://localhost:18000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "query": "你好"}'
```

### 添加记忆

```bash
curl -X POST http://localhost:18000/memories \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "memory_content": "记忆内容"}'
```

### 搜索记忆

```bash
curl -X POST http://localhost:18000/search \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "query": "搜索关键词"}'
```

## 常见问题

### Python 未找到

确保 `conda_venv/` 目录存在，或将系统 Python 添加到 PATH。

### 端口被占用

修改 `run.bat` 中的端口号（默认 18000）。

### .env 配置不生效

脚本会自动将 `.env` 复制到 `src/` 目录，确保根目录 `.env` 文件存在。

### 依赖安装失败

```cmd
conda_venv\python.exe -m pip install -r docker/requirements.txt -i https://pypi.org/simple
```

## 可选服务

### Ollama（本地嵌入模型）

```bash
# 安装后拉取模型
ollama pull nomic-embed-text
```

### Neo4j（图数据库）

```cmd
# 社区版启动
D:\path\to\neo4j-community\bin\neo4j console
```

### Redis（任务队列）

```cmd
# 启动 Redis
redis-server
```

启用队列：在 `.env` 中设置 `MEMSCHEDULER_USE_REDIS_QUEUE=true`

## 停止服务

按 `Ctrl + C` 停止服务。
