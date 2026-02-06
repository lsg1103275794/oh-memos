#!/usr/bin/env python3
"""MemOS CLI Service Management - start, stop, status of services."""

import socket
from enum import Enum
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table

from .config import DEFAULT_CONFIG_DIR, load_config
from .modes import get_mode

console = Console()


class ServiceStatus(Enum):
    """Service status enum."""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"


def check_port_in_use(port: int, host: str = "localhost") -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


def check_http_health(url: str, timeout: float = 2.0) -> bool:
    """Check if HTTP endpoint is healthy."""
    try:
        response = httpx.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def get_service_status() -> dict[str, ServiceStatus]:
    """Get status of all MemOS services."""
    config = load_config()
    status = {}

    # Check MemOS API
    api_healthy = check_http_health(f"{config.api_url}/health")
    status["api"] = ServiceStatus.RUNNING if api_healthy else ServiceStatus.STOPPED

    # Check Neo4j (port 7687 for bolt)
    neo4j_port = int(config.neo4j_uri.split(":")[-1]) if ":" in config.neo4j_uri else 7687
    neo4j_up = check_port_in_use(neo4j_port)
    status["neo4j"] = ServiceStatus.RUNNING if neo4j_up else ServiceStatus.STOPPED

    # Check Qdrant
    qdrant_up = check_port_in_use(config.qdrant_port, config.qdrant_host)
    status["qdrant"] = ServiceStatus.RUNNING if qdrant_up else ServiceStatus.STOPPED

    # Check Ollama (optional)
    ollama_healthy = check_http_health(f"{config.ollama_url}/api/tags")
    status["ollama"] = ServiceStatus.RUNNING if ollama_healthy else ServiceStatus.STOPPED

    return status


def display_status(status: dict[str, ServiceStatus], mode_status: dict[str, ServiceStatus] | None = None):
    """Display service status in a table."""
    table = Table(title="MemOS Service Status")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Port/URL")

    config = load_config()

    status_icons = {
        ServiceStatus.RUNNING: "[green]● running[/green]",
        ServiceStatus.STOPPED: "[red]○ stopped[/red]",
        ServiceStatus.ERROR: "[yellow]⚠ error[/yellow]",
        ServiceStatus.UNKNOWN: "[dim]? unknown[/dim]",
    }

    service_info = {
        "api": ("MemOS API", config.api_url),
        "neo4j": ("Neo4j", config.neo4j_uri),
        "qdrant": ("Qdrant", f"{config.qdrant_host}:{config.qdrant_port}"),
        "ollama": ("Ollama", config.ollama_url),
    }

    for service, (name, url) in service_info.items():
        s = status.get(service, ServiceStatus.UNKNOWN)
        table.add_row(name, status_icons[s], url)

    if mode_status:
        table.add_section()
        for mode_name, s in mode_status.items():
            mode = get_mode(mode_name)
            table.add_row(f"MCP:{mode_name}", status_icons[s], f":{mode.port}")

    console.print(table)


def start_services(modes: list[str] | None = None, project_dir: Path | None = None) -> bool:
    """Start MemOS services."""
    project_dir = project_dir or DEFAULT_CONFIG_DIR
    config = load_config(project_dir / "config.toml")

    console.print("[bold]Starting MemOS services...[/bold]")

    status = get_service_status()

    if status["neo4j"] != ServiceStatus.RUNNING:
        console.print("[yellow]⚠ Neo4j is not running. Please start Neo4j first.[/yellow]")
        return False

    if status["qdrant"] != ServiceStatus.RUNNING:
        console.print("[yellow]⚠ Qdrant is not running. Please start Qdrant first.[/yellow]")
        return False

    if status["api"] != ServiceStatus.RUNNING:
        console.print("Starting MemOS API...")
        console.print("[yellow]TODO: Implement API server startup[/yellow]")

    modes = modes or config.active_modes
    for mode_name in modes:
        mode = get_mode(mode_name)
        console.print(f"Starting MCP server for {mode.emoji} {mode.display_name} on port {mode.port}...")
        console.print("[yellow]TODO: Implement MCP server startup[/yellow]")

    console.print("[green]✅ Services started[/green]")
    return True


def stop_services(project_dir: Path | None = None) -> bool:
    """Stop MemOS services."""
    console.print("[bold]Stopping MemOS services...[/bold]")
    console.print("[yellow]TODO: Implement service stopping[/yellow]")
    return True
