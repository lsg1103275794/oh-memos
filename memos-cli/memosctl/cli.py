#!/usr/bin/env python3
"""MemOS CLI (memosctl) - Multi-mode Memory Management"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from memosctl import __version__
from memosctl.init_wizard import run_init_wizard
from memosctl.modes import list_modes

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
def start(mode: Optional[str] = typer.Option(None, "--mode", "-m", help="Mode(s) to start")):
    """Start MemOS services for specified mode(s)."""
    console.print("[yellow]TODO: Implement start command[/yellow]")


@app.command()
def stop():
    """Stop running MemOS services."""
    console.print("[yellow]TODO: Implement stop command[/yellow]")


@app.command()
def status():
    """Show status of MemOS services."""
    console.print("[yellow]TODO: Implement status command[/yellow]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """MemOS CLI - Multi-mode Memory Management."""
    pass


if __name__ == "__main__":
    app()
