"""Device discovery and connection helper utilities for CLI commands."""

import sys
from typing import TYPE_CHECKING

import typer

from ...hid.device import DeviceInfo, MuteMeDevice

if TYPE_CHECKING:
    from rich.console import Console


def discover_and_connect_device(
    console: "Console | None" = None, output_fn=typer.echo
) -> tuple[MuteMeDevice, DeviceInfo]:
    """Discover and connect to a MuteMe device.

    Args:
        console: Rich Console instance (optional)
        output_fn: Output function to use (console.print or typer.echo)

    Returns:
        Tuple of (connected device, device info)

    Raises:
        SystemExit: If no devices found or connection fails
    """
    # Step 1: Discover devices
    # Use Rich Panel if available
    try:
        from rich.panel import Panel

        if console is not None:
            console.print(Panel("Step 1: Discovering devices...", style="bold blue"))
        else:
            output_fn("Step 1: Discovering devices...")
    except ImportError:
        output_fn("Step 1: Discovering devices...")

    devices = MuteMeDevice.discover_devices()

    if not devices:
        output_fn("❌ No MuteMe devices found")
        output_fn("")
        output_fn("Troubleshooting:")
        output_fn("• Make sure your MuteMe device is connected")
        output_fn("• Check USB cable connection")
        output_fn("• Try a different USB port")
        sys.exit(1)

    output_fn(f"✅ Found {len(devices)} device(s)")
    output_fn("")

    # Step 2: Connect to device
    # Use Rich Panel if available
    try:
        from rich.panel import Panel

        if console is not None:
            console.print(Panel("Step 2: Connecting to device...", style="bold blue"))
        else:
            output_fn("Step 2: Connecting to device...")
    except ImportError:
        output_fn("Step 2: Connecting to device...")

    device_info = devices[0]
    vid_pid = f"VID:0x{device_info.vendor_id:04x} PID:0x{device_info.product_id:04x}"
    output_fn(f"   Device: {vid_pid}")
    output_fn(f"   Path: {device_info.path}")

    try:
        # Try VID/PID connection first
        device = MuteMeDevice.connect_by_vid_pid(device_info.vendor_id, device_info.product_id)
        output_fn("✅ Connected successfully using VID/PID")
    except Exception as e:
        output_fn(f"⚠️  VID/PID connection failed: {e}")
        output_fn("   Trying path-based connection...")
        try:
            device = MuteMeDevice.connect(device_info.path)
            output_fn("✅ Connected successfully using path")
        except Exception as path_error:
            output_fn(f"❌ Connection failed: {path_error}")
            sys.exit(1)

    return device, device_info
