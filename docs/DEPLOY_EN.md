# MemOS Windows Portable Deployment Guide

This guide explains how to deploy MemOS memory service on Windows.

---

## Table of Contents

- [Requirements](#requirements)
- [Quick Deployment](#quick-deployment)
- [Database Configuration](#database-configuration)
  - [Qdrant Cloud (Recommended)](#qdrant-cloud-recommended)
  - [Local Qdrant](#local-qdrant)
- [Embedding Model Configuration](#embedding-model-configuration)
- [LLM API Configuration](#llm-api-configuration)
- [Complete Configuration Example](#complete-configuration-example)
- [Troubleshooting](#troubleshooting)

---

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 | Windows 10/11 |
| RAM | 4GB | 8GB+ |
| Disk Space | 2GB | 5GB+ |
| Python | 3.10+ | 3.11+ (auto-installed by script) |

---

## Quick Deployment

### Step 1: Install Python Environment

```cmd
Double-click setup_env.bat
```

The script will automatically:
1. Download Miniconda (~80MB)
2. Install to `project_directory\conda_venv\`
3. Display full installation paths

After completion, you'll see:
```
========================================
   Setup Complete!
========================================

   Python executable:
   G:\test\MemOS\conda_venv\python.exe

   Pip executable:
   G:\test\MemOS\conda_venv\Scripts\pip.exe

   Environment directory:
   G:\test\MemOS\conda_venv
```

### Step 2: Install Dependencies and Start

```cmd
Double-click install_run.bat
```

First run installs all dependencies. Use `run.bat` for subsequent quick starts.

### Step 3: Verify Deployment

Visit http://localhost:18000/docs to see the API documentation.

---

## Database Configuration

MemOS uses Qdrant as the vector database for memory storage. Two deployment options:

### Qdrant Cloud (Recommended)

**Advantages**:
- Generous free tier (1GB storage)
- No local resources needed
- Persistent data across restarts
- Multi-device access support

**Configuration Steps**:

1. **Register Qdrant Cloud Account**

   Visit https://cloud.qdrant.io/ (GitHub/Google login supported)

2. **Create Free Cluster**

   - Click "Create Cluster"
   - Select "Free" tier
   - Choose nearest region (e.g., `aws-us-east-1`)
   - Note the cluster URL: `https://xxx-xxx.aws.qdrant.io:6333`

3. **Get API Key**

   - Go to cluster details
   - Click "API Keys" → "Create API Key"
   - Copy the generated key

4. **Configure .env File**

   ```env
   # Qdrant Cloud Configuration
   QDRANT_MODE=cloud
   QDRANT_URL=https://your-cluster-url.aws.qdrant.io:6333
   QDRANT_API_KEY=your-api-key-here
   ```

### Local Qdrant

**Advantages**:
- Fully offline operation
- Local data storage

**Configuration Steps**:

1. **Start with Docker**

   ```bash
   docker run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant
   ```

2. **Configure .env File**

   ```env
   # Local Qdrant Configuration
   QDRANT_MODE=local
   QDRANT_URL=http://localhost:6333
   # No API Key needed for local mode
   ```

---

## Embedding Model Configuration

MemOS requires an embedding model to convert text to vectors. Ollama local models are recommended.

### Install Ollama

1. Download and install Ollama: https://ollama.ai/download

2. Pull embedding model:
   ```bash
   ollama pull nomic-embed-text
   ```

3. Configure .env:
   ```env
   # Ollama Embedding Configuration
   EMBEDDING_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_EMBEDDING_MODEL=nomic-embed-text
   ```

### Other Embedding Model Options

| Model | Configuration | Notes |
|-------|---------------|-------|
| nomic-embed-text | `OLLAMA_EMBEDDING_MODEL=nomic-embed-text` | Recommended, balanced |
| nomic-embed-text-v2-moe | `OLLAMA_EMBEDDING_MODEL=nomic-embed-text-v2-moe` | Newer version |
| OpenAI | `EMBEDDING_PROVIDER=openai` | Requires API Key |

---

## LLM API Configuration

MemOS context enhancement requires an LLM API. Supports OpenAI-compatible format.

### Using OpenAI

```env
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### Using Other Compatible APIs

```env
# Example: DeepSeek
OPENAI_API_KEY=your-deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# Example: Local Ollama
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3
```

---

## Complete Configuration Example

Full `.env` file example:

```env
# ========================================
# MemOS Configuration
# ========================================

# --- Server ---
HOST=0.0.0.0
PORT=18000

# --- Qdrant Vector Database ---
# Using Qdrant Cloud (Recommended)
QDRANT_MODE=cloud
QDRANT_URL=https://your-cluster.aws.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key

# --- Embedding Model ---
# Using Ollama Local Embedding
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

## Troubleshooting

### Q: "Python not found" on startup

**A**: Run `setup_env.bat` first to install the Python environment.

### Q: Qdrant connection failed

**A**: Check the following:
1. Verify `QDRANT_URL` format in `.env` is correct
2. Ensure `QDRANT_API_KEY` has no extra spaces
3. If using Cloud, confirm cluster status is "Running"

### Q: Embedding model error

**A**: Confirm Ollama is running:
```bash
ollama list  # View installed models
ollama serve  # Start service if not running
```

### Q: Port 18000 is occupied

**A**: Change `PORT` in `.env` to another port, or close the program using port 18000.

### Q: Where is memory data stored?

**A**:
- Vector data: Stored in Qdrant (Cloud or local)
- Metadata: Stored in `./data/memos_cubes/` directory

---

## Service Management

### Start Service
```cmd
run.bat
```

### View API Documentation
```
http://localhost:18000/docs
```

### Test API
```bash
# Save memory
curl -X POST http://localhost:18000/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "Test memory", "user_id": "dev_user"}'

# Search memories
curl -X POST http://localhost:18000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "user_id": "dev_user"}'
```

---

## Related Links

- [MemOS Official Repository](https://github.com/MemTensor/MemOS)
- [Qdrant Cloud](https://cloud.qdrant.io/)
- [Ollama](https://ollama.ai/)
