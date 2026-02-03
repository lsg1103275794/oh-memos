#!/bin/bash

# MemOS Bundle Installer for Linux/macOS
# 一键安装脚本 - 自动配置运行环境

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME="$BUNDLE_ROOT/runtime"
SCRIPTS="$BUNDLE_ROOT/scripts/bundle"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "========================================"
echo "  MemOS 一键安装程序"
echo "  MemOS Bundle Installer"
echo "========================================"
echo ""

# ============================================
# Step 1: 检查/下载 Python 环境
# ============================================
echo "[1/5] 检查 Python 环境..."

if [ -f "$RUNTIME/conda/bin/python" ]; then
    echo -e "      Python 已安装 ${GREEN}✓${NC}"
else
    echo "      正在下载 Miniconda..."
    bash "$SCRIPTS/download_runtime.sh" conda
fi

# ============================================
# Step 2: 检查/下载 Java 运行时
# ============================================
echo "[2/5] 检查 Java 运行时..."

if [ -f "$RUNTIME/jre/bin/java" ]; then
    echo -e "      Java 已安装 ${GREEN}✓${NC}"
else
    echo "      正在下载 OpenJDK 17..."
    bash "$SCRIPTS/download_runtime.sh" jre
fi

# ============================================
# Step 3: 检查/下载 Neo4j
# ============================================
echo "[3/5] 检查 Neo4j..."

if [ -f "$RUNTIME/neo4j/bin/neo4j" ]; then
    echo -e "      Neo4j 已安装 ${GREEN}✓${NC}"
else
    echo "      正在下载 Neo4j Community..."
    bash "$SCRIPTS/download_runtime.sh" neo4j
fi

# ============================================
# Step 4: 检查/下载 Qdrant
# ============================================
echo "[4/5] 检查 Qdrant..."

if [ -f "$RUNTIME/qdrant/qdrant" ]; then
    echo -e "      Qdrant 已安装 ${GREEN}✓${NC}"
else
    echo "      正在下载 Qdrant..."
    bash "$SCRIPTS/download_runtime.sh" qdrant
fi

# ============================================
# Step 5: 安装 Python 依赖
# ============================================
echo "[5/5] 安装 Python 依赖..."

# 设置 Python 环境
export PATH="$RUNTIME/conda/bin:$PATH"

# 安装项目依赖
echo "      正在安装 MemOS 依赖包..."
cd "$BUNDLE_ROOT"
"$RUNTIME/conda/bin/python" -m pip install -e . --quiet --disable-pip-version-check 2>/dev/null || \
"$RUNTIME/conda/bin/python" -m pip install -r requirements.txt --quiet --disable-pip-version-check

# ============================================
# 初始化配置文件
# ============================================
echo ""
echo "初始化配置文件..."

if [ ! -f "$BUNDLE_ROOT/.env" ]; then
    if [ -f "$BUNDLE_ROOT/.env.bundle.example" ]; then
        cp "$BUNDLE_ROOT/.env.bundle.example" "$BUNDLE_ROOT/.env"
        echo "      已创建 .env 配置文件"
    fi
fi

# 创建数据目录
mkdir -p "$BUNDLE_ROOT/data/memos_cubes/dev_cube"

# ============================================
# 配置 Neo4j
# ============================================
echo ""
echo "配置 Neo4j..."

NEO4J_HOME="$RUNTIME/neo4j"
if [ -f "$NEO4J_HOME/conf/neo4j.conf" ]; then
    if ! grep -q "dbms.security.auth_enabled=false" "$NEO4J_HOME/conf/neo4j.conf" 2>/dev/null; then
        echo "dbms.security.auth_enabled=false" >> "$NEO4J_HOME/conf/neo4j.conf"
        echo "      Neo4j 认证已禁用（开发模式）"
    fi
fi

# 设置可执行权限
chmod +x "$RUNTIME/qdrant/qdrant" 2>/dev/null || true
chmod +x "$RUNTIME/neo4j/bin/neo4j" 2>/dev/null || true

# ============================================
# 安装完成
# ============================================
echo ""
echo "========================================"
echo -e "  ${GREEN}安装完成！ Installation Complete!${NC}"
echo "========================================"
echo ""
echo "  下一步 Next Steps:"
echo ""
echo "  1. 编辑 .env 配置 LLM API Key"
echo "     Edit .env to configure your LLM API Key"
echo ""
echo "  2. 运行 ./configure_mcp.sh 配置 Claude Code"
echo "     Run ./configure_mcp.sh to setup Claude Code MCP"
echo ""
echo "  3. 运行 ./start.sh 启动服务"
echo "     Run ./start.sh to start all services"
echo ""
echo "========================================"
echo ""
