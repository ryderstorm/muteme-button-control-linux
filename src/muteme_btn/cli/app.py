"""Main Typer app instance for MuteMe Button Control CLI."""

import typer

# Create app first (commands will be imported by cli/__init__.py after app is created)
app = typer.Typer(
    name="muteme-btn-control",
    help="A Linux CLI tool for MuteMe button integration with PulseAudio",
    no_args_is_help=False,
)


def _setup_main_callback() -> None:
    """Set up the main callback after commands are imported."""
    from .commands import run, version

    @app.callback(invoke_without_command=True)
    def main(
        ctx: typer.Context,
        version_flag: bool | None = typer.Option(
            False,
            "--version",
            "-v",
            help="Show version and exit",
            callback=version.version_callback,
            is_eager=True,
        ),
    ) -> None:
        """MuteMe Button Control - Linux CLI for MuteMe button integration."""
        # If no command was provided, run the daemon
        if ctx.invoked_subcommand is None:
            run.run(config=None, log_level=None)
