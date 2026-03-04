#!/bin/bash

# MemOS Bundle Stopper for Linux/macOS
# 一键停止脚本 - 停止所有服务

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME="$BUNDLE_ROOT/runtime"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo "========================================"
echo "  MemOS 服务停止中..."
echo "  Stopping MemOS Services..."
echo "========================================"
echo ""

# ============================================
# 停止 MemOS API (Python/uvicorn)
# ============================================
echo "[1/3] 停止 MemOS API..."

if [ -f "$BUNDLE_ROOT/data/pids/api.pid" ]; then
    kill $(cat "$BUNDLE_ROOT/data/pids/api.pid") 2>/dev/null
    rm -f "$BUNDLE_ROOT/data/pids/api.pid"
fi

# 查找并停止 uvicorn 进程
pkill -f "uvicorn oh_memos.api.start_api:app" 2>/dev/null || true
echo -e "      MemOS API 已停止 ${GREEN}✓${NC}"

# ============================================
# 停止 Qdrant
# ============================================
echo "[2/3] 停止 Qdrant..."

if [ -f "$BUNDLE_ROOT/data/pids/qdrant.pid" ]; then
    kill $(cat "$BUNDLE_ROOT/data/pids/qdrant.pid") 2>/dev/null
    rm -f "$BUNDLE_ROOT/data/pids/qdrant.pid"
fi

pkill -f "qdrant" 2>/dev/null || true
echo -e "      Qdrant 已停止 ${GREEN}✓${NC}"

# ============================================
# 停止 Neo4j
# ============================================
echo "[3/3] 停止 Neo4j..."

export NEO4J_HOME="$RUNTIME/neo4j"
export JAVA_HOME="$RUNTIME/jre"

if [ -f "$NEO4J_HOME/bin/neo4j" ]; then
    "$NEO4J_HOME/bin/neo4j" stop 2>/dev/null || true
fi

pkill -f "neo4j" 2>/dev/null || true
echo -e "      Neo4j 已停止 ${GREEN}✓${NC}"

echo ""
echo "========================================"
echo -e "  ${GREEN}所有服务已停止${NC}"
echo "  All services stopped"
echo "========================================"
echo ""
