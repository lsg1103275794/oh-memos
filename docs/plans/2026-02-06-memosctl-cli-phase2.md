# MemOS CLI Phase 2: MCP Server Integration

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `memosctl start` actually launch MCP server processes on mode-specific ports.

**Architecture:** Each mode runs a separate MCP server process. Process management via subprocess with PID tracking. Configuration passed via environment variables and command-line args.

**Tech Stack:** Python subprocess, psutil (optional), signal handling

---

## Task 1: Create MCP Server Launcher

**Files:**
- Create: `memos-cli/memosctl/mcp_launcher.py`
- Test: `memos-cli/tests/test_mcp_launcher.py`

### Implementation

Create `memos-cli/memosctl/mcp_launcher.py`:

```python
#!/usr/bin/env python3
"""MCP Server Launcher - Manages MCP server processes for each mode."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console

from .config import load_config, DEFAULT_CONFIG_DIR
from .modes import get_mode

console = Console()

# PID file directory
PID_DIR = DEFAULT_CONFIG_DIR / "pids"


def get_pid_file(mode: str) -> Path:
    """Get PID file path for a mode."""
    PID_DIR.mkdir(parents=True, exist_ok=True)
    return PID_DIR / f"mcp_{mode}.pid"


def read_pid(mode: str) -> Optional[int]:
    """Read PID from file."""
    pid_file = get_pid_file(mode)
    if pid_file.exists():
        try:
            return int(pid_file.read_text().strip())
        except (ValueError, OSError):
            return None
    return None


def write_pid(mode: str, pid: int) -> None:
    """Write PID to file."""
    get_pid_file(mode).write_text(str(pid))


def remove_pid(mode: str) -> None:
    """Remove PID file."""
    pid_file = get_pid_file(mode)
    if pid_file.exists():
        pid_file.unlink()


def is_process_running(pid: int) -> bool:
    """Check if a process is running."""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def get_mcp_server_path() -> Path:
    """Get path to MCP server script."""
    # Try to find memos_mcp_server.py relative to this package
    # First check if installed as package
    import memosctl
    cli_dir = Path(memosctl.__file__).parent.parent.parent
    mcp_server = cli_dir / "mcp-server" / "memos_mcp_server.py"
    if mcp_server.exists():
        return mcp_server

    # Fallback: check common locations
    for base in [Path.cwd(), Path.home() / "MemOS", Path("/mnt/g/test/MemOS")]:
        mcp_server = base / "mcp-server" / "memos_mcp_server.py"
        if mcp_server.exists():
            return mcp_server

    raise FileNotFoundError("Cannot find memos_mcp_server.py")


def build_mcp_env(mode: str, project_dir: Path) -> dict:
    """Build environment variables for MCP server."""
    config = load_config(project_dir / "config.toml")
    mode_obj = get_mode(mode)

    env = os.environ.copy()

    # Load .env file if exists
    env_file = project_dir / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()

    # Override with mode-specific settings
    env["MEMOS_MCP_MODE"] = mode
    env["MEMOS_MCP_PORT"] = str(mode_obj.port)

    return env


def start_mcp_server(
    mode: str,
    project_dir: Path,
    foreground: bool = False,
) -> Optional[int]:
    """Start MCP server for a mode.

    Args:
        mode: Mode name
        project_dir: Project directory
        foreground: Run in foreground (blocking)

    Returns:
        PID if started in background, None if foreground
    """
    mode_obj = get_mode(mode)

    # Check if already running
    existing_pid = read_pid(mode)
    if existing_pid and is_process_running(existing_pid):
        console.print(f"[yellow]MCP server for {mode} already running (PID {existing_pid})[/yellow]")
        return existing_pid

    # Get MCP server path
    try:
        mcp_server = get_mcp_server_path()
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        return None

    # Build environment
    env = build_mcp_env(mode, project_dir)

    # Build command
    cmd = [
        sys.executable,
        str(mcp_server),
        f"--memos-default-cube={env.get('MEMOS_DEFAULT_CUBE', 'dev_cube')}",
    ]

    console.print(f"Starting MCP server for {mode_obj.emoji} {mode_obj.display_name} on port {mode_obj.port}...")

    if foreground:
        # Run in foreground
        subprocess.run(cmd, env=env)
        return None
    else:
        # Run in background
        if sys.platform == "win32":
            # Windows: use CREATE_NEW_PROCESS_GROUP
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            # Unix: use nohup-like behavior
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        write_pid(mode, process.pid)
        console.print(f"[green]✓ Started (PID {process.pid})[/green]")
        return process.pid


def stop_mcp_server(mode: str) -> bool:
    """Stop MCP server for a mode.

    Args:
        mode: Mode name

    Returns:
        True if stopped successfully
    """
    pid = read_pid(mode)
    if not pid:
        console.print(f"[dim]No PID file for {mode}[/dim]")
        return True

    if not is_process_running(pid):
        console.print(f"[dim]Process {pid} not running, cleaning up PID file[/dim]")
        remove_pid(mode)
        return True

    console.print(f"Stopping MCP server for {mode} (PID {pid})...")

    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
        else:
            os.kill(pid, signal.SIGTERM)
            # Wait briefly for graceful shutdown
            import time
            for _ in range(10):
                if not is_process_running(pid):
                    break
                time.sleep(0.1)
            else:
                os.kill(pid, signal.SIGKILL)

        remove_pid(mode)
        console.print(f"[green]✓ Stopped[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Failed to stop: {e}[/red]")
        return False


def get_mcp_status(mode: str) -> tuple[bool, Optional[int]]:
    """Get MCP server status for a mode.

    Returns:
        (is_running, pid)
    """
    pid = read_pid(mode)
    if pid and is_process_running(pid):
        return True, pid
    return False, None
```

---

## Task 2: Update Service Module

**Files:**
- Modify: `memos-cli/memosctl/service.py`

Update `start_services` and `stop_services` to use the new launcher.

---

## Task 3: Add MCP Mode Configuration to Server

**Files:**
- Modify: `mcp-server/config.py` - Add MEMOS_MCP_MODE and MEMOS_MCP_PORT support
- Modify: `mcp-server/tools_registry.py` - Filter tools based on mode

This enables the MCP server to run in "mode-aware" configuration.

---

## Summary

Phase 2 connects the CLI to actual MCP server processes:
1. PID-based process management
2. Mode-specific environment configuration
3. Background/foreground process launching
4. Graceful shutdown handling
