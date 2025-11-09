"""CLI interface for MuteMe Button Control."""

import asyncio
import sys
import time
from pathlib import Path

import typer

from . import __version__
from .config import AppConfig, LogLevel
from .core.daemon import MuteMeDaemon
from .hid.device import DeviceInfo, LEDColor, MuteMeDevice
from .utils.logging import setup_logging

# LED timing constants (seconds)
LED_COLOR_HOLD_DURATION = 0.3  # Duration to hold each color
LED_COLOR_TRANSITION_DURATION = 0.1  # Duration for transitions/off periods
LED_COLOR_VISIBLE_DURATION = 0.5  # Duration for color testing
LED_BRIGHTNESS_TEST_DURATION = 3.0  # Duration for brightness level tests

app = typer.Typer(
    name="muteme-btn-control",
    help="A Linux CLI tool for MuteMe button integration with PulseAudio",
    no_args_is_help=False,
)


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


def _discover_and_connect_device() -> tuple[MuteMeDevice, DeviceInfo]:
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


def _display_device_info(device_info: DeviceInfo) -> None:
    """Display device information.

    Args:
        device_info: Device information to display
    """
    typer.echo("")
    typer.echo("Device Information:")
    typer.echo(f"  Vendor ID: 0x{device_info.vendor_id:04x}")
    typer.echo(f"  Product ID: 0x{device_info.product_id:04x}")
    typer.echo(f"  Manufacturer: {device_info.manufacturer or 'Unknown'}")
    typer.echo(f"  Product: {device_info.product or 'Unknown'}")
    typer.echo(f"  USB Path: {device_info.path}")
    typer.echo("")


def _test_led_colors(device: MuteMeDevice, interactive: bool) -> list[str]:
    """Test LED colors on the device.

    Args:
        device: MuteMe device to test
        interactive: Whether to run in interactive mode

    Returns:
        List of error messages for failed colors
    """
    typer.echo("Step 3: Testing LED control...")
    typer.echo("   Testing with format: report_id_0 (output) - [0x00, color_value]")
    typer.echo("")

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
        typer.echo("   Colors will be tested in this order:")
        for i, (color_name, _) in enumerate(all_colors, 1):
            typer.echo(f"      {i}. {color_name}")
        typer.echo("")
        typer.echo("   Press ENTER to begin color tests...")
        input()
        typer.echo("")

    all_led_errors = []

    typer.echo("   Testing all colors:")
    typer.echo("")

    for i, (color_name, color) in enumerate(all_colors, 1):
        typer.echo(f"   {i}. Setting LED to {color_name}...", nl=False)

        try:
            device.set_led_color(color, use_feature_report=False, report_format="report_id_0")
            typer.echo(" ✅")

            if interactive:
                typer.echo("      → Note the color displayed on the device")
                if i < len(all_colors):
                    typer.echo("      → Press ENTER to move to next color...")
                    input()
                else:
                    typer.echo("      → (Last color - test complete)")
            else:
                time.sleep(LED_COLOR_VISIBLE_DURATION)  # Visible duration per color
        except Exception as e:
            typer.echo(f" ❌ Error: {e}")
            all_led_errors.append(f"{color_name}: {e}")
            if interactive and i < len(all_colors):
                typer.echo("      → Press ENTER to continue...")
                input()

    typer.echo("")
    typer.echo("   ✅ Color test complete!")

    if all_led_errors:
        typer.echo("")
        typer.echo("   ⚠️  Some colors failed:")
        for error in all_led_errors:
            typer.echo(f"      • {error}")

    typer.echo("")

    return all_led_errors


def _test_brightness_levels(device: MuteMeDevice, interactive: bool) -> list[str]:
    """Test brightness levels on the device.

    Args:
        device: MuteMe device to test
        interactive: Whether to run in interactive mode

    Returns:
        List of error messages for failed brightness levels
    """
    typer.echo("Step 3b: Testing brightness levels...")
    typer.echo("   Testing brightness/effect levels with WHITE color")
    typer.echo("")

    brightness_levels = [
        ("Dim", "dim"),
        ("Normal", "normal"),
        ("Flashing", "flashing"),
        ("Fast Pulse", "fast_pulse"),
        ("Slow Pulse", "slow_pulse"),
    ]

    if interactive:
        typer.echo("   Brightness levels will be tested in this order:")
        for i, (level_name, _) in enumerate(brightness_levels, 1):
            typer.echo(f"      {i}. {level_name}")
        typer.echo("")
        typer.echo("   Press ENTER to begin brightness tests...")
        input()
        typer.echo("")

    all_brightness_errors = []

    for i, (level_name, brightness) in enumerate(brightness_levels, 1):
        typer.echo(f"   {i}. Setting WHITE to {level_name}...", nl=False)
        try:
            device.set_led_color(
                LEDColor.WHITE,
                use_feature_report=False,
                report_format="report_id_0",
                brightness=brightness,
            )
            typer.echo(" ✅")
            if interactive:
                typer.echo("      → Note the brightness/effect on the device")
                if i < len(brightness_levels):
                    typer.echo("      → Press ENTER to move to next brightness level...")
                    input()
                else:
                    typer.echo("      → (Last brightness level - test complete)")
                    typer.echo("      → Press ENTER to continue to button test...")
                    input()
            else:
                time.sleep(LED_BRIGHTNESS_TEST_DURATION)  # Duration per brightness level
        except Exception as e:
            typer.echo(f" ❌ Error: {e}")
            all_brightness_errors.append(f"{level_name}: {e}")
            if interactive:
                typer.echo("      → Press ENTER to continue...")
                input()

    typer.echo("")
    typer.echo("   ✅ Brightness test complete!")

    if all_brightness_errors:
        typer.echo("")
        typer.echo("   ⚠️  Some brightness levels failed:")
        for error in all_brightness_errors:
            typer.echo(f"      • {error}")

    typer.echo("")

    return all_brightness_errors


async def _test_button_communication_async(device: MuteMeDevice) -> bool:
    """Test button communication asynchronously.

    Args:
        device: MuteMe device to test

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
                    typer.echo(f"   ✅ Button event detected: {event.type}")
                    typer.echo(
                        f"   LED set to bright green fast pulse "
                        f"(will stay on for {LED_BRIGHTNESS_TEST_DURATION} seconds)"
                    )
                    # Keep the green fast pulse for duration
                    await asyncio.sleep(LED_BRIGHTNESS_TEST_DURATION)
                except Exception as e:
                    typer.echo(f"   ⚠️  Failed to set LED to green: {e}")
                break
            await asyncio.sleep(0.1)

        if not button_detected:
            typer.echo("   ⚠️  No button press detected (OK if not pressed)")
    except Exception as e:
        typer.echo(f"   ⚠️  Button read test error: {e}")
    return button_detected


def _test_button_communication(device: MuteMeDevice, interactive: bool) -> bool:
    """Test button communication on the device.

    Args:
        device: MuteMe device to test
        interactive: Whether to run in interactive mode

    Returns:
        True if button press detected, False otherwise
    """
    typer.echo("Step 4: Testing button communication...")

    if interactive:
        typer.echo("")
        typer.echo("   Press ENTER when ready to start button test...")
        input()
        typer.echo("")
        # Set LED to dim red slow pulse when user presses ENTER
        try:
            device.set_led_color(
                LEDColor.RED,
                use_feature_report=False,
                report_format="report_id_0",
                brightness="slow_pulse",
            )
            typer.echo("   LED set to dim red slow pulse - ready for button test")
        except Exception as e:
            typer.echo(f"   ⚠️  Failed to set LED: {e}")
        typer.echo("")
        typer.echo("   Press the MuteMe button now...")
        typer.echo("   (Waiting up to 10 seconds for button press...)")
        typer.echo("   LED will change to bright green fast pulse when button is pressed")

    # Only run button test in interactive mode
    button_detected = False
    if interactive:
        button_detected = asyncio.run(_test_button_communication_async(device))
    else:
        typer.echo("   (Button test skipped in non-interactive mode)")

    typer.echo("")

    return button_detected


def _display_diagnostic_summary(
    button_detected: bool, all_led_errors: list[str], num_colors: int
) -> None:
    """Display diagnostic summary.

    Args:
        button_detected: Whether button communication was detected
        all_led_errors: List of LED error messages
        num_colors: Number of colors tested
    """
    typer.echo("")
    typer.echo("Step 5: Diagnostic Summary")
    typer.echo("=" * 50)
    typer.echo("Device Connection: ✅ Connected")
    typer.echo(f"Button Communication: {'✅ Working' if button_detected else '⚠️  Not tested'}")
    led_status = "✅ Working" if not all_led_errors else f"❌ {len(all_led_errors)} error(s)"
    typer.echo(f"LED Control: {led_status}")
    typer.echo(f"Colors Tested: {num_colors} colors")
    typer.echo("Report Format: report_id_0 (output) - [0x00, color_value]")

    typer.echo("")
    typer.echo("HID Report Format:")
    typer.echo("  Report: [0x00, color_value]")
    typer.echo(
        "  Colors: 0x00=OFF, 0x01=RED, 0x02=GREEN, 0x03=YELLOW, "
        "0x04=BLUE, 0x05=PURPLE, 0x06=CYAN, 0x07=WHITE"
    )

    if all_led_errors:
        typer.echo("")
        typer.echo("⚠️  Some LED commands failed. Check:")
        typer.echo("  • Device firmware version")
        typer.echo("  • HID report format compatibility")
        typer.echo("  • Device initialization requirements")
    typer.echo("")


def _cleanup_device(device: MuteMeDevice) -> None:
    """Clean up device connection and turn off LED.

    Args:
        device: MuteMe device to clean up
    """
    # Flash gentle RGB pattern at end (single cycle with dim brightness)
    typer.echo("")
    typer.echo("Flashing RGB pattern...")
    try:
        _flash_rgb_pattern(device, cycles=1)
        typer.echo("✅ End pattern complete")
    except Exception as e:
        typer.echo(f"⚠️  Failed to flash end pattern: {e}")

    # Cleanup - turn LED off
    typer.echo("")
    typer.echo("Turning LED off...")
    try:
        device.set_led_color(
            LEDColor.NOCOLOR, use_feature_report=False, report_format="report_id_0"
        )
        typer.echo("✅ LED turned off")
    except Exception as e:
        typer.echo(f"⚠️  Failed to turn LED off: {e}")

    # Cleanup
    device.disconnect()


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
) -> None:
    """Test device communication and LED control with diagnostic output."""
    try:
        # Load configuration
        app_config = _load_config(config, log_level)

        # Setup logging (use INFO level for cleaner output, but allow override)
        setup_logging(
            level=(log_level.upper() if log_level else "INFO"),
            format_type=app_config.logging.format.value,
            file_path=app_config.logging.file_path,
            max_file_size=app_config.logging.max_file_size,
            backup_count=app_config.logging.backup_count,
        )

        typer.echo("🔍 MuteMe Device Communication Test")
        typer.echo("=" * 50)
        typer.echo("")

        # Discover and connect to device
        device, device_info = _discover_and_connect_device()

        # Display device information
        _display_device_info(device_info)

        # Flash gentle RGB pattern at start (single cycle with dim brightness)
        typer.echo("Flashing RGB pattern...")
        try:
            _flash_rgb_pattern(device, cycles=1)
            typer.echo("✅ Start pattern complete")
        except Exception as e:
            typer.echo(f"⚠️  Failed to flash start pattern: {e}")
        typer.echo("")

        # Set device to dim white after RGB pattern
        typer.echo("Setting device to dim white...")
        try:
            device.set_led_color(
                LEDColor.WHITE,
                use_feature_report=False,
                report_format="report_id_0",
                brightness="dim",
            )
            typer.echo("✅ Device set to dim white")
        except Exception as e:
            typer.echo(f"⚠️  Failed to set dim white: {e}")
        typer.echo("")

        # Test LED colors
        all_led_errors = _test_led_colors(device, interactive)

        # Test brightness levels
        _test_brightness_levels(device, interactive)

        # Test button communication
        button_detected = _test_button_communication(device, interactive)

        # Display diagnostic summary
        num_colors = 8  # Number of colors tested
        _display_diagnostic_summary(button_detected, all_led_errors, num_colors)

        typer.echo("✅ Test complete")

        # Cleanup device
        _cleanup_device(device)

        if all_led_errors:
            typer.echo("")
            typer.echo("⚠️  Some LED commands failed. Check:")
            typer.echo("  • Device firmware version")
            typer.echo("  • HID report format compatibility")
            typer.echo("  • Device initialization requirements")
            sys.exit(1)

    except KeyboardInterrupt:
        typer.echo("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        typer.echo(f"\n❌ Test failed: {e}", err=True)
        import traceback

        if log_level and log_level.upper() == "DEBUG":
            typer.echo(traceback.format_exc(), err=True)
        sys.exit(1)


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
