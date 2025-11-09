"""Check-device command implementation."""

import sys

import typer

from ...cli import app
from ...hid.device import MuteMeDevice


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
