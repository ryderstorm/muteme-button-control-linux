"""Run command implementation."""

import asyncio
import sys
from pathlib import Path

import typer

from ...cli import app
from ...core.daemon import MuteMeDaemon
from ...utils.logging import setup_logging
from ..utils.config_loader import load_config


@app.command()
def run(
    config: Path | None = typer.Option(  # noqa: B008
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    log_level: str | None = typer.Option(  # noqa: B008
        None,
        "--log-level",
        help="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    ),
) -> None:
    """Run the MuteMe button control daemon."""
    try:
        # Load configuration
        app_config = load_config(config, log_level)

        # Setup logging
        setup_logging(
            level=app_config.logging.level.value,
            format_type=app_config.logging.format.value,
            file_path=app_config.logging.file_path,
            max_file_size=app_config.logging.max_file_size,
            backup_count=app_config.logging.backup_count,
        )

        # Create and run daemon
        daemon = MuteMeDaemon(
            device_config=app_config.device,
            audio_config=app_config.audio,
        )

        # Run the daemon
        asyncio.run(daemon.start())

    except KeyboardInterrupt:
        typer.echo("\nShutting down...", err=True)
        sys.exit(0)
    except Exception as e:
        typer.echo(f"❌ Failed to start daemon: {e}", err=True)
        sys.exit(1)
