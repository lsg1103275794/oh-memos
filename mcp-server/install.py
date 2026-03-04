#!/usr/bin/env python3
"""
Install MemOS MCP Server into Claude Code settings.

This script:
1. Installs required dependencies
2. Updates Claude Code settings.json with MCP server config
"""

import json
import os
import subprocess
import sys

from pathlib import Path


def get_claude_settings_path() -> Path:
    """Get the Claude Code settings.json path."""
    if sys.platform == "win32":
        return Path(os.environ.get("USERPROFILE", "")) / ".claude" / "settings.json"
    else:
        return Path.home() / ".claude" / "settings.json"


def install_dependencies():
    """Install required Python packages."""
    print("📦 Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "mcp", "httpx", "pydantic"], check=True)
    print("[OK] Dependencies installed")


def get_mcp_server_path() -> str:
    """Get the absolute path to the MCP server script."""
    script_dir = Path(__file__).parent.absolute()
    server_path = script_dir / "oh_memos_mcp_server.py"

    # Convert to Windows path format if needed
    if sys.platform == "win32" or "wsl" in str(Path("/proc/version").read_text()).lower() if Path("/proc/version").exists() else False:
        # For WSL, convert to Windows path
        return str(server_path).replace("/mnt/g", "G:")

    return str(server_path)


def update_claude_settings():
    """Update Claude Code settings with MCP server config."""
    settings_path = get_claude_settings_path()

    print(f"[NOTE] Updating Claude Code settings at: {settings_path}")

    # Read existing settings
    if settings_path.exists():
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
    else:
        settings = {}

    # Ensure mcpServers exists
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}

    # Ensure configFile.mcpServers exists (for some Claude Code versions)
    if "configFile" not in settings:
        settings["configFile"] = {}
    if "mcpServers" not in settings["configFile"]:
        settings["configFile"]["mcpServers"] = {}

    # Get server path
    server_path = get_mcp_server_path()

    # MCP server configuration
    memos_config = {
        "command": "python",
        "args": [server_path],
        "env": {
            "MEMOS_URL": "http://localhost:18000",
            "MEMOS_USER": "dev_user",
            "MEMOS_DEFAULT_CUBE": "dev_cube"
        },
        "alwaysAllow": [
            "oh-memos_search",
            "oh-memos_save",
            "oh-memos_list",
            "oh-memos_suggest"
        ]
    }

    # Add to both locations for compatibility
    settings["mcpServers"]["oh-memos"] = memos_config
    settings["configFile"]["mcpServers"]["oh-memos"] = memos_config

    # Write back
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    print("[OK] Claude Code settings updated")
    print(f"   Server path: {server_path}")


def main():
    print("=" * 60)
    print("MemOS MCP Server Installer")
    print("=" * 60)
    print()

    try:
        install_dependencies()
        print()
        update_claude_settings()
        print()
        print("=" * 60)
        print("[OK] Installation complete!")
        print()
        print("Next steps:")
        print("1. Restart Claude Code")
        print("2. Make sure MemOS API is running (http://localhost:18000)")
        print("3. Claude will now have access to oh-memos_search, oh-memos_save tools")
        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] Installation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
