"""Version command implementation."""

import typer

from ... import __version__
from ...cli import app


def version_callback(value: bool) -> None:
    """Callback for version option."""
    if value:
        typer.echo(f"muteme-btn-control {__version__}")
        raise typer.Exit()


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo(f"muteme-btn-control {__version__}")
