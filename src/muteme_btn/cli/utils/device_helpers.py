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
            console.print(
                Panel("[bold cyan]Step 1: Discovering devices...[/bold cyan]", style="bold blue")
            )
        else:
            output_fn("Step 1: Discovering devices...")
    except ImportError:
        output_fn("Step 1: Discovering devices...")

    devices = MuteMeDevice.discover_devices()

    if not devices:
        if console is not None:
            console.print("[red]❌ No MuteMe devices found[/red]")
            console.print("")
            console.print("[bold yellow]Troubleshooting:[/bold yellow]")
            console.print("[dim]• Make sure your MuteMe device is connected[/dim]")
            console.print("[dim]• Check USB cable connection[/dim]")
            console.print("[dim]• Try a different USB port[/dim]")
        else:
            output_fn("❌ No MuteMe devices found")
            output_fn("")
            output_fn("Troubleshooting:")
            output_fn("• Make sure your MuteMe device is connected")
            output_fn("• Check USB cable connection")
            output_fn("• Try a different USB port")
        sys.exit(1)

    if console is not None:
        console.print(f"[green]✅ Found {len(devices)} device(s)[/green]")
    else:
        output_fn(f"✅ Found {len(devices)} device(s)")
    output_fn("")

    # Step 2: Connect to device
    # Use Rich Panel if available
    try:
        from rich.panel import Panel

        if console is not None:
            console.print(
                Panel("[bold cyan]Step 2: Connecting to device...[/bold cyan]", style="bold green")
            )
        else:
            output_fn("Step 2: Connecting to device...")
    except ImportError:
        output_fn("Step 2: Connecting to device...")

    device_info = devices[0]
    vid_pid = f"VID:0x{device_info.vendor_id:04x} PID:0x{device_info.product_id:04x}"
    if console is not None:
        console.print(f"   [dim]Device:[/dim] [cyan]{vid_pid}[/cyan]")
        console.print(f"   [dim]Path:[/dim] [cyan]{device_info.path}[/cyan]")
    else:
        output_fn(f"   Device: {vid_pid}")
        output_fn(f"   Path: {device_info.path}")

    try:
        # Try VID/PID connection first
        device = MuteMeDevice.connect_by_vid_pid(device_info.vendor_id, device_info.product_id)
        if console is not None:
            console.print("[green]✅ Connected successfully using VID/PID[/green]")
        else:
            output_fn("✅ Connected successfully using VID/PID")
    except Exception as e:
        if console is not None:
            console.print(f"[yellow]⚠️  VID/PID connection failed:[/yellow] [red]{e}[/red]")
            console.print("   [dim]Trying path-based connection...[/dim]")
        else:
            output_fn(f"⚠️  VID/PID connection failed: {e}")
            output_fn("   Trying path-based connection...")
        try:
            device = MuteMeDevice.connect(device_info.path)
            if console is not None:
                console.print("[green]✅ Connected successfully using path[/green]")
            else:
                output_fn("✅ Connected successfully using path")
        except Exception as path_error:
            if console is not None:
                console.print(f"[red]❌ Connection failed:[/red] [red]{path_error}[/red]")
            else:
                output_fn(f"❌ Connection failed: {path_error}")
            sys.exit(1)

    return device, device_info
