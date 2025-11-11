"""Device discovery and connection helper utilities for CLI commands."""

import sys

import typer

from ...hid.device import DeviceInfo, MuteMeDevice


def discover_and_connect_device() -> tuple[MuteMeDevice, DeviceInfo]:
    """Discover and connect to a MuteMe device.

    Returns:
        Tuple of (connected device, device info)

    Raises:
        SystemExit: If no devices found or connection fails
    """
    # Step 1: Discover devices
    typer.echo("Step 1: Discovering devices...")
    devices = MuteMeDevice.discover_devices()

    if not devices:
        typer.echo("❌ No MuteMe devices found")
        typer.echo("")
        typer.echo("Troubleshooting:")
        typer.echo("• Make sure your MuteMe device is connected")
        typer.echo("• Check USB cable connection")
        typer.echo("• Try a different USB port")
        sys.exit(1)

    typer.echo(f"✅ Found {len(devices)} device(s)")
    typer.echo("")

    # Step 2: Connect to device
    typer.echo("Step 2: Connecting to device...")
    device_info = devices[0]
    vid_pid = f"VID:0x{device_info.vendor_id:04x} PID:0x{device_info.product_id:04x}"
    typer.echo(f"   Device: {vid_pid}")
    typer.echo(f"   Path: {device_info.path}")

    try:
        # Try VID/PID connection first
        device = MuteMeDevice.connect_by_vid_pid(device_info.vendor_id, device_info.product_id)
        typer.echo("✅ Connected successfully using VID/PID")
    except Exception as e:
        typer.echo(f"⚠️  VID/PID connection failed: {e}")
        typer.echo("   Trying path-based connection...")
        try:
            device = MuteMeDevice.connect(device_info.path)
            typer.echo("✅ Connected successfully using path")
        except Exception as path_error:
            typer.echo(f"❌ Connection failed: {path_error}")
            sys.exit(1)

    return device, device_info
