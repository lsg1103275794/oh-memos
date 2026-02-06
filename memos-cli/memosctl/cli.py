#!/usr/bin/env python3
"""MemOS CLI (memosctl) - Multi-mode Memory Management"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from memosctl import __version__
from memosctl.init_wizard import run_init_wizard
from memosctl.modes import list_modes, get_mode
from memosctl.service import (
    ServiceStatus,
    check_port_in_use,
    display_status,
    get_service_status,
    get_mode_status,
    start_services,
    stop_services,
)
from memosctl.calendar_cmd import run_calendar

app = typer.Typer(
    name="memosctl",
    help="MemOS CLI - Multi-mode Memory Management",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.command()
def version():
    """Show memosctl version."""
    console.print(f"memosctl version {__version__}")


@app.command()
def init(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Project name"),
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help=f"Mode: {', '.join(list_modes())}"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Neo4j password"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    non_interactive: bool = typer.Option(False, "--yes", "-y", help="Non-interactive mode"),
):
    """Initialize a new MemOS project with interactive wizard."""
    try:
        result = run_init_wizard(
            project_name=name, mode=mode, neo4j_password=password,
            output_dir=output, non_interactive=non_interactive,
        )
        if non_interactive:
            console.print(f"✅ Created project at {result['project_dir']}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def start(
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="Mode(s) to start (comma-separated)"),
    project: Optional[Path] = typer.Option(None, "--project", "-p", help="Project directory"),
):
    """Start MemOS services for specified mode(s)."""
    modes = mode.split(",") if mode else None
    success = start_services(modes=modes, project_dir=project)
    if not success:
        raise typer.Exit(1)


@app.command()
def stop(
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="Mode(s) to stop (comma-separated)"),
    project: Optional[Path] = typer.Option(None, "--project", "-p", help="Project directory"),
):
    """Stop running MemOS services."""
    modes = mode.split(",") if mode else None
    success = stop_services(modes=modes, project_dir=project)
    if not success:
        raise typer.Exit(1)


@app.command()
def status():
    """Show status of MemOS services."""
    from memosctl.service import get_service_status, get_mode_status, display_status

    svc_status = get_service_status()
    mode_status = get_mode_status()
    display_status(svc_status, mode_status)


@app.command()
def calendar(
    semester: Optional[str] = typer.Option("current", "--semester", "-s", help="Semester (e.g., 2026-Spring, current)"),
    course: Optional[str] = typer.Option(None, "--course", "-c", help="Filter by course name"),
    week: Optional[int] = typer.Option(None, "--week", "-w", help="Filter by week number"),
    view: str = typer.Option("list", "--view", "-v", help="View: list, week, month"),
    cube: Optional[str] = typer.Option(None, "--cube", help="Memory cube ID"),
):
    """View learning notes in calendar format (student mode)."""
    success = run_calendar(
        semester=semester,
        course=course,
        week=week,
        view=view,
        cube_id=cube,
    )
    if not success:
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """MemOS CLI - Multi-mode Memory Management."""
    pass


if __name__ == "__main__":
    app()
