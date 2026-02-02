# MemOS 向量嵌入模型配置指南

> 配置 Qdrant 向量数据库和嵌入模型的最佳实践。

## 概览

MemOS 使用向量嵌入模型将文本转换为高维向量，存储在 Qdrant 中进行语义搜索。

```
+------------------+     +------------------+     +------------------+
|   Memory Text    | --> |  Embedder Model  | --> |   Qdrant Vector  |
|   (UTF-8)        |     |  (1024 dims)     |     |   Collection     |
+------------------+     +------------------+     +------------------+
```

## 重要提示

**向量维度必须一致！**

Qdrant 集合创建后，维度不可更改。如果更换了不同维度的嵌入模型，必须删除旧集合。

| 常见问题 | 错误信息 | 解决方案 |
|----------|----------|----------|
| 维度不匹配 | `Vector dimension error: expected dim: 768, got 1024` | 删除 Qdrant 集合后重启 |
| 模型切换 | 向量空间不兼容 | 即使维度相同，也需删除旧集合 |

---

## 推荐配置

### 方案一：云端 API（推荐）

使用 SiliconFlow 等云服务托管的嵌入模型，无需本地 GPU。
# https://cloud.siliconflow.cn/i/eaey72Uc 点击前往注册硅基流动提供免费的向量模型和重排模型

**.env 配置：**

```bash
# 嵌入模型配置
EMBEDDING_DIMENSION=1024                            # 嵌入向量维度
MOS_EMBEDDER_BACKEND=universal_api                  # 后端类型
MOS_EMBEDDER_PROVIDER=openai                        # API 提供商协议
MOS_EMBEDDER_MODEL=BAAI/bge-m3                      # 模型名称
MOS_EMBEDDER_API_BASE=https://api.siliconflow.cn/v1 # API 地址
MOS_EMBEDDER_API_KEY=sk-your-api-key                # API 密钥
```

**优点：**
- 无需 GPU，资源占用低
- 稳定可靠，无需维护
- 支持高并发

**缺点：**
- 需要网络连接
- 有调用成本（通常很低） # https://cloud.siliconflow.cn/i/eaey72Uc 点击前往注册硅基流动提供免费的向量模型和重排模型

---

### 方案二：本地 Ollama

使用 Ollama 运行本地嵌入模型，完全离线。

**.env 配置：**

```bash
# 嵌入模型配置
EMBEDDING_DIMENSION=1024                            # 嵌入向量维度
MOS_EMBEDDER_BACKEND=ollama                         # 后端类型
MOS_EMBEDDER_MODEL=dengcao/bge-m3:567m              # 模型名称
MOS_EMBEDDER_API_BASE=http://localhost:11434        # Ollama 地址
```

**安装模型：**

```bash
ollama pull dengcao/bge-m3:567m
```

**优点：**
- 完全离线，隐私性强
- 无 API 调用成本

**缺点：**
- 需要 GPU 资源（约 2-3GB 显存）
- 首次加载较慢

---

## 切换嵌入模型

**重要：切换模型后必须删除 Qdrant 集合！**

不同模型产生的向量空间不兼容，即使维度相同也不能混用。

### 步骤：

1. **修改 .env 配置**

   按上述方案配置新的嵌入模型参数。

2. **删除 Qdrant 集合**

   访问 Qdrant Dashboard: http://localhost:6333/dashboard

   或使用 API：
   ```bash
   # 列出集合
   curl http://localhost:6333/collections

   # 删除集合（替换 collection_name）
   curl -X DELETE http://localhost:6333/collections/{collection_name}
   ```

3. **重启 MemOS API**

   ```bash
   # 重启后会自动创建新集合
   python -m uvicorn memos.api.server:app --port 18000
   ```

4. **重新注册 Cube**

   MCP 工具会自动重新注册，或手动：
   ```bash
   curl -X POST "http://localhost:18000/mem_cubes" \
     -H "Content-Type: application/json" \
     -d '{"user_id":"dev_user","mem_cube_name_or_path":"dev_cube"}'
   ```

---

## 常见模型维度参考

| 模型 | 维度 | 后端 | 备注 |
|------|------|------|------|
| BAAI/bge-m3 | 1024 | universal_api | 推荐，多语言 |
| dengcao/bge-m3:567m | 1024 | ollama | 本地推荐 |
| text-embedding-ada-002 | 1536 | universal_api | OpenAI |
| nomic-embed-text | 768 | ollama | 轻量级 |
| all-MiniLM-L6-v2 | 384 | sentence_transformer | 英文专用 |

---

## 配置验证

修改配置后，可通过以下方式验证：

```bash
# 检查 Qdrant 集合维度
curl http://localhost:6333/collections/{cube_name}_graph | jq '.result.config.params.vectors.size'

# 应输出与 EMBEDDING_DIMENSION 一致的值
```

---

## 故障排除

### 问题：Vector dimension error

**错误信息：**
```
Vector dimension error: expected dim: 768, got 1024
```

**原因：** Qdrant 集合创建时使用了旧模型的维度。

**解决：**
1. 删除对应的 Qdrant 集合
2. 重启 MemOS API
3. 重新注册 Cube

### 问题：Embedder API 连接失败

**检查：**
1. API 地址是否正确
2. API Key 是否有效
3. 网络是否通畅

### 问题：Ollama 模型未加载

**检查：**
```bash
# 确认模型已安装
ollama list

# 测试嵌入
curl http://localhost:11434/api/embeddings \
  -d '{"model":"dengcao/bge-m3:567m","prompt":"测试文本"}'
```

---

*更新日期：2026-02-02*
