#!/usr/bin/env python3
"""MCP Server Launcher - Manages MCP server processes for each mode."""

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
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def get_mcp_server_path() -> Path:
    """Get path to MCP server script."""
    # Check relative to memos-cli
    import oh_memosctl
    cli_pkg = Path(memosctl.__file__).parent
    
    # Go up to MemOS root and find mcp-server
    for parent in [cli_pkg.parent.parent, cli_pkg.parent.parent.parent]:
        mcp_server = parent / "mcp-server" / "memos_mcp_server.py"
        if mcp_server.exists():
            return mcp_server
    
    # Check common locations
    for base in [Path.cwd(), Path("/mnt/g/test/MemOS")]:
        mcp_server = base / "mcp-server" / "memos_mcp_server.py"
        if mcp_server.exists():
            return mcp_server
    
    raise FileNotFoundError("Cannot find memos_mcp_server.py")


def build_mcp_env(mode: str, project_dir: Path) -> dict:
    """Build environment variables for MCP server."""
    config = load_config(project_dir / "config.toml") if (project_dir / "config.toml").exists() else load_config()
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
    project_dir: Optional[Path] = None,
    foreground: bool = False,
) -> Optional[int]:
    """Start MCP server for a mode."""
    mode_obj = get_mode(mode)
    project_dir = project_dir or DEFAULT_CONFIG_DIR
    
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
    cmd = [sys.executable, str(mcp_server)]
    
    console.print(f"Starting MCP server for {mode_obj.emoji} {mode_obj.display_name}...")
    
    if foreground:
        subprocess.run(cmd, env=env)
        return None
    else:
        # Run in background
        kwargs = {
            "env": env,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        
        process = subprocess.Popen(cmd, **kwargs)
        write_pid(mode, process.pid)
        console.print(f"[green]âœ?Started (PID {process.pid})[/green]")
        return process.pid


def stop_mcp_server(mode: str) -> bool:
    """Stop MCP server for a mode."""
    pid = read_pid(mode)
    if not pid:
        console.print(f"[dim]No PID file for {mode}[/dim]")
        return True
    
    if not is_process_running(pid):
        console.print(f"[dim]Process {pid} not running, cleaning up[/dim]")
        remove_pid(mode)
        return True
    
    console.print(f"Stopping MCP server for {mode} (PID {pid})...")
    
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], 
                         check=True, capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
            import time
            for _ in range(10):
                if not is_process_running(pid):
                    break
                time.sleep(0.1)
            else:
                os.kill(pid, signal.SIGKILL)
        
        remove_pid(mode)
        console.print(f"[green]âœ?Stopped[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Failed to stop: {e}[/red]")
        return False


def get_mcp_status(mode: str) -> tuple[bool, Optional[int]]:
    """Get MCP server status for a mode."""
    pid = read_pid(mode)
    if pid and is_process_running(pid):
        return True, pid
    return False, None
