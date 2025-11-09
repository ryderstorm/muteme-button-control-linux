"""CLI interface for MuteMe Button Control."""

import asyncio
import sys
from pathlib import Path

import typer

from . import __version__
from .config import AppConfig, LogLevel
from .core.daemon import MuteMeDaemon
from .hid.device import MuteMeDevice
from .utils.logging import setup_logging

app = typer.Typer(
    name="muteme-btn-control",
    help="A Linux CLI tool for MuteMe button integration with PulseAudio",
    no_args_is_help=False,
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


@app.command()
def check_device(
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Show detailed device information"),
) -> None:
    """Check MuteMe device status and permissions."""
    try:
        # Discover devices
        devices = MuteMeDevice.discover_devices()

        if not devices:
            typer.echo("❌ No MuteMe devices found")
            typer.echo("")
            typer.echo("Troubleshooting:")
            typer.echo("• Make sure your MuteMe device is connected")
            typer.echo("• Check USB cable connection")
            typer.echo("• Try a different USB port")
            typer.echo("• Install UDEV rules for device permissions")
            sys.exit(1)

        typer.echo(f"✅ Found {len(devices)} MuteMe device(s)")
        typer.echo("")

        # Check each device
        for i, device in enumerate(devices, 1):
            typer.echo(f"Device {i}:")
            typer.echo(f"  VID:PID: 0x{device.vendor_id:04x}:0x{device.product_id:04x}")

            if verbose:
                typer.echo("  Device Details:")
                typer.echo(f"    Vendor ID: 0x{device.vendor_id:04x}")
                typer.echo(f"    Product ID: 0x{device.product_id:04x}")
                typer.echo(f"    Manufacturer: {device.manufacturer or 'Unknown'}")
                typer.echo(f"    Product: {device.product or 'Unknown'}")
                typer.echo(f"    USB Path: {device.path}")

            # Find the corresponding hidraw device
            hidraw_path = MuteMeDevice._find_hidraw_device(device.vendor_id, device.product_id)
            if not hidraw_path:
                typer.echo("  Permissions: ❌ FAILED")
                typer.echo("  Error: Could not find corresponding /dev/hidraw* device")
                typer.echo("  Troubleshooting:")
                typer.echo("    • Try unplugging and replugging the device")
                typer.echo("    • Check if UDEV rules are installed: just install-udev")
                sys.exit(1)

            # At this point, hidraw_path is guaranteed to be a string
            assert hidraw_path is not None

            if verbose:
                typer.echo(f"    HIDraw Device: {hidraw_path}")

            # Check permissions on the hidraw device
            if MuteMeDevice.check_device_permissions(hidraw_path):
                typer.echo("  Permissions: ✅ OK")
            else:
                typer.echo("  Permissions: ❌ FAILED")
                if verbose:
                    error_msg = MuteMeDevice.get_device_permissions_error(hidraw_path)
                    typer.echo("  Error Details:")
                    for line in error_msg.split("\n"):
                        if line.strip():
                            typer.echo(f"    {line}")
                sys.exit(1)

            typer.echo("")

        typer.echo("All devices are accessible and ready to use!")

    except Exception as e:
        typer.echo(f"❌ Device discovery failed: {e}")
        typer.echo("")
        typer.echo("This could indicate:")
        typer.echo("• Missing HID library dependencies")
        typer.echo("• System permission issues")
        typer.echo("• Hardware problems")
        sys.exit(1)


def _find_config_file(config_path: Path | None) -> Path | None:
    """Find configuration file in standard locations.

    Args:
        config_path: Explicit config path from CLI (takes precedence)

    Returns:
        Path to config file if found, None otherwise
    """
    if config_path and config_path.exists():
        return config_path

    # Standard locations (in order of precedence)
    standard_locations = [
        Path("muteme.toml"),  # Current directory
        Path.home() / ".config" / "muteme" / "muteme.toml",
        Path("/etc/muteme/muteme.toml"),
    ]

    for location in standard_locations:
        if location.exists():
            return location

    return None


def _load_config(config_path: Path | None, log_level: str | None) -> AppConfig:
    """Load application configuration.

    Args:
        config_path: Optional explicit config file path
        log_level: Optional log level override from CLI

    Returns:
        Loaded AppConfig instance
    """
    found_config = _find_config_file(config_path)

    # Fail fast if explicit config path was provided but doesn't exist
    if config_path and found_config is None:
        typer.echo(f"❌ Configuration file not found: {config_path}", err=True)
        sys.exit(1)

    if found_config:
        try:
            config = AppConfig.from_toml_file(found_config)
            # Override log level if provided via CLI
            if log_level:
                config.logging.level = LogLevel(log_level.upper())
            return config
        except Exception as e:
            typer.echo(f"❌ Failed to load configuration from {found_config}: {e}", err=True)
            sys.exit(1)
    else:
        # Use defaults
        config = AppConfig()
        if log_level:
            config.logging.level = LogLevel(log_level.upper())
        return config


@app.command()
def run(
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    log_level: str | None = typer.Option(
        None,
        "--log-level",
        help="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    ),
) -> None:
    """Run the MuteMe button control daemon."""
    try:
        # Load configuration
        app_config = _load_config(config, log_level)

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


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool | None = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """MuteMe Button Control - Linux CLI for MuteMe button integration."""
    # If no command was provided, run the daemon
    if ctx.invoked_subcommand is None:
        run(config=None, log_level=None)


if __name__ == "__main__":
    app()
