#!/bin/bash

# MemOS MCP Configuration for Claude Code
# 自动配置 MCP 到 Claude Code

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "========================================"
echo "  MemOS MCP 配置工具"
echo "  Configure MCP for Claude Code"
echo "========================================"
echo ""

# Claude Code 配置文件路径
CLAUDE_CONFIG_DIR="$HOME/.claude"
CLAUDE_CONFIG="$CLAUDE_CONFIG_DIR/settings.json"

# 检查 Claude Code 配置目录
if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    echo "[INFO] 创建 Claude Code 配置目录..."
    mkdir -p "$CLAUDE_CONFIG_DIR"
fi

# 确定 Python 路径
if [ "$(uname)" = "Darwin" ]; then
    # macOS
    PYTHON_PATH="$BUNDLE_ROOT/runtime/conda/bin/python"
else
    # Linux
    PYTHON_PATH="$BUNDLE_ROOT/runtime/conda/bin/python"
fi

echo ""
echo "================================================"
echo -e "  ${CYAN}MCP 配置信息 (memoslocal)${NC}"
echo "================================================"
echo ""
echo "  请将以下配置添加到您的 Claude Code settings:"
echo ""
echo -e "  ${YELLOW}方式1: 使用 Claude Code 命令${NC}"
echo "  ----------------------------------"
echo "  在 Claude Code 中运行:"
echo ""
echo "  /mcp add memoslocal"
echo ""
echo "  然后输入以下配置:"
echo "  - command: $PYTHON_PATH"
echo "  - args: $BUNDLE_ROOT/mcp-server/memos_mcp_server.py"
echo ""
echo ""
echo -e "  ${YELLOW}方式2: 手动编辑配置文件${NC}"
echo "  ----------------------------------"
echo "  编辑文件: $CLAUDE_CONFIG"
echo ""
echo "  添加以下内容到 \"mcpServers\" 部分:"
echo ""
cat << EOF
  {
    "mcpServers": {
      "memoslocal": {
        "command": "$PYTHON_PATH",
        "args": ["$BUNDLE_ROOT/mcp-server/memos_mcp_server.py"],
        "env": {
          "MEMOS_URL": "http://localhost:18000",
          "MEMOS_CUBES_DIR": "$BUNDLE_ROOT/data/memos_cubes"
        }
      }
    }
  }
EOF
echo ""
echo "================================================"
echo ""

# 生成配置模板文件
MCP_CONFIG_FILE="$BUNDLE_ROOT/mcp-config.json"

echo "正在生成配置模板文件..."
cat > "$MCP_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "memoslocal": {
      "command": "$PYTHON_PATH",
      "args": ["$BUNDLE_ROOT/mcp-server/memos_mcp_server.py"],
      "env": {
        "MEMOS_URL": "http://localhost:18000",
        "MEMOS_CUBES_DIR": "$BUNDLE_ROOT/data/memos_cubes"
      }
    }
  }
}
EOF

echo ""
echo -e "配置模板已保存到: ${GREEN}$MCP_CONFIG_FILE${NC}"
echo ""
echo "================================================"
echo "  下一步 Next Steps"
echo "================================================"
echo ""
echo "  1. 启动 MemOS 服务: ./start.sh"
echo "  2. 在 Claude Code 中使用 memos_* 工具"
echo ""
echo "  可用工具 Available Tools:"
echo "  - memos_search     : 搜索记忆"
echo "  - memos_save       : 保存记忆"
echo "  - memos_list       : 列出记忆"
echo "  - memos_list_cubes : 列出 Cubes"
echo "  - memos_suggest    : 智能建议"
echo ""
echo "================================================"
echo ""
