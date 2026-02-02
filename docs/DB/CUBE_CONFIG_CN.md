# MemOS Cube 配置指南

> 记忆立方体 (MemCube) 的 config.json 配置说明与示例。

## 配置优先级

```
命令行参数  >  环境变量 (.env)  >  config.json 默认值
```

`.env` 中的值会在运行时覆盖 `config.json` 中的对应字段。因此 config.json 只需填写基础结构，敏感信息（API Key 等）放在 `.env` 中。

---

## 文件位置

```
data/memos_cubes/
  └── {cube_id}/
      ├── config.json              # 核心配置（必需）
      └── textual_memory.json      # 记忆数据（自动生成）
```

---

## config.json 完整示例

以下示例使用推荐的 `tree_text`（知识图谱）模式，包含所有必要字段。

**注意：** `placeholder` 表示的值会被 `.env` 覆盖，无需在 config.json 中填写真实值。

```json
{
  "model_schema": "memos.configs.mem_cube.GeneralMemCubeConfig",
  "user_id": "dev_user",
  "cube_id": "my_project_cube",
  "config_filename": "config.json",
  "text_mem": {
    "backend": "tree_text",
    "config": {
      "cube_id": "my_project_cube",
      "memory_filename": "textual_memory.json",
      "reorganize": true,
      "extractor_llm": {
        "backend": "openai",
        "config": {
          "model_name_or_path": "gpt-4o-mini",
          "temperature": 0.6,
          "max_tokens": 6000,
          "api_key": "placeholder",
          "api_base": "https://api.openai.com/v1"
        }
      },
      "dispatcher_llm": {
        "backend": "openai",
        "config": {
          "model_name_or_path": "gpt-4o-mini",
          "temperature": 0.6,
          "max_tokens": 6000,
          "api_key": "placeholder",
          "api_base": "https://api.openai.com/v1"
        }
      },
      "embedder": {
        "backend": "universal_api",
        "config": {
          "model_name_or_path": "BAAI/bge-m3",
          "provider": "openai",
          "base_url": "https://api.openai.com/v1",
          "api_key": "placeholder",
          "embedding_dims": 1024
        }
      },
      "reranker": {
        "backend": "http_bge",
        "config": {
          "url": "https://api.siliconflow.cn/v1/rerank",
          "model": "netease-youdao/bce-reranker-base_v1",
          "headers_extra": "{}"
        }
      },
      "graph_db": {
        "backend": "neo4j-community",
        "config": {
          "uri": "bolt://localhost:7687",
          "user": "neo4j",
          "password": "placeholder",
          "db_name": "neo4j",
          "use_multi_db": false,
          "user_name": "dev_user",
          "embedding_dimension": 1024,
          "vec_config": {
            "backend": "qdrant",
            "config": {
              "collection_name": "my_project_cube_graph",
              "vector_dimension": 1024,
              "distance_metric": "cosine",
              "host": "localhost",
              "port": 6333
            }
          }
        }
      },
      "search_strategy": {
        "bm25": true,
        "cot": false
      }
    }
  },
  "act_mem": {},
  "para_mem": {}
}
```

---

## .env 覆盖规则

以下 `.env` 变量会在运行时自动覆盖 config.json 中的对应字段：

### LLM 配置（extractor_llm / dispatcher_llm）

| .env 变量 | 覆盖 config.json 字段 |
|------------|----------------------|
| `MOS_CHAT_MODEL_PROVIDER` | `extractor_llm.backend` / `dispatcher_llm.backend` |
| `MOS_CHAT_MODEL` | `config.model_name_or_path` |
| `OPENAI_API_KEY` | `config.api_key` |
| `OPENAI_API_BASE` | `config.api_base` |
| `MOS_CHAT_TEMPERATURE` | `config.temperature` |
| `MOS_MAX_TOKENS` | `config.max_tokens` |

### Embedder 配置

| .env 变量 | 覆盖 config.json 字段 |
|------------|----------------------|
| `MOS_EMBEDDER_BACKEND` | `embedder.backend` |
| `MOS_EMBEDDER_MODEL` | `config.model_name_or_path` |
| `MOS_EMBEDDER_PROVIDER` | `config.provider` |
| `MOS_EMBEDDER_API_BASE` | `config.base_url` |
| `MOS_EMBEDDER_API_KEY` | `config.api_key` |
| `EMBEDDING_DIMENSION` | `config.embedding_dims` |

### Neo4j 配置

| .env 变量 | 覆盖 config.json 字段 |
|------------|----------------------|
| `NEO4J_BACKEND` | `graph_db.backend` |
| `NEO4J_URI` | `config.uri` |
| `NEO4J_USER` | `config.user` |
| `NEO4J_PASSWORD` | `config.password` |
| `NEO4J_DB_NAME` | `config.db_name` |

### Reranker 配置

| .env 变量 | 覆盖 config.json 字段 |
|------------|----------------------|
| `MOS_RERANKER_BACKEND` | `reranker.backend` |
| `MOS_RERANKER_URL` | `config.url` |
| `MOS_RERANKER_MODEL` | `config.model` |
| `MOS_RERANKER_API_KEY` | `config.api_key` |

---

## 新建 Cube 快速步骤

1. **创建目录：**
   ```bash
   mkdir -p data/memos_cubes/my_project_cube
   ```

2. **复制示例 config.json** 并修改：
   - `cube_id` → 你的项目名
   - `user_name` → 你的用户名
   - `collection_name` → `{cube_id}_graph`

3. **配置 .env** 填写真实的 API Key 等敏感信息

4. **启动服务后注册 Cube：**
   ```bash
   curl -X POST "http://localhost:18000/mem_cubes" \
     -H "Content-Type: application/json" \
     -d '{"user_id":"dev_user","mem_cube_name_or_path":"my_project_cube"}'
   ```

---

## 记忆模式选择

| 模式 | backend | 需要 Neo4j | 需要 Qdrant | 特点 |
|------|---------|-----------|-------------|------|
| 扁平记忆 | `general_text` | 否 | 是 | 纯向量搜索，简单轻量 |
| 知识图谱 | `tree_text` | 是 | 是 | 支持关系推理，功能完整 |

通过 `.env` 中的 `MOS_TEXT_MEM_TYPE` 控制：

```bash
# 扁平记忆（不需要 Neo4j）
MOS_TEXT_MEM_TYPE=general_text

# 知识图谱记忆（推荐，需要 Neo4j）
MOS_TEXT_MEM_TYPE=tree_text
```

---

*更新日期：2026-02-02*
