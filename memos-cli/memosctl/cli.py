#!/usr/bin/env python3
"""
MemOS CLI (memosctl) - Multi-mode Memory Management

Commands:
    init    Initialize a new MemOS project with interactive wizard
    start   Start MemOS services for specified mode(s)
    stop    Stop running MemOS services
    status  Show status of MemOS services
"""

import typer
from rich.console import Console

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
    from memosctl import __version__
    console.print(f"memosctl version {__version__}")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """MemOS CLI - Multi-mode Memory Management."""
    pass


if __name__ == "__main__":
    app()
