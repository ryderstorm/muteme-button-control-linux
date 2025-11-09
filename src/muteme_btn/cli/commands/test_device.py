"""Test-device command implementation."""

import asyncio
import sys
import time
from pathlib import Path

import typer

from ...cli import app
from ...hid.device import DeviceInfo, LEDColor, MuteMeDevice
from ...utils.logging import setup_logging
from ..utils.config_loader import load_config
from ..utils.device_helpers import discover_and_connect_device

# LED timing constants (seconds)
LED_COLOR_HOLD_DURATION = 0.3  # Duration to hold each color
LED_COLOR_TRANSITION_DURATION = 0.1  # Duration for transitions/off periods
LED_COLOR_VISIBLE_DURATION = 0.5  # Duration for color testing
LED_BRIGHTNESS_TEST_DURATION = 3.0  # Duration for brightness level tests


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

        typer.echo("🔍 MuteMe Device Communication Test")
        typer.echo("=" * 50)
        typer.echo("")

        # Discover and connect to device
        device, device_info = discover_and_connect_device()

        # Display device information
        _display_device_info(device_info)

        # If color/brightness flags are provided, do quick test only
        if color or brightness:
            if brightness and not color:
                typer.echo("❌ --brightness requires --color to be specified", err=True)
                sys.exit(1)

            # Quick test mode
            typer.echo("Quick Test Mode")
            typer.echo("=" * 50)
            typer.echo("")

            test_color = LEDColor.from_name(color) if color else LEDColor.WHITE
            test_brightness = brightness if brightness else "normal"

            typer.echo(f"Testing: Color={test_color.name}, Brightness={test_brightness}")
            typer.echo("")

            try:
                if test_brightness == "flashing":
                    # Flashing uses software animation - show info first, then animate
                    typer.echo("Starting flashing animation (20 rapid on/off cycles)...")
                    typer.echo("")

                    device.set_led_color(
                        test_color,
                        use_feature_report=False,
                        report_format="report_id_0",
                        brightness=test_brightness,
                    )

                    typer.echo("✅ Flashing animation complete")
                    typer.echo("")
                    typer.echo("Observe the device LED. Press ENTER when done...")
                    if interactive:
                        input()
                    else:
                        time.sleep(2)

                    # Cleanup before returning
                    typer.echo("")
                    typer.echo("Turning LED off...")
                    try:
                        device.set_led_color(
                            LEDColor.NOCOLOR,
                            use_feature_report=False,
                            report_format="report_id_0",
                        )
                        typer.echo("✅ LED turned off")
                    except Exception as e:
                        typer.echo(f"⚠️  Failed to turn LED off: {e}")
                    device.disconnect()
                    typer.echo("✅ Quick test complete")
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

                typer.echo(f"✅ Set LED to {test_color.name} with {test_brightness} brightness")
                offset_val = color_value - test_color.value
                typer.echo(
                    f"   HID report: [0x00, 0x{color_value:02x}] "
                    f"(color=0x{test_color.value:02x}, offset=0x{offset_val:02x})"
                )
                typer.echo("")
                typer.echo("Observe the device LED. Press ENTER when done...")
                if interactive:
                    input()
                else:
                    time.sleep(5)
            except Exception as e:
                typer.echo(f"❌ Failed to set LED: {e}", err=True)
                sys.exit(1)

            # Cleanup
            _cleanup_device(device)
            typer.echo("✅ Quick test complete")
            return

        # Full test suite (existing behavior)

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
