"""CLI interface for MuteMe Button Control."""

import typer
from typing import Optional
import sys

from . import __version__
from .hid.device import MuteMeDevice

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


@app.command()
def check_device(
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Show detailed device information")
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
                typer.echo(f"    Device Path: {device.path}")
            
            # Check permissions
            if MuteMeDevice.check_device_permissions(device.path):
                typer.echo("  Permissions: ✅ OK")
            else:
                typer.echo("  Permissions: ❌ FAILED")
                if verbose:
                    error_msg = MuteMeDevice.get_device_permissions_error(device.path)
                    typer.echo("  Error Details:")
                    for line in error_msg.split('\n'):
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
