#!/bin/bash

# MemOS Bundle Starter for Linux/macOS
# 一键启动脚本 - 启动所有服务

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME="$BUNDLE_ROOT/runtime"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "========================================"
echo "  MemOS 服务启动中..."
echo "  Starting MemOS Services..."
echo "========================================"
echo ""

# 检查运行时是否存在
if [ ! -f "$RUNTIME/conda/bin/python" ]; then
    echo -e "${RED}[ERROR] 运行环境未安装，请先运行 install.sh${NC}"
    echo "[ERROR] Runtime not installed, please run install.sh first"
    exit 1
fi

# 设置环境变量
export JAVA_HOME="$RUNTIME/jre"
export PATH="$JAVA_HOME/bin:$RUNTIME/conda/bin:$PATH"
export NEO4J_HOME="$RUNTIME/neo4j"

# 加载 .env 文件
if [ -f "$BUNDLE_ROOT/.env" ]; then
    set -a
    source "$BUNDLE_ROOT/.env"
    set +a
fi

# 创建 PID 目录
mkdir -p "$BUNDLE_ROOT/data/pids"

# ============================================
# Step 1: 启动 Qdrant
# ============================================
echo "[1/3] 启动 Qdrant (端口 6333)..."

if pgrep -f "qdrant" > /dev/null 2>&1; then
    echo -e "      Qdrant 已在运行 ${GREEN}✓${NC}"
else
    # 确保数据目录存在
    mkdir -p "$BUNDLE_ROOT/data/qdrant"

    # 启动 Qdrant（后台）
    nohup "$RUNTIME/qdrant/qdrant" --storage-path "$BUNDLE_ROOT/data/qdrant" > "$BUNDLE_ROOT/data/logs/qdrant.log" 2>&1 &
    echo $! > "$BUNDLE_ROOT/data/pids/qdrant.pid"
    echo "      Qdrant 启动中..."
fi

# 等待 Qdrant 启动
sleep 2

# ============================================
# Step 2: 启动 Neo4j
# ============================================
echo "[2/3] 启动 Neo4j (端口 7474/7687)..."

if pgrep -f "neo4j" > /dev/null 2>&1 || nc -z localhost 7687 2>/dev/null; then
    echo -e "      Neo4j 已在运行 ${GREEN}✓${NC}"
else
    # 创建日志目录
    mkdir -p "$BUNDLE_ROOT/data/logs"

    # 启动 Neo4j（后台）
    "$NEO4J_HOME/bin/neo4j" start > "$BUNDLE_ROOT/data/logs/neo4j.log" 2>&1
    echo "      Neo4j 启动中..."
fi

# 等待 Neo4j 启动
echo "      等待数据库就绪..."
sleep 8

# ============================================
# Step 3: 启动 MemOS API
# ============================================
echo "[3/3] 启动 MemOS API (端口 18000)..."

if nc -z localhost 18000 2>/dev/null; then
    echo -e "      MemOS API 已在运行 ${GREEN}✓${NC}"
else
    cd "$BUNDLE_ROOT"

    echo ""
    echo "========================================"
    echo -e "  ${GREEN}所有服务启动完成！${NC}"
    echo "  All services started!"
    echo "========================================"
    echo ""
    echo "  服务地址 Service URLs:"
    echo "  - MemOS API: http://localhost:18000/docs"
    echo "  - Neo4j:     http://localhost:7474"
    echo "  - Qdrant:    http://localhost:6333/dashboard"
    echo ""
    echo "  按 Ctrl+C 停止 API 服务"
    echo "  Press Ctrl+C to stop API service"
    echo ""
    echo "----------------------------------------"
    echo ""

    "$RUNTIME/conda/bin/python" -m uvicorn memos.api.start_api:app --host 0.0.0.0 --port 18000
fi
