#!/bin/bash

# MemOS Runtime Downloader for Linux/macOS
# 下载运行时组件：Miniconda, Neo4j, JRE, Qdrant

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME="$BUNDLE_ROOT/runtime"
TEMP_DIR="$BUNDLE_ROOT/temp"

# 创建目录
mkdir -p "$RUNTIME"
mkdir -p "$TEMP_DIR"

# 检测操作系统
OS="$(uname -s)"
ARCH="$(uname -m)"

# 组件版本
MINICONDA_VERSION="latest"
NEO4J_VERSION="5.28.0"
JRE_VERSION="17.0.13+11"
QDRANT_VERSION="1.15.3"

# 根据系统设置下载 URL
if [ "$OS" = "Darwin" ]; then
    # macOS
    if [ "$ARCH" = "arm64" ]; then
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh"
        JRE_URL="https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.13%2B11/OpenJDK17U-jre_aarch64_mac_hotspot_17.0.13_11.tar.gz"
        QDRANT_URL="https://github.com/qdrant/qdrant/releases/download/v${QDRANT_VERSION}/qdrant-aarch64-apple-darwin.tar.gz"
    else
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
        JRE_URL="https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.13%2B11/OpenJDK17U-jre_x64_mac_hotspot_17.0.13_11.tar.gz"
        QDRANT_URL="https://github.com/qdrant/qdrant/releases/download/v${QDRANT_VERSION}/qdrant-x86_64-apple-darwin.tar.gz"
    fi
    NEO4J_URL="https://dist.neo4j.org/neo4j-community-${NEO4J_VERSION}-unix.tar.gz"
else
    # Linux
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    NEO4J_URL="https://dist.neo4j.org/neo4j-community-${NEO4J_VERSION}-unix.tar.gz"
    JRE_URL="https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.13%2B11/OpenJDK17U-jre_x64_linux_hotspot_17.0.13_11.tar.gz"
    QDRANT_URL="https://github.com/qdrant/qdrant/releases/download/v${QDRANT_VERSION}/qdrant-x86_64-unknown-linux-musl.tar.gz"
fi

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 获取要下载的组件
COMPONENT="${1:-}"

if [ -z "$COMPONENT" ]; then
    echo ""
    echo "用法: download_runtime.sh [component]"
    echo ""
    echo "可用组件 Available components:"
    echo "  conda  - Miniconda Python 3.11"
    echo "  neo4j  - Neo4j Community ${NEO4J_VERSION}"
    echo "  jre    - OpenJDK 17 JRE"
    echo "  qdrant - Qdrant ${QDRANT_VERSION}"
    echo "  all    - 下载所有组件"
    echo ""
    exit 1
fi

# ============================================
# 下载 Miniconda
# ============================================
download_conda() {
    echo ""
    echo "========================================"
    echo "  下载 Miniconda (Python 3.11)"
    echo "========================================"

    if [ -f "$RUNTIME/conda/bin/python" ]; then
        echo "Miniconda 已存在，跳过下载"
        return 0
    fi

    CONDA_INSTALLER="$TEMP_DIR/miniconda.sh"

    echo "正在下载 Miniconda..."
    curl -L -o "$CONDA_INSTALLER" "$MINICONDA_URL"

    if [ ! -f "$CONDA_INSTALLER" ]; then
        echo -e "${RED}[ERROR] Miniconda 下载失败${NC}"
        return 1
    fi

    echo "正在安装 Miniconda（静默模式）..."
    bash "$CONDA_INSTALLER" -b -p "$RUNTIME/conda"

    # 安装必要的包
    echo "安装 Python 基础包..."
    "$RUNTIME/conda/bin/python" -m pip install --upgrade pip --quiet
    "$RUNTIME/conda/bin/python" -m pip install uvicorn fastapi httpx --quiet

    echo -e "Miniconda 安装完成 ${GREEN}✓${NC}"
}

# ============================================
# 下载 OpenJDK JRE
# ============================================
download_jre() {
    echo ""
    echo "========================================"
    echo "  下载 OpenJDK 17 JRE"
    echo "========================================"

    if [ -f "$RUNTIME/jre/bin/java" ]; then
        echo "JRE 已存在，跳过下载"
        return 0
    fi

    JRE_TAR="$TEMP_DIR/jre.tar.gz"

    echo "正在下载 OpenJDK 17..."
    curl -L -o "$JRE_TAR" "$JRE_URL"

    if [ ! -f "$JRE_TAR" ]; then
        echo -e "${RED}[ERROR] JRE 下载失败${NC}"
        return 1
    fi

    echo "正在解压 JRE..."
    mkdir -p "$TEMP_DIR/jre_temp"
    tar -xzf "$JRE_TAR" -C "$TEMP_DIR/jre_temp"

    # 移动到正确位置
    JRE_DIR=$(find "$TEMP_DIR/jre_temp" -maxdepth 1 -type d -name "jdk*" | head -1)
    if [ -n "$JRE_DIR" ]; then
        mv "$JRE_DIR" "$RUNTIME/jre"
    fi
    rm -rf "$TEMP_DIR/jre_temp"

    echo -e "JRE 安装完成 ${GREEN}✓${NC}"
}

# ============================================
# 下载 Neo4j
# ============================================
download_neo4j() {
    echo ""
    echo "========================================"
    echo "  下载 Neo4j Community ${NEO4J_VERSION}"
    echo "========================================"

    if [ -f "$RUNTIME/neo4j/bin/neo4j" ]; then
        echo "Neo4j 已存在，跳过下载"
        return 0
    fi

    NEO4J_TAR="$TEMP_DIR/neo4j.tar.gz"

    echo "正在下载 Neo4j..."
    curl -L -o "$NEO4J_TAR" "$NEO4J_URL"

    if [ ! -f "$NEO4J_TAR" ]; then
        echo -e "${RED}[ERROR] Neo4j 下载失败${NC}"
        return 1
    fi

    echo "正在解压 Neo4j..."
    mkdir -p "$TEMP_DIR/neo4j_temp"
    tar -xzf "$NEO4J_TAR" -C "$TEMP_DIR/neo4j_temp"

    # 移动到正确位置
    NEO4J_DIR=$(find "$TEMP_DIR/neo4j_temp" -maxdepth 1 -type d -name "neo4j*" | head -1)
    if [ -n "$NEO4J_DIR" ]; then
        mv "$NEO4J_DIR" "$RUNTIME/neo4j"
    fi
    rm -rf "$TEMP_DIR/neo4j_temp"

    # 配置 Neo4j
    echo "配置 Neo4j..."
    if [ -f "$RUNTIME/neo4j/conf/neo4j.conf" ]; then
        echo "dbms.security.auth_enabled=false" >> "$RUNTIME/neo4j/conf/neo4j.conf"
        echo "server.default_listen_address=0.0.0.0" >> "$RUNTIME/neo4j/conf/neo4j.conf"
    fi

    # 设置执行权限
    chmod +x "$RUNTIME/neo4j/bin/neo4j"

    echo -e "Neo4j 安装完成 ${GREEN}✓${NC}"
}

# ============================================
# 下载 Qdrant
# ============================================
download_qdrant() {
    echo ""
    echo "========================================"
    echo "  下载 Qdrant ${QDRANT_VERSION}"
    echo "========================================"

    if [ -f "$RUNTIME/qdrant/qdrant" ]; then
        echo "Qdrant 已存在，跳过下载"
        return 0
    fi

    QDRANT_TAR="$TEMP_DIR/qdrant.tar.gz"

    echo "正在下载 Qdrant..."
    curl -L -o "$QDRANT_TAR" "$QDRANT_URL"

    if [ ! -f "$QDRANT_TAR" ]; then
        echo -e "${RED}[ERROR] Qdrant 下载失败${NC}"
        return 1
    fi

    echo "正在解压 Qdrant..."
    mkdir -p "$RUNTIME/qdrant"
    tar -xzf "$QDRANT_TAR" -C "$RUNTIME/qdrant"

    # 设置执行权限
    chmod +x "$RUNTIME/qdrant/qdrant"

    echo -e "Qdrant 安装完成 ${GREEN}✓${NC}"
}

# ============================================
# 清理临时文件
# ============================================
cleanup() {
    echo ""
    echo "清理临时文件..."
    rm -rf "$TEMP_DIR"
    echo "完成！"
}

# ============================================
# 主逻辑
# ============================================
case "$COMPONENT" in
    all)
        download_conda
        download_jre
        download_neo4j
        download_qdrant
        cleanup
        ;;
    conda)
        download_conda
        ;;
    neo4j)
        download_neo4j
        ;;
    jre)
        download_jre
        ;;
    qdrant)
        download_qdrant
        ;;
    *)
        echo "未知组件: $COMPONENT"
        exit 1
        ;;
esac
