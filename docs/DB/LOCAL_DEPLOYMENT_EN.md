# MemOS Local Database Deployment Guide

> Complete offline deployment without Docker or cloud services.

## Overview

MemOS requires the following database services:

| Service | Purpose | Required | Default Port | Dependency |
|---------|---------|----------|--------------|------------|
| **Qdrant** | Vector search | [Required] | 6333, 6334 | None |
| **Neo4j** | Knowledge graph | [tree_text mode] | 7474, 7687 | Java 17+ |
| **Redis** | Task queue | [Optional] | 6379 | None |

## Quick Start

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

## 1. Qdrant (Vector Database)

### Download

1. Go to [Qdrant Releases](https://github.com/qdrant/qdrant/releases)
2. Download the Windows binary: `qdrant-x86_64-pc-windows-msvc.zip`
3. Extract to your preferred location (e.g., `D:\User\Qdrant\`)

### Directory Structure

```
D:\User\Qdrant\
├── qdrant.exe           # Main executable
├── config/
│   └── config.yaml      # Configuration (optional)
├── storage/             # Data storage (auto-created)
└── snapshots/           # Backups (auto-created)
```

### Configuration (Optional)

Create `config/config.yaml` for custom settings:

```yaml
# Qdrant Configuration
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

### Start Qdrant

**Manual:**
```cmd
cd D:\User\Qdrant
qdrant.exe
```

**As Background Service:**
```cmd
start "Qdrant" /min D:\User\Qdrant\qdrant.exe
```

### Verify

- Dashboard: http://localhost:6333/dashboard
- Health check: http://localhost:6333/health

```bash
curl http://localhost:6333/collections
```

---

## 2. Neo4j (Knowledge Graph)

> Required only for `tree_text` memory mode (knowledge graph features).

### Prerequisites: Java Runtime

Neo4j requires Java 17+ runtime environment:

1. Download [Oracle JDK](https://www.oracle.com/java/technologies/downloads/) or [OpenJDK](https://adoptium.net/)
2. Extract to your preferred location (e.g., `D:\User\jdk-24\`)
3. Set environment variables:
   ```cmd
   :: Temporary (current session)
   set JAVA_HOME=D:\User\jdk-24
   set PATH=%JAVA_HOME%\bin;%PATH%

   :: Or permanent (system environment variables)
   :: Right-click "This PC" -> Properties -> Advanced -> Environment Variables
   :: New: JAVA_HOME = D:\User\jdk-24
   :: Edit PATH, add %JAVA_HOME%\bin
   ```
4. Verify installation:
   ```cmd
   java -version
   :: Should show: java version "24" or similar
   ```

### Download

1. Go to [Neo4j Download Center](https://neo4j.com/download-center/)
2. Download **Neo4j Community Edition** (free)
3. Extract to your preferred location (e.g., `D:\User\neo4j-community-5.15.0\`)

### Directory Structure

```
D:\User\neo4j-community-5.15.0\
├── bin/
│   ├── neo4j.bat           # Main command
│   └── start-Neo4j.bat     # Windows service starter
├── conf/
│   └── neo4j.conf          # Configuration
├── data/                   # Database files
└── logs/                   # Log files
```

### Initial Setup

1. **Set Password** (first run):
   ```cmd
   cd D:\User\neo4j-community-5.15.0\bin
   neo4j-admin.bat dbms set-initial-password 12345678
   ```

2. **Configure** `conf/neo4j.conf`:
   ```properties
   # Listen on all interfaces
   server.default_listen_address=0.0.0.0

   # Bolt connector (application connections)
   server.bolt.enabled=true
   server.bolt.listen_address=:7687

   # HTTP connector (browser)
   server.http.enabled=true
   server.http.listen_address=:7474
   ```

### Start Neo4j

**Console Mode (recommended for development):**
```cmd
cd D:\User\neo4j-community-5.15.0\bin
neo4j console
```

**Windows Service:**
```cmd
cd D:\User\neo4j-community-5.15.0\bin
neo4j windows-service install
neo4j start
```

### Verify

- Browser UI: http://localhost:7474
- Default credentials: `neo4j` / `12345678`

```bash
curl http://localhost:7474
```

---

## 3. Redis (Optional)

> Only needed if `MEMSCHEDULER_USE_REDIS_QUEUE=true`

### Download

1. Go to [Redis Windows Releases](https://github.com/redis-windows/redis-windows/releases)
2. Download the latest `.zip` file
3. Extract to your preferred location

### Start Redis

```cmd
redis-server.exe
```

### Verify

```cmd
redis-cli ping
# Should return: PONG
```

---

## MemOS Configuration

### .env Settings

```env
# ========== Qdrant (Local) ==========
QDRANT_HOST=localhost
QDRANT_PORT=6333
# Comment out cloud settings:
# QDRANT_URL=https://xxx.cloud.qdrant.io
# QDRANT_API_KEY=xxx

# ========== Neo4j ==========
NEO4J_BACKEND=neo4j-community
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=12345678
NEO4J_DB_NAME=neo4j

# ========== Memory Mode ==========
# tree_text = Knowledge Graph (requires Neo4j)
# general_text = Flat memory (vector only)
MOS_TEXT_MEM_TYPE=tree_text
MOS_ENABLE_REORGANIZE=true

# ========== Redis (disabled) ==========
MEMSCHEDULER_USE_REDIS_QUEUE=false
```

### Memory Cube Configuration

Update `data/memos_cubes/{cube_id}/config.json`:

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

## Startup Script

### start_db.bat

```batch
@echo off
setlocal

echo [MemOS] Starting local database services...
echo.

:: 1. Start Neo4j
echo [MemOS] Starting Neo4j...
set NEO4J_BIN=D:\User\neo4j-community-5.15.0\bin
if exist "%NEO4J_BIN%\start-Neo4j.bat" (
    cd /d "%NEO4J_BIN%"
    start "Neo4j Service" /min cmd /c "start-Neo4j.bat"
    echo [+] Neo4j started
)

echo.

:: 2. Start Qdrant
echo [MemOS] Starting Qdrant...
set QDRANT_PATH=D:\User\Qdrant\qdrant.exe
if exist "%QDRANT_PATH%" (
    cd /d "D:\User\Qdrant"
    start "Qdrant Service" /min "%QDRANT_PATH%"
    echo [+] Qdrant started at http://localhost:6333
)

echo.
echo ========================================
echo [MemOS] Database Services Ready
echo ========================================
echo - Neo4j:  http://localhost:7474
echo - Qdrant: http://localhost:6333/dashboard
echo ========================================
pause
```

---

## Troubleshooting

### Qdrant Issues

| Problem | Solution |
|---------|----------|
| Port 6333 in use | Check with `netstat -ano \| findstr 6333`, kill process |
| Config error crash | Remove `config/config.yaml` to use defaults |
| Storage permission | Run as Administrator or change storage path |

### Neo4j Issues

| Problem | Solution |
|---------|----------|
| Authentication failed | Reset password: `neo4j-admin dbms set-initial-password` |
| Port 7687 in use | Check other Neo4j instances |
| Java not found | Install JDK 17+ and set JAVA_HOME |

### Connection Test

```bash
# Test Qdrant
curl http://localhost:6333/health

# Test Neo4j
curl http://localhost:7474

# Test MemOS API
curl http://localhost:18000/health
```

---

## Architecture Diagram

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

## References

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [MemOS GitHub](https://github.com/lsg1103275794/oh-memos)

---

<div align="center">

**MemOS Local Deployment Guide** | Privacy-First AI Memory System

</div>
