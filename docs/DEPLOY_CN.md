# MemOS Windows 便携部署指南

本文档详细说明如何在 Windows 上部署 MemOS 记忆服务。

---

## 目录

- [环境要求](#环境要求)
- [快速部署](#快速部署)
- [数据库配置](#数据库配置)
  - [Qdrant Cloud（推荐）](#qdrant-cloud推荐)
  - [本地 Qdrant](#本地-qdrant)
- [嵌入模型配置](#嵌入模型配置)
- [LLM API 配置](#llm-api-配置)
- [完整配置示例](#完整配置示例)
- [常见问题](#常见问题)

---

## 环境要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 操作系统 | Windows 10 | Windows 10/11 |
| 内存 | 4GB | 8GB+ |
| 磁盘空间 | 2GB | 5GB+ |
| Python | 3.10+ | 3.11+ (由脚本自动安装) |

---

## 快速部署

### 第一步：安装 Python 环境

```cmd
双击 setup_env.bat
```

脚本会自动：
1. 下载 Miniconda（约 80MB）
2. 安装到 `项目目录\conda_venv\`
3. 显示完整安装路径

安装完成后会看到：
```
========================================
   Setup Complete! 安装完成!
========================================

   Python executable / Python可执行文件:
   G:\test\MemOS\conda_venv\python.exe

   Pip executable / Pip可执行文件:
   G:\test\MemOS\conda_venv\Scripts\pip.exe

   Environment directory / 环境目录:
   G:\test\MemOS\conda_venv
```

### 第二步：安装依赖并启动

```cmd
双击 install_run.bat
```

首次运行会安装所有依赖包，之后可以用 `run.bat` 快速启动。

### 第三步：验证部署

访问 http://localhost:18000/docs 查看 API 文档。

---

## 数据库配置

MemOS 使用 Qdrant 作为向量数据库存储记忆。有两种部署方式：

### Qdrant Cloud（推荐）

**优点**：
- 免费额度充足（1GB 存储）
- 无需本地资源
- 数据持久化，重启不丢失
- 支持多设备访问

**配置步骤**：

1. **注册 Qdrant Cloud 账号**

   访问 https://cloud.qdrant.io/ 注册（支持 GitHub/Google 登录）

2. **创建免费集群**

   - 点击 "Create Cluster"
   - 选择 "Free" 套餐
   - 选择离你最近的区域（如 `aws-us-east-1`）
   - 记录集群 URL，格式如：`https://xxx-xxx.aws.qdrant.io:6333`

3. **获取 API Key**

   - 进入集群详情页
   - 点击 "API Keys" → "Create API Key"
   - 复制生成的 Key

4. **配置 .env 文件**

   ```env
   # Qdrant Cloud 配置
   QDRANT_MODE=cloud
   QDRANT_URL=https://your-cluster-url.aws.qdrant.io:6333
   QDRANT_API_KEY=your-api-key-here
   ```

### 本地 Qdrant

**优点**：
- 完全离线运行
- 数据本地存储

**配置步骤**：

1. **使用 Docker 启动**

   ```bash
   docker run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant
   ```

2. **配置 .env 文件**

   ```env
   # 本地 Qdrant 配置
   QDRANT_MODE=local
   QDRANT_URL=http://localhost:6333
   # 本地模式不需要 API Key
   ```

---

## 嵌入模型配置

MemOS 需要嵌入模型将文本转换为向量。推荐使用 Ollama 本地模型。

### 安装 Ollama

1. 下载安装 Ollama：https://ollama.ai/download

2. 拉取嵌入模型：
   ```bash
   ollama pull nomic-embed-text
   ```

3. 配置 .env：
   ```env
   # Ollama 嵌入模型配置
   EMBEDDING_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_EMBEDDING_MODEL=nomic-embed-text
   ```

### 其他嵌入模型选项

| 模型 | 配置 | 说明 |
|------|------|------|
| nomic-embed-text | `OLLAMA_EMBEDDING_MODEL=nomic-embed-text` | 推荐，平衡性能 |
| nomic-embed-text-v2-moe | `OLLAMA_EMBEDDING_MODEL=nomic-embed-text-v2-moe` | 更新版本 |
| OpenAI | `EMBEDDING_PROVIDER=openai` | 需要 API Key |

---

## LLM API 配置

MemOS 的上下文增强功能需要 LLM API。支持 OpenAI 兼容格式。

### 使用 OpenAI

```env
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### 使用其他兼容 API

```env
# 例如使用 DeepSeek
OPENAI_API_KEY=your-deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# 或使用本地 Ollama
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3
```

---

## 完整配置示例

`.env` 文件完整示例：

```env
# ========================================
# MemOS Configuration
# ========================================

# --- Server ---
HOST=0.0.0.0
PORT=18000

# --- Qdrant Vector Database ---
# 使用 Qdrant Cloud (推荐)
QDRANT_MODE=cloud
QDRANT_URL=https://your-cluster.aws.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key

# --- Embedding Model ---
# 使用 Ollama 本地嵌入
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# --- LLM API (OpenAI Compatible) ---
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# --- Memory Storage ---
MEMOS_CUBES_DIR=./data/memos_cubes

# --- User ---
DEFAULT_USER=dev_user
```

---

## 常见问题

### Q: 启动时提示 "Python not found"

**A**: 先运行 `setup_env.bat` 安装 Python 环境。

### Q: Qdrant 连接失败

**A**: 检查以下项目：
1. 确认 `.env` 中的 `QDRANT_URL` 格式正确
2. 确认 `QDRANT_API_KEY` 没有多余空格
3. 如果使用 Cloud，确认集群状态为 "Running"

### Q: 嵌入模型报错

**A**: 确认 Ollama 正在运行：
```bash
ollama list  # 查看已安装模型
ollama serve  # 如果服务未启动
```

### Q: 端口 18000 被占用

**A**: 修改 `.env` 中的 `PORT` 为其他端口，或关闭占用端口的程序。

### Q: 记忆数据存储在哪里？

**A**:
- 向量数据：存储在 Qdrant（Cloud 或本地）
- 元数据：存储在 `./data/memos_cubes/` 目录

---

## 服务管理

### 启动服务
```cmd
run.bat
```

### 查看 API 文档
```
http://localhost:18000/docs
```

### 测试 API
```bash
# 保存记忆
curl -X POST http://localhost:18000/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "测试记忆", "user_id": "dev_user"}'

# 搜索记忆
curl -X POST http://localhost:18000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "测试", "user_id": "dev_user"}'
```

---

## 相关链接

- [MemOS 官方仓库](https://github.com/MemTensor/MemOS)
- [Qdrant Cloud](https://cloud.qdrant.io/)
- [Ollama](https://ollama.ai/)
