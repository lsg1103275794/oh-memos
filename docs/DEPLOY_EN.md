# MemOS Windows Portable Deployment Guide

A Windows portable deployment solution for MemOS with local Python environment + Ollama embeddings + Qdrant cloud.

## Features

- Portable Python environment, no system installation required
- Local embedding model via Ollama to reduce API costs
- OpenAI-compatible API support
- One-click startup scripts

## Quick Start

### One-Click Start

```cmd
Double-click run.bat
```

### First-Time Installation

```cmd
Double-click install_run.bat
```

### Service URL

- API: http://localhost:18000
- Docs: http://localhost:18000/docs

## Configuration

### Directory Structure

```
MemOS/
├── run.bat                 # Startup script
├── install_run.bat         # Install + start
├── conda_venv/             # Portable Python (prepare yourself)
│   ├── python.exe
│   └── Scripts/
├── .env                    # Configuration file
├── src/
│   └── memos/
└── data/
    └── memos_cubes/        # Memory data
```

### .env Configuration Example

```env
# ========== LLM Configuration ==========
# OpenAI-compatible API
OPENAI_API_KEY=sk-your-api-key
OPENAI_API_BASE=https://your-api-endpoint/v1
MOS_CHAT_MODEL=your-model-name
MOS_CHAT_MODEL_PROVIDER=openai

# ========== Embedding Model ==========
# Use Ollama local embedding (recommended)
MOS_EMBEDDER_BACKEND=ollama
MOS_EMBEDDER_MODEL=nomic-embed-text-v2-moe:latest
OLLAMA_API_BASE=http://localhost:11434
EMBEDDING_DIMENSION=768

# ========== Vector Database ==========
# Qdrant Cloud
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION_NAME=memories

# ========== Optional ==========
# Redis task queue
MEMSCHEDULER_USE_REDIS_QUEUE=false

# Neo4j graph database
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=your-password

# Memory reader
MEM_READER_BACKEND=openai
```

## Startup Script

### run.bat

```batch
@echo off
cd /d "%~dp0"

set PYTHON_EXE=%~dp0conda_venv\python.exe
set PATH=%~dp0conda_venv;%~dp0conda_venv\Scripts;%~dp0conda_venv\Library\bin;%PATH%

echo ========================================
echo    MemOS Windows Launcher
echo ========================================
echo.

echo [1/4] Checking Python...
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found: %PYTHON_EXE%
    pause
    exit /b 1
)
"%PYTHON_EXE%" --version

echo.
echo [2/4] Checking config...
if not exist .env (
    if exist .env.windows.example (
        copy .env.windows.example .env >nul
        echo [INFO] Created .env from template
    )
)

echo.
echo [3/4] Syncing config to src...
copy /y .env src\.env >nul

echo.
echo [4/4] Starting service...
echo ========================================
echo    Server: http://localhost:18000
echo    API Docs: http://localhost:18000/docs
echo    Press Ctrl+C to stop
echo ========================================
echo.

cd /d "%~dp0src"
"%PYTHON_EXE%" -m uvicorn memos.api.start_api:app --host 0.0.0.0 --port 18000 --reload

pause
```

## API Usage

### Chat

```bash
curl -X POST http://localhost:18000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "dev_user", "query": "Hello"}'
```

### Add Memory

```bash
curl -X POST http://localhost:18000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "dev_user",
    "mem_cube_id": "my_project",
    "memory_content": "Important project information"
  }'
```

### Search Memories

```bash
curl -X POST http://localhost:18000/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "dev_user",
    "query": "search keywords",
    "install_cube_ids": ["my_project"]
  }'
```

## Dependencies

### Ollama (Embedding Model)

```bash
# Download: https://ollama.ai
# Pull model
ollama pull nomic-embed-text-v2-moe:latest
```

### Qdrant (Vector Database)

Recommended: [Qdrant Cloud](https://cloud.qdrant.io) free tier.

Local deployment:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### Neo4j (Optional, Graph Database)

Download [Neo4j Community](https://neo4j.com/download/):
```cmd
neo4j-community\bin\neo4j console
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Python not found | Ensure `conda_venv/` directory exists |
| Port in use | Change port number in `run.bat` |
| .env not working | Script auto-copies to `src/`, check root `.env` |
| Dependency install fails | Use official PyPI: `-i https://pypi.org/simple` |

## License

This deployment guide is based on [MemOS](https://github.com/MemTensor/MemOS), licensed under the Apache License 2.0.

## Links

- [MemOS Official Repository](https://github.com/MemTensor/MemOS)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Ollama](https://ollama.ai)
