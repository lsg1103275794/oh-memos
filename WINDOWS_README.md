# MemOS Windows 本地运行指南

## 概述

本指南帮助你在 Windows 系统上本地运行 MemOS 项目。MemOS 是一个记忆操作系统，用于 LLMs 和 AI 智能体。

## 前置要求

1. **Python 3.10+**
   - 下载地址: https://www.python.org/downloads/
   - 安装时勾选 "Add Python to PATH"

2. **Git** (可选，用于克隆仓库)
   - 下载地址: https://git-scm.com/download/win

3. **API Key**
   - 需要 OpenAI API Key 或兼容的 LLM API
   - 可选: 嵌入模型 API Key

## 快速开始

### 方法 1: 使用启动脚本 (推荐)

1. **双击运行** `install_run.bat`
   - 这将自动:
     - 检查 Python 版本
     - 创建必要目录
     - 安装依赖包
     - 复制配置文件
     - 启动服务

2. **服务启动后**
   - API 地址: http://localhost:8000
   - API 文档: http://localhost:8000/docs

### 方法 2: 手动安装

1. **克隆项目** (如果尚未克隆)
   ```bash
   git clone https://github.com/MemTensor/MemOS.git
   cd MemOS
   ```

2. **创建虚拟环境** (推荐)
   ```bash
   python -m venv memos-venv
   memos-venv\Scripts\activate
   ```

3. **安装依赖**
   ```bash
   pip install -r docker/requirements.txt
   ```

4. **创建配置文件**
   ```bash
   copy .env.windows.example .env
   ```
   然后编辑 `.env` 文件，设置你的 API Key。

5. **启动服务**
   ```bash
   cd src
   python -m uvicorn memos.api.start_api:app --host 0.0.0.0 --port 8000 --reload
   ```

## 配置说明

编辑 `.env` 文件配置以下选项:

### 必填配置

```env
# LLM 配置
OPENAI_API_KEY=sk-your-api-key
OPENAI_API_BASE=https://api.openai.com/v1
MOS_CHAT_MODEL=gpt-4o-mini
MOS_CHAT_MODEL_PROVIDER=openai
```

### 可选配置

```env
# 嵌入模型 (默认使用 cosine_local)
MOS_EMBEDDER_BACKEND=cosine_local

# Neo4j (可选，需要图数据库)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=12345678

# Qdrant (可选，需要向量数据库)
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## 启动服务

### 开发模式 (自动重载)
```bash
cd src
python -m uvicorn memos.api.start_api:app --host 0.0.0.0 --port 8000 --reload
```

### 生产模式
```bash
cd src
python -m uvicorn memos.api.start_api:app --host 0.0.0.0 --port 8000 --workers 1
```

## 测试 API

### 使用 curl 测试

```bash
# 创建记忆
curl -X POST "http://localhost:8000/memories" ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\": \"test_user\", \"messages\": [{\"role\": \"user\", \"content\": \"I like pizza\"}]}"

# 搜索记忆
curl -X POST "http://localhost:8000/search" ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"What do I like?\", \"user_id\": \"test_user\"}"
```

### 使用 Python 客户端

```python
import requests
import json

# 添加记忆
data = {
    "user_id": "test_user",
    "messages": [{"role": "user", "content": "I like pizza"}]
}
response = requests.post("http://localhost:8000/memories", json=data)
print(response.json())

# 搜索记忆
data = {
    "query": "What do I like?",
    "user_id": "test_user"
}
response = requests.post("http://localhost:8000/search", json=data)
print(response.json())
```

## 目录结构

运行时会自动创建以下目录:

```
MemOS/
├── data/               # MemCube 数据存储
│   └── memos_cubes/    # 用户记忆立方体
├── logs/               # 日志文件
├── .memos/             # 应用缓存目录
├── src/                # 源代码
└── .env                # 环境配置
```

## 常见问题

### 1. 依赖安装失败

如果 `pip install` 失败，尝试:
```bash
pip install --upgrade pip
pip install --upgrade setuptools wheel
```

### 2. 端口被占用

修改端口:
```bash
python -m uvicorn memos.api.start_api:app --port 8001
```

### 3. Python 未找到

确保 Python 已添加到系统 PATH:
```bash
python --version
```

### 4. 模块导入错误

确保在项目根目录运行:
```bash
cd MemOS
PYTHONPATH=src python -m uvicorn memos.api.start_api:app
```

## 可选组件

### Neo4j 图数据库 (用于树形记忆)

1. 下载 Neo4j Desktop: https://neo4j.com/download/
2. 创建新数据库，设置密码
3. 更新 `.env`:
   ```env
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   ```

### Qdrant 向量数据库

1. 下载 Qdrant: https://github.com/qdrant/qdrant/releases
2. 或使用 Docker:
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```
3. 更新 `.env`:
   ```env
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   ```

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/docs` | GET | OpenAPI 文档 |
| `/memories` | POST | 添加记忆 |
| `/search` | POST | 搜索记忆 |
| `/chat` | POST | 聊天 |
| `/users` | GET/POST | 用户管理 |

## 停止服务

按 `Ctrl + C` 停止服务。

## 相关链接

- [MemOS 文档](https://memos-docs.openmem.net/)
- [GitHub 仓库](https://github.com/MemTensor/MemOS)
- [API 文档](http://localhost:8000/docs)
