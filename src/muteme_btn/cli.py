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


async def _test_device_async(
    device: MuteMeDevice,
    skip_button_test: bool = False,
    interactive: bool = False,
) -> tuple[bool, list[str], list[str]]:
    """Async helper for device testing.

    Returns:
        Tuple of (button_detected, led_errors, formats_tried)
    """
    from muteme_btn.hid.device import LEDColor

    # Give device a moment to initialize
    await asyncio.sleep(0.1)

    # Test button reading (quick, 1 second max)
    button_detected = False
    if not skip_button_test:
        try:
            for _ in range(10):  # 10 * 100ms = 1 second
                events = await device.read_events()  # type: ignore[call-overload]
                if events:
                    button_detected = True
                    break
                await asyncio.sleep(0.1)
        except Exception:  # nosec B110
            pass  # Expected in test - device may not be ready

    # Test LED control with different report formats
    test_colors = [
        ("RED", LEDColor.RED),
        ("GREEN", LEDColor.GREEN),
        ("BLUE", LEDColor.BLUE),
    ]

    # Try different report formats
    formats_to_try = [
        ("standard", False),  # [0x01, color] output report
        ("standard", True),  # [0x01, color] feature report
        ("no_report_id", False),  # [color] output report
        ("report_id_0", False),  # [0x00, color] output report
        ("report_id_2", False),  # [0x02, color] output report
        ("padded", False),  # [0x01, color, 0x00...] 8 bytes output report
    ]

    formats_tried = []
    for format_name, use_feature in formats_to_try:
        format_desc = f"{format_name} ({'feature' if use_feature else 'output'})"
        formats_tried.append(format_desc)

        if interactive:
            # In interactive mode, we'll pause after each format
            # The main function will handle the pause before/after
            pass

        led_errors = []
        for color_name, color in test_colors:
            try:
                device.set_led_color(
                    color, use_feature_report=use_feature, report_format=format_name
                )
                await asyncio.sleep(0.2)  # 200ms per color - more visible
            except Exception as e:
                led_errors.append(f"{color_name}: {e}")

    # If no format worked, return errors from standard format
    if not led_errors:
        led_errors = []
        for color_name, color in test_colors:
            try:
                device.set_led_color(color, use_feature_report=False, report_format="standard")
                await asyncio.sleep(0.2)
            except Exception as e:
                led_errors.append(f"{color_name}: {e}")

    return button_detected, led_errors, formats_tried


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

        typer.echo("")
        typer.echo("Device Information:")
        typer.echo(f"  Vendor ID: 0x{device_info.vendor_id:04x}")
        typer.echo(f"  Product ID: 0x{device_info.product_id:04x}")
        typer.echo(f"  Manufacturer: {device_info.manufacturer or 'Unknown'}")
        typer.echo(f"  Product: {device_info.product or 'Unknown'}")
        typer.echo(f"  USB Path: {device_info.path}")
        typer.echo("")

        # Flash RGB pattern at start (3 cycles)
        typer.echo("Flashing RGB pattern (3 cycles)...")
        try:
            import time

            from muteme_btn.hid.device import LEDColor

            rgb_colors = [LEDColor.RED, LEDColor.GREEN, LEDColor.BLUE]
            for _ in range(3):
                for color in rgb_colors:
                    device.set_led_color(
                        color, use_feature_report=False, report_format="report_id_0"
                    )
                    time.sleep(0.08)  # Faster: 80ms per color
                    device.set_led_color(
                        LEDColor.NOCOLOR, use_feature_report=False, report_format="report_id_0"
                    )
                    time.sleep(0.02)  # Faster: 20ms off between colors
            typer.echo("✅ Start pattern complete")
        except Exception as e:
            typer.echo(f"⚠️  Failed to flash start pattern: {e}")
        typer.echo("")

        # Set device to dim white after RGB pattern
        typer.echo("Setting device to dim white...")
        try:
            from muteme_btn.hid.device import LEDColor

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

        # Step 3: Test LED control with all colors
        typer.echo("Step 3: Testing LED control...")
        typer.echo("   Testing with format: report_id_0 (output) - [0x00, color_value]")
        typer.echo("")

        import time

        from muteme_btn.hid.device import LEDColor

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
                    time.sleep(0.5)  # 500ms per color - visible duration
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

        # Step 3b: Test brightness levels
        typer.echo("Step 3b: Testing brightness levels...")
        typer.echo("   Testing brightness/effect levels with WHITE color")
        typer.echo("")

        brightness_levels = [
            ("Dim", "dim"),
            ("Normal", "normal"),
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
                    import time

                    time.sleep(3.0)  # 3 seconds per brightness level - visible duration
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

        # Step 4: Button communication test
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

            async def test_button():
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
                                    "   LED set to bright green fast pulse "
                                    "(will stay on for 3 seconds)"
                                )
                                # Keep the green fast pulse for 3 seconds
                                await asyncio.sleep(3.0)
                            except Exception as e:
                                typer.echo(f"   ⚠️  Failed to set LED to green: {e}")
                            break
                        await asyncio.sleep(0.1)

                    if not button_detected:
                        typer.echo("   ⚠️  No button press detected (OK if not pressed)")
                except Exception as e:
                    typer.echo(f"   ⚠️  Button read test error: {e}")
                return button_detected

            button_detected = asyncio.run(test_button())
        else:
            typer.echo("   (Button test skipped in non-interactive mode)")

        typer.echo("")

        # Step 5: Diagnostic summary
        typer.echo("")
        typer.echo("Step 5: Diagnostic Summary")
        typer.echo("=" * 50)
        typer.echo("Device Connection: ✅ Connected")
        typer.echo(f"Button Communication: {'✅ Working' if button_detected else '⚠️  Not tested'}")
        led_status = "✅ Working" if not all_led_errors else f"❌ {len(all_led_errors)} error(s)"
        typer.echo(f"LED Control: {led_status}")
        typer.echo(f"Colors Tested: {len(all_colors)} colors")
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

        typer.echo("✅ Test complete")

        # Flash RGB pattern at end (3 cycles)
        typer.echo("")
        typer.echo("Flashing RGB pattern (3 cycles)...")
        try:
            import time

            from muteme_btn.hid.device import LEDColor

            rgb_colors = [LEDColor.RED, LEDColor.GREEN, LEDColor.BLUE]
            for _ in range(3):
                for color in rgb_colors:
                    device.set_led_color(
                        color, use_feature_report=False, report_format="report_id_0"
                    )
                    time.sleep(0.08)  # Faster: 80ms per color
                    device.set_led_color(
                        LEDColor.NOCOLOR, use_feature_report=False, report_format="report_id_0"
                    )
                    time.sleep(0.02)  # Faster: 20ms off between colors
            typer.echo("✅ End pattern complete")
        except Exception as e:
            typer.echo(f"⚠️  Failed to flash end pattern: {e}")

        # Cleanup - turn LED off
        typer.echo("")
        typer.echo("Turning LED off...")
        try:
            from muteme_btn.hid.device import LEDColor

            device.set_led_color(
                LEDColor.NOCOLOR, use_feature_report=False, report_format="report_id_0"
            )
            typer.echo("✅ LED turned off")
        except Exception as e:
            typer.echo(f"⚠️  Failed to turn LED off: {e}")

        # Cleanup
        device.disconnect()

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
