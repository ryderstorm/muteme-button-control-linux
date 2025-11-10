"""Test-device command implementation."""

import asyncio
import sys
import time
from collections.abc import Callable
from pathlib import Path

import typer

from ...cli import app
from ...hid.device import DeviceInfo, LEDColor, MuteMeDevice
from ...utils.logging import setup_logging
from ..utils.config_loader import load_config
from ..utils.device_helpers import discover_and_connect_device

# Conditional Rich import with graceful fallback
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Create dummy classes for type checking
    Console = None  # type: ignore[assignment, misc]
    Panel = None  # type: ignore[assignment, misc]
    Progress = None  # type: ignore[assignment, misc]
    Table = None  # type: ignore[assignment, misc]

# LED timing constants (seconds)
LED_COLOR_HOLD_DURATION = 0.3  # Duration to hold each color
LED_COLOR_TRANSITION_DURATION = 0.1  # Duration for transitions/off periods
LED_COLOR_VISIBLE_DURATION = 0.5  # Duration for color testing
LED_BRIGHTNESS_TEST_DURATION = 3.0  # Duration for brightness level tests


def _get_output_handler() -> tuple[Console | None, Callable]:
    """Get Rich Console instance and output handler function.

    Returns:
        Tuple of (Console instance or None, output function)
    """
    if RICH_AVAILABLE and Console is not None:
        # Configure Console to work well with test capture
        # force_terminal=False allows Rich to work in non-terminal environments (like tests)
        console = Console(force_terminal=False, width=100)
        # Create stderr console once and reuse it
        err_console = Console(file=sys.stderr, force_terminal=False)

        def output_fn(*args, **kwargs):
            """Output function that handles both Rich and typer.echo compatibility."""
            # Handle err parameter for error output
            err = kwargs.pop("err", False)
            # Handle nl parameter (newline control)
            nl = kwargs.pop("nl", True)

            if err:
                # For Rich, use stderr console
                if nl:
                    err_console.print(*args, **kwargs)
                else:
                    # For no newline, use print with end=""
                    err_console.print(*args, **kwargs, end="")
            else:
                # Normal output
                if nl:
                    console.print(*args, **kwargs)
                else:
                    # For no newline, use print with end=""
                    console.print(*args, **kwargs, end="")

        return console, output_fn
    return None, typer.echo


def _flash_rgb_pattern(device: MuteMeDevice, cycles: int = 1) -> None:
    """Flash a gentle RGB pattern on device with dim brightness.

    Uses a single RGB cycle with longer holds and dim brightness to avoid
    seizure-inducing flashing patterns.

    Args:
        device: MuteMe device to control
        cycles: Number of RGB cycles to flash (default: 1 for gentle pattern)
    """
    rgb_colors = [LEDColor.RED, LEDColor.GREEN, LEDColor.BLUE]
    for _ in range(cycles):
        for color in rgb_colors:
            device.set_led_color(
                color,
                use_feature_report=False,
                report_format="report_id_0",
                brightness="dim",
            )
            time.sleep(LED_COLOR_HOLD_DURATION)
            device.set_led_color(
                LEDColor.NOCOLOR, use_feature_report=False, report_format="report_id_0"
            )
            time.sleep(LED_COLOR_TRANSITION_DURATION)


def _display_device_info(
    device_info: DeviceInfo, console: Console | None = None, output_fn=typer.echo
) -> None:
    """Display device information.

    Args:
        device_info: Device information to display
        console: Rich Console instance (optional)
        output_fn: Output function to use (console.print or typer.echo)
    """
    output_fn("")
    if RICH_AVAILABLE and console is not None:
        console.print("[bold yellow]Device Information:[/bold yellow]")
        console.print(f"  [cyan]Vendor ID:[/cyan] [white]0x{device_info.vendor_id:04x}[/white]")
        console.print(f"  [cyan]Product ID:[/cyan] [white]0x{device_info.product_id:04x}[/white]")
        manufacturer = device_info.manufacturer or "Unknown"
        console.print(f"  [cyan]Manufacturer:[/cyan] [white]{manufacturer}[/white]")
        product = device_info.product or "Unknown"
        console.print(f"  [cyan]Product:[/cyan] [white]{product}[/white]")
        console.print(f"  [cyan]USB Path:[/cyan] [white]{device_info.path}[/white]")
    else:
        output_fn("Device Information:")
        output_fn(f"  Vendor ID: 0x{device_info.vendor_id:04x}")
        output_fn(f"  Product ID: 0x{device_info.product_id:04x}")
        output_fn(f"  Manufacturer: {device_info.manufacturer or 'Unknown'}")
        output_fn(f"  Product: {device_info.product or 'Unknown'}")
        output_fn(f"  USB Path: {device_info.path}")
    output_fn("")


def _test_led_colors(
    device: MuteMeDevice, interactive: bool, console: Console | None = None, output_fn=typer.echo
) -> list[str]:
    """Test LED colors on the device.

    Args:
        device: MuteMe device to test
        interactive: Whether to run in interactive mode
        console: Rich Console instance (optional)
        output_fn: Output function to use (console.print or typer.echo)

    Returns:
        List of error messages for failed colors
    """
    # Use Rich Panel for section header if available
    if RICH_AVAILABLE and Panel is not None and console is not None:
        panel_text = "[bold cyan]Step 3: Testing LED control...[/bold cyan]"
        console.print(Panel(panel_text, style="bold blue"))
    else:
        output_fn("Step 3: Testing LED control...")
    if RICH_AVAILABLE and console is not None:
        format_text = "[yellow]report_id_0 (output) - [0x00, color_value][/yellow]"
        console.print(f"   [dim]Testing with format:[/dim] {format_text}")
    else:
        output_fn("   Testing with format: report_id_0 (output) - [0x00, color_value]")
    output_fn("")

    # Test all available colors in order
    all_colors = [
        ("OFF", LEDColor.NOCOLOR),
        ("RED", LEDColor.RED),
        ("GREEN", LEDColor.GREEN),
        ("BLUE", LEDColor.BLUE),
        ("YELLOW", LEDColor.YELLOW),
        ("CYAN", LEDColor.CYAN),
        ("PURPLE", LEDColor.PURPLE),
        ("WHITE", LEDColor.WHITE),
    ]

    if interactive:
        output_fn("   Colors will be tested in this order:")
        for i, (color_name, _) in enumerate(all_colors, 1):
            output_fn(f"      {i}. {color_name}")
        output_fn("")
        output_fn("   Press ENTER to begin color tests...")
        input()
        output_fn("")

    all_led_errors = []

    if RICH_AVAILABLE and console is not None:
        console.print("   [bold]Testing all colors:[/bold]")
    else:
        output_fn("   Testing all colors:")
    output_fn("")

    # Use Rich Progress bar in non-interactive mode
    if not interactive and RICH_AVAILABLE and Progress is not None and console is not None:
        # Ensure spacing before progress bar
        output_fn("")
        with Progress(console=console, transient=False) as progress:
            task = progress.add_task("[cyan]Testing colors...", total=len(all_colors))
            for color_name, color in all_colors:
                # Update progress bar description dynamically
                progress.update(task, description=f"[cyan]Testing {color_name}...")
                try:
                    device.set_led_color(
                        color, use_feature_report=False, report_format="report_id_0"
                    )
                    time.sleep(LED_COLOR_VISIBLE_DURATION)
                    progress.update(task, advance=1)
                except Exception as e:
                    all_led_errors.append(f"{color_name}: {e}")
                    error_desc = f"[red]Error testing {color_name}..."
                    progress.update(task, advance=1, description=error_desc)
            # Show summary after progress completes with color names
            if all_led_errors:
                color_names = ", ".join([name for name, _ in all_colors])
                console.print(
                    f"   [yellow]⚠️  Tested {len(all_colors)} colors[/yellow] "
                    f"[red]({len(all_led_errors)} error(s))[/red]: "
                    f"[white]{color_names}[/white]"
                )
            else:
                color_names = ", ".join([name for name, _ in all_colors])
                console.print(
                    f"   [green]✅ Tested {len(all_colors)} colors successfully:[/green] "
                    f"[bold white]{color_names}[/bold white]"
                )
    else:
        # Interactive mode or fallback
        for i, (color_name, color) in enumerate(all_colors, 1):
            output_fn(f"   {i}. Setting LED to {color_name}...", nl=False)

            try:
                device.set_led_color(color, use_feature_report=False, report_format="report_id_0")
                output_fn(" ✅")

                if interactive:
                    output_fn("      → Note the color displayed on the device")
                    if i < len(all_colors):
                        output_fn("      → Press ENTER to move to next color...")
                        input()
                    else:
                        output_fn("      → (Last color - test complete)")
                else:
                    time.sleep(LED_COLOR_VISIBLE_DURATION)  # Visible duration per color
            except Exception as e:
                output_fn(f" ❌ Error: {e}")
                all_led_errors.append(f"{color_name}: {e}")
                if interactive and i < len(all_colors):
                    output_fn("      → Press ENTER to continue...")
                    input()

    # Show completion message only for interactive/fallback mode
    # (Progress bar mode shows summary inline)
    if interactive or not (RICH_AVAILABLE and Progress is not None and console is not None):
        output_fn("")
        output_fn("   ✅ Color test complete!")

        if all_led_errors:
            output_fn("")
            output_fn("   ⚠️  Some colors failed:")
            for error in all_led_errors:
                output_fn(f"      • {error}")

        output_fn("")

    return all_led_errors


def _test_brightness_levels(
    device: MuteMeDevice, interactive: bool, console: Console | None = None, output_fn=typer.echo
) -> list[str]:
    """Test brightness levels on the device.

    Args:
        device: MuteMe device to test
        interactive: Whether to run in interactive mode
        console: Rich Console instance (optional)
        output_fn: Output function to use (console.print or typer.echo)

    Returns:
        List of error messages for failed brightness levels
    """
    # Use Rich Panel for section header if available
    if RICH_AVAILABLE and Panel is not None and console is not None:
        panel_text = "[bold cyan]Step 4: Testing brightness levels...[/bold cyan]"
        console.print(Panel(panel_text, style="bold magenta"))
    else:
        output_fn("Step 4: Testing brightness levels...")
    if RICH_AVAILABLE and console is not None:
        console.print(
            "   [dim]Testing brightness/effect levels with[/dim] "
            "[bold white]WHITE[/bold white] [dim]color[/dim]"
        )
    else:
        output_fn("   Testing brightness/effect levels with WHITE color")
    output_fn("")

    brightness_levels = [
        ("Dim", "dim"),
        ("Normal", "normal"),
        ("Flashing", "flashing"),
        ("Fast Pulse", "fast_pulse"),
        ("Slow Pulse", "slow_pulse"),
    ]

    if interactive:
        output_fn("   Brightness levels will be tested in this order:")
        for i, (level_name, _) in enumerate(brightness_levels, 1):
            output_fn(f"      {i}. {level_name}")
        output_fn("")
        output_fn("   Press ENTER to begin brightness tests...")
        input()
        output_fn("")

    all_brightness_errors = []

    # Use Rich Progress bar in non-interactive mode
    if not interactive and RICH_AVAILABLE and Progress is not None and console is not None:
        # Ensure spacing before progress bar
        output_fn("")
        with Progress(console=console, transient=False) as progress:
            task = progress.add_task(
                "[cyan]Testing brightness levels...", total=len(brightness_levels)
            )
            for level_name, brightness in brightness_levels:
                # Update progress bar description dynamically
                progress.update(task, description=f"[cyan]Testing {level_name}...")
                try:
                    device.set_led_color(
                        LEDColor.WHITE,
                        use_feature_report=False,
                        report_format="report_id_0",
                        brightness=brightness,
                    )
                    time.sleep(LED_BRIGHTNESS_TEST_DURATION)
                    progress.update(task, advance=1)
                except Exception as e:
                    all_brightness_errors.append(f"{level_name}: {e}")
                    error_desc = f"[red]Error testing {level_name}..."
                    progress.update(task, advance=1, description=error_desc)
            # Show summary after progress completes with level names
            if all_brightness_errors:
                console.print(
                    f"   [yellow]⚠️  Tested {len(brightness_levels)} brightness levels[/yellow] "
                    f"[red]({len(all_brightness_errors)} error(s))[/red]: "
                    f"[white]{', '.join([level for level, _ in brightness_levels])}[/white]"
                )
            else:
                level_names = ", ".join([level for level, _ in brightness_levels])
                success_msg = (
                    f"   [green]✅ Tested {len(brightness_levels)} "
                    f"brightness levels successfully:[/green] "
                    f"[bold white]{level_names}[/bold white]"
                )
                console.print(success_msg)
    else:
        # Interactive mode or fallback
        for i, (level_name, brightness) in enumerate(brightness_levels, 1):
            output_fn(f"   {i}. Setting WHITE to {level_name}...", nl=False)
            try:
                device.set_led_color(
                    LEDColor.WHITE,
                    use_feature_report=False,
                    report_format="report_id_0",
                    brightness=brightness,
                )
                output_fn(" ✅")
                if interactive:
                    output_fn("      → Note the brightness/effect on the device")
                    if i < len(brightness_levels):
                        output_fn("      → Press ENTER to move to next brightness level...")
                        input()
                    else:
                        output_fn("      → (Last brightness level - test complete)")
                        output_fn("      → Press ENTER to continue to button test...")
                        input()
                else:
                    time.sleep(LED_BRIGHTNESS_TEST_DURATION)  # Duration per brightness level
            except Exception as e:
                output_fn(f" ❌ Error: {e}")
                all_brightness_errors.append(f"{level_name}: {e}")
                if interactive:
                    output_fn("      → Press ENTER to continue...")
                    input()

    # Show completion message only for interactive/fallback mode
    # (Progress bar mode shows summary inline)
    if interactive or not (RICH_AVAILABLE and Progress is not None and console is not None):
        output_fn("")
        output_fn("   ✅ Brightness test complete!")

        if all_brightness_errors:
            output_fn("")
            output_fn("   ⚠️  Some brightness levels failed:")
            for error in all_brightness_errors:
                output_fn(f"      • {error}")

        output_fn("")

    return all_brightness_errors


async def _test_button_communication_async(
    device: MuteMeDevice, console: Console | None = None, output_fn=typer.echo
) -> bool:
    """Test button communication asynchronously.

    Args:
        device: MuteMe device to test
        console: Rich Console instance (optional)
        output_fn: Output function to use (console.print or typer.echo)

    Returns:
        True if button press detected, False otherwise
    """
    button_detected = False
    try:
        # Give device a moment to initialize
        await asyncio.sleep(0.2)

        # Try to read button events for 10 seconds (100 iterations of 100ms)
        for _ in range(100):
            events = await device.read_events()  # type: ignore[call-overload]
            if events:
                button_detected = True
                event = events[0]
                # Change LED to bright green fast pulse on first button press
                try:
                    device.set_led_color(
                        LEDColor.GREEN,
                        use_feature_report=False,
                        report_format="report_id_0",
                        brightness="fast_pulse",
                    )
                    output_fn(f"   ✅ Button event detected: {event.type}")
                    output_fn(
                        f"   LED set to bright green fast pulse "
                        f"(will stay on for {LED_BRIGHTNESS_TEST_DURATION} seconds)"
                    )
                    # Keep the green fast pulse for duration
                    await asyncio.sleep(LED_BRIGHTNESS_TEST_DURATION)
                except Exception as e:
                    output_fn(f"   ⚠️  Failed to set LED to green: {e}")
                break
            await asyncio.sleep(0.1)

        if not button_detected:
            output_fn("   ⚠️  No button press detected (OK if not pressed)")
    except Exception as e:
        output_fn(f"   ⚠️  Button read test error: {e}")
    return button_detected


def _test_button_communication(
    device: MuteMeDevice, interactive: bool, console: Console | None = None, output_fn=typer.echo
) -> bool:
    """Test button communication on the device.

    Args:
        device: MuteMe device to test
        interactive: Whether to run in interactive mode
        console: Rich Console instance (optional)
        output_fn: Output function to use (console.print or typer.echo)

    Returns:
        True if button press detected, False otherwise
    """
    # Use Rich Panel for section header if available
    if RICH_AVAILABLE and Panel is not None and console is not None:
        panel_text = "[bold cyan]Step 5: Testing button communication...[/bold cyan]"
        console.print(Panel(panel_text, style="bold green"))
    else:
        output_fn("Step 5: Testing button communication...")

    if interactive:
        output_fn("")
        output_fn("   Press ENTER when ready to start button test...")
        input()
        output_fn("")
        # Set LED to dim red slow pulse when user presses ENTER
        try:
            device.set_led_color(
                LEDColor.RED,
                use_feature_report=False,
                report_format="report_id_0",
                brightness="slow_pulse",
            )
            output_fn("   LED set to dim red slow pulse - ready for button test")
        except Exception as e:
            output_fn(f"   ⚠️  Failed to set LED: {e}")
        output_fn("")
        output_fn("   Press the MuteMe button now...")
        output_fn("   (Waiting up to 10 seconds for button press...)")
        output_fn("   LED will change to bright green fast pulse when button is pressed")

        # Use Rich console.status() for indeterminate operation
        if RICH_AVAILABLE and console is not None:
            with console.status("[bold yellow]Waiting for button press...", spinner="dots"):
                button_detected = asyncio.run(
                    _test_button_communication_async(device, console, output_fn)
                )
        else:
            button_detected = asyncio.run(
                _test_button_communication_async(device, console, output_fn)
            )
    else:
        output_fn("   (Button test skipped in non-interactive mode)")
        button_detected = False

    output_fn("")

    return button_detected


def _display_diagnostic_summary(
    button_detected: bool,
    all_led_errors: list[str],
    num_colors: int,
    console: Console | None = None,
    output_fn=typer.echo,
) -> None:
    """Display diagnostic summary.

    Args:
        button_detected: Whether button communication was detected
        all_led_errors: List of LED error messages
        num_colors: Number of colors tested
        console: Rich Console instance (optional)
        output_fn: Output function to use (console.print or typer.echo)
    """
    output_fn("")
    # Use Rich Panel for section header if available
    if RICH_AVAILABLE and Panel is not None and console is not None:
        panel_text = "[bold cyan]Step 6: Diagnostic Summary[/bold cyan]"
        console.print(Panel(panel_text, style="bold yellow"))
    else:
        output_fn("Step 6: Diagnostic Summary")
        if RICH_AVAILABLE and console is not None:
            console.rule("Step 6: Diagnostic Summary")
        else:
            output_fn("=" * 50)

    # Use Rich Table if available
    if RICH_AVAILABLE and Table is not None and console is not None:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Test", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")

        table.add_row("Device Connection", "[green]✅ Connected[/green]")
        button_status = (
            "[green]✅ Working[/green]" if button_detected else "[yellow]⚠️  Not tested[/yellow]"
        )
        table.add_row("Button Communication", button_status)
        led_status = (
            "[green]✅ Working[/green]"
            if not all_led_errors
            else f"[red]❌ {len(all_led_errors)} error(s)[/red]"
        )
        table.add_row("LED Control", led_status)
        table.add_row("Colors Tested", f"[cyan]{num_colors} colors[/cyan]")
        table.add_row(
            "Report Format", "[yellow]report_id_0 (output) - [0x00, color_value][/yellow]"
        )

        console.print(table)
    else:
        # Fallback to text output
        output_fn("Device Connection: ✅ Connected")
        output_fn(f"Button Communication: {'✅ Working' if button_detected else '⚠️  Not tested'}")
        led_status = "✅ Working" if not all_led_errors else f"❌ {len(all_led_errors)} error(s)"
        output_fn(f"LED Control: {led_status}")
        output_fn(f"Colors Tested: {num_colors} colors")
        output_fn("Report Format: report_id_0 (output) - [0x00, color_value]")

    output_fn("")
    if RICH_AVAILABLE and console is not None:
        console.print("[bold cyan]HID Report Format:[/bold cyan]")
        console.print("  [dim]Report:[/dim] [yellow][0x00, color_value][/yellow]")
        console.print(
            "  [dim]Colors:[/dim] [white]0x00=OFF, 0x01=RED, 0x02=GREEN, 0x03=YELLOW, "
            "0x04=BLUE, 0x05=PURPLE, 0x06=CYAN, 0x07=WHITE[/white]"
        )
    else:
        output_fn("HID Report Format:")
        output_fn("  Report: [0x00, color_value]")
        output_fn(
            "  Colors: 0x00=OFF, 0x01=RED, 0x02=GREEN, 0x03=YELLOW, "
            "0x04=BLUE, 0x05=PURPLE, 0x06=CYAN, 0x07=WHITE"
        )

    if all_led_errors:
        output_fn("")
        output_fn("⚠️  Some LED commands failed. Check:")
        output_fn("  • Device firmware version")
        output_fn("  • HID report format compatibility")
        output_fn("  • Device initialization requirements")
    output_fn("")


def _cleanup_device(
    device: MuteMeDevice, console: Console | None = None, output_fn=typer.echo
) -> None:
    """Clean up device connection and turn off LED.

    Args:
        device: MuteMe device to clean up
        console: Rich Console instance (optional)
        output_fn: Output function to use (console.print or typer.echo)
    """
    # Flash gentle RGB pattern at end (single cycle with dim brightness)
    output_fn("")
    if RICH_AVAILABLE and console is not None:
        console.print("[dim]Flashing RGB pattern...[/dim]")
    else:
        output_fn("Flashing RGB pattern...")
    try:
        _flash_rgb_pattern(device, cycles=1)
        if RICH_AVAILABLE and console is not None:
            console.print("[green]✅ End pattern complete[/green]")
        else:
            output_fn("✅ End pattern complete")
    except Exception as e:
        if RICH_AVAILABLE and console is not None:
            console.print(f"[yellow]⚠️  Failed to flash end pattern:[/yellow] [red]{e}[/red]")
        else:
            output_fn(f"⚠️  Failed to flash end pattern: {e}")

    # Cleanup - turn LED off
    output_fn("")
    if RICH_AVAILABLE and console is not None:
        console.print("[dim]Turning LED off...[/dim]")
    else:
        output_fn("Turning LED off...")
    try:
        device.set_led_color(
            LEDColor.NOCOLOR, use_feature_report=False, report_format="report_id_0"
        )
        if RICH_AVAILABLE and console is not None:
            console.print("[green]✅ LED turned off[/green]")
        else:
            output_fn("✅ LED turned off")
    except Exception as e:
        if RICH_AVAILABLE and console is not None:
            console.print(f"[yellow]⚠️  Failed to turn LED off:[/yellow] [red]{e}[/red]")
        else:
            output_fn(f"⚠️  Failed to turn LED off: {e}")

    # Cleanup
    device.disconnect()


@app.command()
def test_device(
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
    interactive: bool = typer.Option(  # noqa: B008
        False,
        "--interactive",
        "-i",
        help="Interactive mode: pause before changing to each color",
    ),
    color: str | None = typer.Option(  # noqa: B008
        None,
        "--color",
        help="Test specific color only (e.g., 'red', 'blue', 'white'). Skips full test suite.",
    ),
    brightness: str | None = typer.Option(  # noqa: B008
        None,
        "--brightness",
        help=(
            "Test specific brightness only "
            "(e.g., 'dim', 'normal', 'fast_pulse', 'slow_pulse', 'flashing'). "
            "Requires --color."
        ),
    ),
) -> None:
    """Test device communication and LED control with diagnostic output."""
    try:
        # Load configuration
        app_config = load_config(config, log_level)

        # Setup logging (use INFO level for cleaner output, but allow override)
        setup_logging(
            level=(log_level.upper() if log_level else "INFO"),
            format_type=app_config.logging.format.value,
            file_path=app_config.logging.file_path,
            max_file_size=app_config.logging.max_file_size,
            backup_count=app_config.logging.backup_count,
        )

        # Initialize Rich Console if available
        console, output_fn = _get_output_handler()

        # Title header with color
        if RICH_AVAILABLE and console is not None:
            console.rule("[bold cyan]🔍 MuteMe Device Communication Test[/bold cyan]")
            console.print("")
        else:
            output_fn("🔍 MuteMe Device Communication Test")
            output_fn("=" * 50)
            output_fn("")

        # Discover and connect to device
        device, device_info = discover_and_connect_device(console, output_fn)

        # Display device information
        _display_device_info(device_info, console, output_fn)

        # If color/brightness flags are provided, do quick test only
        if color or brightness:
            if brightness and not color:
                output_fn("❌ --brightness requires --color to be specified", err=True)
                sys.exit(1)

            # Quick test mode
            if RICH_AVAILABLE and console is not None:
                console.rule("[bold yellow]Quick Test Mode[/bold yellow]")
                console.print("")
            else:
                output_fn("Quick Test Mode")
                output_fn("=" * 50)
                output_fn("")

            test_color = LEDColor.from_name(color) if color else LEDColor.WHITE
            test_brightness = brightness if brightness else "normal"

            output_fn(f"Testing: Color={test_color.name}, Brightness={test_brightness}")
            output_fn("")

            try:
                if test_brightness == "flashing":
                    # Flashing uses software animation - show info first, then animate
                    output_fn("Starting flashing animation (20 rapid on/off cycles)...")
                    output_fn("")

                    device.set_led_color(
                        test_color,
                        use_feature_report=False,
                        report_format="report_id_0",
                        brightness=test_brightness,
                    )

                    output_fn("✅ Flashing animation complete")
                    output_fn("")
                    output_fn("Observe the device LED. Press ENTER when done...")
                    if interactive:
                        input()
                    else:
                        time.sleep(2)

                    # Cleanup before returning
                    output_fn("")
                    output_fn("Turning LED off...")
                    try:
                        device.set_led_color(
                            LEDColor.NOCOLOR,
                            use_feature_report=False,
                            report_format="report_id_0",
                        )
                        output_fn("✅ LED turned off")
                    except Exception as e:
                        output_fn(f"⚠️  Failed to turn LED off: {e}")
                    device.disconnect()
                    output_fn("✅ Quick test complete")
                    return

                # For non-flashing brightness levels
                device.set_led_color(
                    test_color,
                    use_feature_report=False,
                    report_format="report_id_0",
                    brightness=test_brightness,
                )
                # Calculate and show the actual HID value being sent
                color_value = test_color.value
                if test_brightness == "dim":
                    color_value = test_color.value | 0x10
                elif test_brightness == "fast_pulse":
                    color_value = test_color.value | 0x20
                elif test_brightness == "slow_pulse":
                    color_value = test_color.value | 0x30
                else:
                    color_value = test_color.value

                output_fn(f"✅ Set LED to {test_color.name} with {test_brightness} brightness")
                offset_val = color_value - test_color.value
                output_fn(
                    f"   HID report: [0x00, 0x{color_value:02x}] "
                    f"(color=0x{test_color.value:02x}, offset=0x{offset_val:02x})"
                )
                output_fn("")
                output_fn("Observe the device LED. Press ENTER when done...")
                if interactive:
                    input()
                else:
                    time.sleep(5)
            except Exception as e:
                output_fn(f"❌ Failed to set LED: {e}", err=True)
                sys.exit(1)

            # Cleanup
            _cleanup_device(device, console, output_fn)
            output_fn("✅ Quick test complete")
            return

        # Full test suite (existing behavior)

        # Flash gentle RGB pattern at start (single cycle with dim brightness)
        if RICH_AVAILABLE and console is not None:
            console.print("[dim]Flashing RGB pattern...[/dim]")
        else:
            output_fn("Flashing RGB pattern...")
        try:
            _flash_rgb_pattern(device, cycles=1)
            if RICH_AVAILABLE and console is not None:
                console.print("[green]✅ Start pattern complete[/green]")
            else:
                output_fn("✅ Start pattern complete")
        except Exception as e:
            if RICH_AVAILABLE and console is not None:
                console.print(f"[yellow]⚠️  Failed to flash start pattern:[/yellow] [red]{e}[/red]")
            else:
                output_fn(f"⚠️  Failed to flash start pattern: {e}")
        output_fn("")

        # Set device to dim white after RGB pattern
        if RICH_AVAILABLE and console is not None:
            console.print("[dim]Setting device to dim white...[/dim]")
        else:
            output_fn("Setting device to dim white...")
        try:
            device.set_led_color(
                LEDColor.WHITE,
                use_feature_report=False,
                report_format="report_id_0",
                brightness="dim",
            )
            if RICH_AVAILABLE and console is not None:
                console.print("[green]✅ Device set to dim white[/green]")
            else:
                output_fn("✅ Device set to dim white")
        except Exception as e:
            if RICH_AVAILABLE and console is not None:
                console.print(f"[yellow]⚠️  Failed to set dim white:[/yellow] [red]{e}[/red]")
            else:
                output_fn(f"⚠️  Failed to set dim white: {e}")
        output_fn("")

        # Test LED colors
        all_led_errors = _test_led_colors(device, interactive, console, output_fn)

        # Test brightness levels
        _test_brightness_levels(device, interactive, console, output_fn)

        # Test button communication
        button_detected = _test_button_communication(device, interactive, console, output_fn)

        # Display diagnostic summary
        num_colors = 8  # Number of colors tested
        _display_diagnostic_summary(button_detected, all_led_errors, num_colors, console, output_fn)

        if RICH_AVAILABLE and console is not None:
            console.print("[bold green]✅ Test complete[/bold green]")
        else:
            output_fn("✅ Test complete")

        # Cleanup device
        _cleanup_device(device, console, output_fn)

        if all_led_errors:
            output_fn("")
            output_fn("⚠️  Some LED commands failed. Check:")
            output_fn("  • Device firmware version")
            output_fn("  • HID report format compatibility")
            output_fn("  • Device initialization requirements")
            sys.exit(1)

    except KeyboardInterrupt:
        _, output_fn = _get_output_handler()
        output_fn("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        _, output_fn = _get_output_handler()
        output_fn(f"\n❌ Test failed: {e}", err=True)
        import traceback

        if log_level and log_level.upper() == "DEBUG":
            output_fn(traceback.format_exc(), err=True)
        sys.exit(1)
