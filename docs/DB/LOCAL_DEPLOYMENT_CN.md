# MemOS 本地数据库部署指南

> 完全离线部署，无需 Docker 或云服务。

## 概览

MemOS 需要以下数据库服务：

| 服务 | 用途 | 是否必需 | 默认端口 | 依赖 |
|------|------|----------|----------|------|
| **Qdrant** | 向量搜索 | [必需] | 6333, 6334 | 无 |
| **Neo4j** | 知识图谱 | [tree_text 模式] | 7474, 7687 | Java 17+ |
| **Redis** | 任务队列 | [可选] | 6379 | 无 |

## 快速启动

```
+-------------------------------------------------------------+
|                    One-Click Startup                        |
|                                                             |
|   Windows:  Double-click  start_db.bat                      |
|                                                             |
|   Services started:                                         |
|   - Neo4j   -> http://localhost:7474                        |
|   - Qdrant  -> http://localhost:6333/dashboard              |
+-------------------------------------------------------------+
```

---

## 1. Qdrant (向量数据库)

### 下载安装

1. 访问 [Qdrant Releases](https://github.com/qdrant/qdrant/releases)
2. 下载 Windows 版本: `qdrant-x86_64-pc-windows-msvc.zip`
3. 解压到你喜欢的位置 (如 `D:\User\Qdrant\`)

### 目录结构

```
D:\User\Qdrant\
├── qdrant.exe           # 主程序
├── config/
│   └── config.yaml      # 配置文件 (可选)
├── storage/             # 数据存储 (自动创建)
└── snapshots/           # 备份快照 (自动创建)
```

### 配置文件 (可选)

创建 `config/config.yaml` 自定义配置：

```yaml
# Qdrant 配置
storage:
  storage_path: ./storage
  snapshots_path: ./snapshots

service:
  host: 0.0.0.0
  http_port: 6333
  grpc_port: 6334
  enable_cors: true

cluster:
  enabled: false

telemetry_disabled: true
```

### 启动 Qdrant

**手动启动:**
```cmd
cd D:\User\Qdrant
qdrant.exe
```

**后台服务:**
```cmd
start "Qdrant" /min D:\User\Qdrant\qdrant.exe
```

### 验证

- 控制台: http://localhost:6333/dashboard
- 健康检查: http://localhost:6333/health

```bash
curl http://localhost:6333/collections
```

---

## 2. Neo4j (知识图谱数据库)

> 仅在使用 `tree_text` 记忆模式时需要（知识图谱功能）。

### 前置条件：Java 运行时

Neo4j 需要 Java 17+ 运行时环境：

1. 下载 [Oracle JDK](https://www.oracle.com/java/technologies/downloads/) 或 [OpenJDK](https://adoptium.net/)
2. 解压到你喜欢的位置 (如 `D:\User\jdk-24\`)
3. 设置环境变量：
   ```cmd
   :: 临时设置 (当前会话)
   set JAVA_HOME=D:\User\jdk-24
   set PATH=%JAVA_HOME%\bin;%PATH%

   :: 或永久设置 (系统环境变量)
   :: 右键"此电脑" -> 属性 -> 高级系统设置 -> 环境变量
   :: 新建 JAVA_HOME = D:\User\jdk-24
   :: 编辑 PATH，添加 %JAVA_HOME%\bin
   ```
4. 验证安装：
   ```cmd
   java -version
   :: 应显示: java version "24" 或类似
   ```

### 下载安装

1. 访问 [Neo4j 下载中心](https://neo4j.com/download-center/)
2. 下载 **Neo4j Community Edition** (免费版)
3. 解压到你喜欢的位置 (如 `D:\User\neo4j-community-5.15.0\`)

### 目录结构

```
D:\User\neo4j-community-5.15.0\
├── bin/
│   ├── neo4j.bat           # 主命令
│   └── start-Neo4j.bat     # Windows 服务启动器
├── conf/
│   └── neo4j.conf          # 配置文件
├── data/                   # 数据库文件
└── logs/                   # 日志文件
```

### 初始设置

1. **设置密码** (首次运行):
   ```cmd
   cd D:\User\neo4j-community-5.15.0\bin
   neo4j-admin.bat dbms set-initial-password 12345678
   ```

2. **配置** `conf/neo4j.conf`:
   ```properties
   # 监听所有网络接口
   server.default_listen_address=0.0.0.0

   # Bolt 连接器 (应用程序连接)
   server.bolt.enabled=true
   server.bolt.listen_address=:7687

   # HTTP 连接器 (浏览器)
   server.http.enabled=true
   server.http.listen_address=:7474
   ```

### 启动 Neo4j

**控制台模式 (推荐开发使用):**
```cmd
cd D:\User\neo4j-community-5.15.0\bin
neo4j console
```

**Windows 服务:**
```cmd
cd D:\User\neo4j-community-5.15.0\bin
neo4j windows-service install
neo4j start
```

### 验证

- 浏览器界面: http://localhost:7474
- 默认账号: `neo4j` / `12345678`

```bash
curl http://localhost:7474
```

---

## 3. Redis (可选)

> 仅在 `MEMSCHEDULER_USE_REDIS_QUEUE=true` 时需要

### 下载安装

1. 访问 [Redis Windows Releases](https://github.com/redis-windows/redis-windows/releases)
2. 下载最新的 `.zip` 文件
3. 解压到你喜欢的位置

### 启动 Redis

```cmd
redis-server.exe
```

### 验证

```cmd
redis-cli ping
# 应返回: PONG
```

---

## MemOS 配置

### .env 环境变量

```env
# ========== Qdrant (本地) ==========
QDRANT_HOST=localhost
QDRANT_PORT=6333
# 注释掉云端配置:
# QDRANT_URL=https://xxx.cloud.qdrant.io
# QDRANT_API_KEY=xxx

# ========== Neo4j ==========
NEO4J_BACKEND=neo4j-community
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=12345678
NEO4J_DB_NAME=neo4j

# ========== 记忆模式 ==========
# tree_text = 知识图谱模式 (需要 Neo4j)
# general_text = 扁平记忆 (仅向量搜索)
MOS_TEXT_MEM_TYPE=tree_text
MOS_ENABLE_REORGANIZE=true

# ========== Redis (已禁用) ==========
MEMSCHEDULER_USE_REDIS_QUEUE=false
```

### 记忆立方体配置

更新 `data/memos_cubes/{cube_id}/config.json`:

```json
{
  "graph_db": {
    "backend": "neo4j-community",
    "config": {
      "uri": "bolt://localhost:7687",
      "user": "neo4j",
      "password": "12345678",
      "vec_config": {
        "backend": "qdrant",
        "config": {
          "collection_name": "your_cube_graph",
          "vector_dimension": 768,
          "host": "localhost",
          "port": 6333
        }
      }
    }
  }
}
```

---

## 启动脚本

### start_db.bat

```batch
@echo off
setlocal

echo [MemOS] 正在启动本地数据库服务...
echo.

:: 1. 启动 Neo4j
echo [MemOS] 启动 Neo4j...
set NEO4J_BIN=D:\User\neo4j-community-5.15.0\bin
if exist "%NEO4J_BIN%\start-Neo4j.bat" (
    cd /d "%NEO4J_BIN%"
    start "Neo4j Service" /min cmd /c "start-Neo4j.bat"
    echo [+] Neo4j 已启动
)

echo.

:: 2. 启动 Qdrant
echo [MemOS] 启动 Qdrant...
set QDRANT_PATH=D:\User\Qdrant\qdrant.exe
if exist "%QDRANT_PATH%" (
    cd /d "D:\User\Qdrant"
    start "Qdrant Service" /min "%QDRANT_PATH%"
    echo [+] Qdrant 已启动: http://localhost:6333
)

echo.
echo ========================================
echo [MemOS] 数据库服务就绪
echo ========================================
echo - Neo4j:  http://localhost:7474
echo - Qdrant: http://localhost:6333/dashboard
echo ========================================
pause
```

---

## 故障排除

### Qdrant 问题

| 问题 | 解决方案 |
|------|----------|
| 端口 6333 被占用 | 用 `netstat -ano \| findstr 6333` 检查，结束进程 |
| 配置错误导致崩溃 | 删除 `config/config.yaml` 使用默认配置 |
| 存储权限问题 | 以管理员身份运行或更改存储路径 |

### Neo4j 问题

| 问题 | 解决方案 |
|------|----------|
| 认证失败 | 重置密码: `neo4j-admin dbms set-initial-password` |
| 端口 7687 被占用 | 检查是否有其他 Neo4j 实例 |
| 找不到 Java | 安装 JDK 17+ 并设置 JAVA_HOME |

### 连接测试

```bash
# 测试 Qdrant
curl http://localhost:6333/health

# 测试 Neo4j
curl http://localhost:7474

# 测试 MemOS API
curl http://localhost:18000/health
```

---

## 架构图

```
+---------------------------------------------------------------+
|                        MemOS Stack                            |
+---------------------------------------------------------------+
|                                                               |
|   +-----------+     +-----------+     +-----------+           |
|   |  Ollama   |     |  MemOS    |     |  Claude   |           |
|   | (Embedder)|---->|   API     |<----|   Code    |           |
|   | :11434    |     | :18000    |     |   (MCP)   |           |
|   +-----------+     +-----+-----+     +-----------+           |
|                           |                                   |
|            +--------------+---------------+                   |
|            v              v               v                   |
|   +-----------+     +-----------+     +-----------+           |
|   |  Qdrant   |     |  Neo4j    |     |  Redis    |           |
|   | (Vectors) |     | (Graph)   |     | (Queue)   |           |
|   | :6333     |     | :7687     |     | :6379     |           |
|   | [Required]|     |[tree_text]|     | [Optional]|           |
|   +-----------+     +-----------+     +-----------+           |
|                                                               |
+---------------------------------------------------------------+
```

---

## 数据备份

### Qdrant 快照

```bash
# 创建快照
curl -X POST http://localhost:6333/collections/dev_cube_graph/snapshots

# 列出快照
curl http://localhost:6333/collections/dev_cube_graph/snapshots
```

### Neo4j 备份

```cmd
cd D:\User\neo4j-community-5.15.0\bin
neo4j-admin database dump neo4j --to-path=D:\backup\neo4j
```

---

## 相关链接

- [Qdrant 文档](https://qdrant.tech/documentation/)
- [Neo4j 文档](https://neo4j.com/docs/)
- [MemOS GitHub](https://github.com/lsg1103275794/MemOSLocal-SM)

---

<div align="center">

**MemOS 本地部署指南** | 隐私优先的 AI 记忆系统

</div>
