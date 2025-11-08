"""CLI interface for MuteMe Button Control."""

import typer
from typing import Optional

from . import __version__

app = typer.Typer(
    name="muteme-btn-control",
    help="A Linux CLI tool for MuteMe button integration with PulseAudio",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Callback for version option."""
    if value:
        typer.echo(f"muteme-btn-control {__version__}")
        raise typer.Exit()


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo(f"muteme-btn-control {__version__}")


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        False, "--version", "-v", help="Show version and exit", callback=version_callback, is_eager=True
    ),
) -> None:
    """MuteMe Button Control - Linux CLI for MuteMe button integration."""
    pass


if __name__ == "__main__":
    app()
