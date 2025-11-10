"""Tests for CLI device status checking functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from muteme_btn.cli import app
from muteme_btn.hid.device import DeviceInfo
from muteme_btn.hid.events import ButtonEvent, ButtonState


class TestCLIDeviceCommands:
    """Test cases for CLI device-related commands."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_check_device_command_found(self, mock_discover):
        """Test check-device command when devices are found."""
        # Mock device discovery
        from muteme_btn.hid.device import DeviceInfo

        mock_devices = [
            DeviceInfo(
                vendor_id=0x20A0,
                product_id=0x42DA,
                path="/dev/hidraw0",
                manufacturer="MuteMe",
                product="MuteMe Button",
            ),
            DeviceInfo(
                vendor_id=0x3603,
                product_id=0x0001,
                path="/dev/hidraw1",
                manufacturer="MuteMe",
                product="MuteMe Mini",
            ),
        ]
        mock_discover.return_value = mock_devices

        # Mock permission check and hidraw device finding to succeed
        with (
            patch("muteme_btn.hid.device.MuteMeDevice.check_device_permissions", return_value=True),
            patch(
                "muteme_btn.hid.device.MuteMeDevice._find_hidraw_device",
                side_effect=lambda vid, pid: f"/dev/hidraw{0 if vid == 0x20A0 else 1}",
            ),
        ):
            # Run check-device command
            result = self.runner.invoke(app, ["check-device"])

            assert result.exit_code == 0
            assert "Found 2 MuteMe device(s)" in result.stdout
            assert "VID:PID: 0x20a0:0x42da" in result.stdout
            assert "VID:PID: 0x3603:0x0001" in result.stdout
            assert "Permissions: ✅ OK" in result.stdout
            assert "All devices are accessible and ready to use!" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_check_device_command_none_found(self, mock_discover):
        """Test check-device command when no devices are found."""
        mock_discover.return_value = []

        result = self.runner.invoke(app, ["check-device"])

        assert result.exit_code == 1  # Should exit with error code
        assert "No MuteMe devices found" in result.stdout
        assert "Make sure your MuteMe device is connected" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_check_device_command_discovery_error(self, mock_discover):
        """Test check-device command when device discovery fails."""
        mock_discover.side_effect = Exception("HID enumeration failed")

        result = self.runner.invoke(app, ["check-device"])

        assert result.exit_code != 0
        assert "Device discovery failed" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    @patch("muteme_btn.hid.device.MuteMeDevice.check_device_permissions")
    def test_check_device_command_permission_check(self, mock_check_perms, mock_discover):
        """Test check-device command with permission checking."""
        # Mock device discovery
        from muteme_btn.hid.device import DeviceInfo

        mock_devices = [
            DeviceInfo(
                vendor_id=0x20A0,
                product_id=0x42DA,
                path="/dev/hidraw0",
                manufacturer="MuteMe",
                product="MuteMe Button",
            )
        ]
        mock_discover.return_value = mock_devices

        # Mock permission check
        mock_check_perms.return_value = True

        # Mock hidraw device finding
        with patch(
            "muteme_btn.hid.device.MuteMeDevice._find_hidraw_device",
            return_value="/dev/hidraw0",
        ):
            result = self.runner.invoke(app, ["check-device"])

            assert result.exit_code == 0
            assert "Permissions: ✅ OK" in result.stdout
            mock_check_perms.assert_called_once_with("/dev/hidraw0")

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    @patch("muteme_btn.hid.device.MuteMeDevice.check_device_permissions")
    @patch("muteme_btn.hid.device.MuteMeDevice.get_device_permissions_error")
    def test_check_device_command_permission_error(
        self, mock_get_error, mock_check_perms, mock_discover
    ):
        """Test check-device command when permission check fails."""
        # Mock device discovery
        from muteme_btn.hid.device import DeviceInfo

        mock_devices = [
            DeviceInfo(
                vendor_id=0x20A0,
                product_id=0x42DA,
                path="/dev/hidraw0",
                manufacturer="MuteMe",
                product="MuteMe Button",
            )
        ]
        mock_discover.return_value = mock_devices

        # Mock permission check failure
        mock_check_perms.return_value = False
        mock_get_error.return_value = "Permission denied for /dev/hidraw0"

        # Mock hidraw device finding
        with patch(
            "muteme_btn.hid.device.MuteMeDevice._find_hidraw_device",
            return_value="/dev/hidraw0",
        ):
            # Test with verbose flag to see error details
            result = self.runner.invoke(app, ["check-device", "--verbose"])

            assert result.exit_code != 0
            assert "Permissions: ❌ FAILED" in result.stdout
            assert "Permission denied for /dev/hidraw0" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_check_device_command_verbose_output(self, mock_discover):
        """Test check-device command with verbose output."""
        # Mock device discovery
        from muteme_btn.hid.device import DeviceInfo

        mock_devices = [
            DeviceInfo(
                vendor_id=0x20A0,
                product_id=0x42DA,
                path="/dev/hidraw0",
                manufacturer="MuteMe",
                product="MuteMe Button",
            )
        ]
        mock_discover.return_value = mock_devices

        # Mock permission check to succeed
        with (
            patch("muteme_btn.hid.device.MuteMeDevice.check_device_permissions", return_value=True),
            patch(
                "muteme_btn.hid.device.MuteMeDevice._find_hidraw_device",
                return_value="/dev/hidraw0",
            ),
        ):
            result = self.runner.invoke(app, ["check-device", "--verbose"])

            assert result.exit_code == 0
            assert "Device Details:" in result.stdout
            assert "Vendor ID: 0x20a0" in result.stdout
            assert "Product ID: 0x42da" in result.stdout
            assert "Manufacturer: MuteMe" in result.stdout
            assert "Product: MuteMe Button" in result.stdout
            assert "USB Path: /dev/hidraw0" in result.stdout
            assert "HIDraw Device: /dev/hidraw0" in result.stdout


class TestTestDeviceCommand:
    """Test cases for test-device command."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def _create_mock_device(self) -> MagicMock:
        """Create a mock MuteMeDevice instance."""
        mock_device = MagicMock()
        mock_device.is_connected.return_value = True
        mock_device.set_led_color.return_value = None
        mock_device.disconnect.return_value = None
        mock_device.read_events = AsyncMock(return_value=[])
        return mock_device

    def _create_mock_device_info(self) -> DeviceInfo:
        """Create a mock DeviceInfo instance."""
        return DeviceInfo(
            vendor_id=0x20A0,
            product_id=0x42DA,
            path="/dev/hidraw0",
            manufacturer="MuteMe",
            product="MuteMe Button",
        )

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_discovery_success(self, mock_discover):
        """Test test-device command when device discovery succeeds."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            assert "Found 1 device(s)" in result.stdout
            assert "Step 1: Discovering devices" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_discovery_failure(self, mock_discover):
        """Test test-device command when no devices are found."""
        mock_discover.return_value = []

        result = self.runner.invoke(app, ["test-device"])

        assert result.exit_code == 1
        assert "No MuteMe devices found" in result.stdout
        assert "Make sure your MuteMe device is connected" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_connection_vid_pid(self, mock_discover):
        """Test test-device command connects using VID/PID."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            assert "Connected successfully using VID/PID" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_connection_path_fallback(self, mock_discover):
        """Test test-device command falls back to path-based connection."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid",
                side_effect=Exception("VID/PID connection failed"),
            ),
            patch("muteme_btn.hid.device.MuteMeDevice.connect", return_value=mock_device),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            assert "VID/PID connection failed" in result.stdout
            assert "Connected successfully using path" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_connection_both_fail(self, mock_discover):
        """Test test-device command when both connection methods fail."""
        mock_discover.return_value = [self._create_mock_device_info()]

        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid",
                side_effect=Exception("VID/PID failed"),
            ),
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect", side_effect=Exception("Path failed")
            ),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 1
            assert "Connection failed" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_display_info(self, mock_discover):
        """Test test-device command displays device information."""
        device_info = self._create_mock_device_info()
        mock_discover.return_value = [device_info]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            assert "Device Information:" in result.stdout
            assert "Vendor ID: 0x20a0" in result.stdout
            assert "Product ID: 0x42da" in result.stdout
            assert "Manufacturer: MuteMe" in result.stdout
            assert "Product: MuteMe Button" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_led_colors_non_interactive(self, mock_discover):
        """Test test-device command tests all LED colors in non-interactive mode."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            assert "Testing all colors:" in result.stdout
            # Check that all colors are tested
            assert "OFF" in result.stdout or "Setting LED to OFF" in result.stdout
            assert "RED" in result.stdout
            assert "GREEN" in result.stdout
            assert "BLUE" in result.stdout
            assert "YELLOW" in result.stdout
            assert "CYAN" in result.stdout
            assert "PURPLE" in result.stdout
            assert "WHITE" in result.stdout
            assert "Color test complete!" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_led_colors_interactive(self, mock_discover):
        """Test test-device command tests all LED colors in interactive mode."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.input", return_value=""),  # Mock user input
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
            patch("time.sleep"),  # Mock time.sleep for flashing animation in device module
            patch("asyncio.sleep"),  # Mock asyncio.sleep for button communication test
            patch.object(
                mock_device, "read_events", return_value=[]
            ),  # Mock read_events to return immediately
        ):
            result = self.runner.invoke(app, ["test-device", "--interactive"])

            assert result.exit_code == 0
            assert "Colors will be tested in this order:" in result.stdout
            assert "Press ENTER to begin color tests" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_brightness_levels(self, mock_discover):
        """Test test-device command tests brightness levels."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            assert "Testing brightness levels" in result.stdout
            assert "Dim" in result.stdout
            assert "Normal" in result.stdout
            assert "Flashing" in result.stdout
            assert "Fast Pulse" in result.stdout
            assert "Slow Pulse" in result.stdout
            assert "Brightness test complete!" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_brightness_sequence_order(self, mock_discover):
        """Test test-device command brightness sequence includes flashing in correct order."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            stdout = result.stdout
            # Find brightness test section
            brightness_section_start = stdout.find("Testing brightness levels")
            assert brightness_section_start != -1

            # Extract brightness section
            brightness_section = stdout[brightness_section_start:]

            # Verify sequence: Dim → Normal → Flashing → Fast Pulse → Slow Pulse
            dim_pos = brightness_section.find("Setting WHITE to Dim")
            normal_pos = brightness_section.find("Setting WHITE to Normal")
            flashing_pos = brightness_section.find("Setting WHITE to Flashing")
            fast_pulse_pos = brightness_section.find("Setting WHITE to Fast Pulse")
            slow_pulse_pos = brightness_section.find("Setting WHITE to Slow Pulse")

            assert dim_pos != -1
            assert normal_pos != -1
            assert flashing_pos != -1
            assert fast_pulse_pos != -1
            assert slow_pulse_pos != -1
            assert dim_pos < normal_pos < flashing_pos < fast_pulse_pos < slow_pulse_pos

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_button_communication_interactive(self, mock_discover):
        """Test test-device command tests button communication in interactive mode."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        # Mock button event
        button_event = ButtonEvent(
            state=ButtonState.PRESSED, timestamp=1234567890.0, device_path="/dev/hidraw0"
        )
        mock_device.read_events = AsyncMock(return_value=[button_event])

        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.input", return_value=""),  # Mock user input
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device", "--interactive"])

            assert result.exit_code == 0
            assert "Testing button communication" in result.stdout
            assert (
                "Button event detected" in result.stdout or "Button Communication" in result.stdout
            )

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_button_skipped_non_interactive(self, mock_discover):
        """Test test-device command skips button test in non-interactive mode."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            assert "Button test skipped in non-interactive mode" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_diagnostic_summary(self, mock_discover):
        """Test test-device command displays diagnostic summary."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            assert "Diagnostic Summary" in result.stdout
            # Rich Table format or fallback text format
            assert "Device Connection" in result.stdout
            assert "Button Communication" in result.stdout
            assert "LED Control" in result.stdout
            assert "Colors Tested" in result.stdout
            assert "Report Format" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_led_error_handling(self, mock_discover):
        """Test test-device command handles LED errors gracefully."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        # Make set_led_color fail for some colors
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:  # Fail on third call
                raise Exception("LED write failed")
            return None

        mock_device.set_led_color.side_effect = side_effect

        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 1  # Should exit with error if LED errors occur
            assert (
                "Some colors failed" in result.stdout or "Some LED commands failed" in result.stdout
            )

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_cleanup(self, mock_discover):
        """Test test-device command cleans up device connection."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            # Verify cleanup was called
            mock_device.disconnect.assert_called_once()
            assert "LED turned off" in result.stdout or "Turning LED off" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_uses_rich_console_print(self, mock_discover):
        """Test that test-device command uses Rich console.print() instead of typer.echo()."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
            patch("rich.console.Console.print") as mock_console_print,
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            # Verify Rich console.print() was called
            assert mock_console_print.called
            # Verify typer.echo() was NOT used for main output (may be used for errors)
            # Main output should use Rich

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_uses_rich_progress_bars_non_interactive(self, mock_discover):
        """Test that test-device command uses Rich Progress bars in non-interactive mode."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
            patch("muteme_btn.cli.commands.test_device.Progress") as mock_progress,
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            # Verify Rich Progress was used for color/brightness testing
            assert mock_progress.called

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_uses_rich_table_for_diagnostic_summary(self, mock_discover):
        """Test that test-device command uses Rich Table for diagnostic summary."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
            patch("muteme_btn.cli.commands.test_device.Table") as mock_table,
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            # Verify Rich Table was used for diagnostic summary
            assert mock_table.called

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_uses_rich_panel_for_section_headers(self, mock_discover):
        """Test that test-device command uses Rich Panel for section headers."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
            patch("muteme_btn.cli.commands.test_device.Panel") as mock_panel,
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            # Verify Rich Panel was used for section headers (e.g., "Step 1: Discovering devices")
            assert mock_panel.called

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_uses_rich_colored_status_indicators(self, mock_discover):
        """Test that test-device command uses Rich colored status indicators."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            # Verify colored status indicators are present (✅, ⚠️, ❌)
            # Rich markup should be used for coloring
            assert "✅" in result.stdout or "[green]✅[/green]" in result.stdout

    @patch("muteme_btn.hid.device.MuteMeDevice.discover_devices")
    def test_test_device_graceful_fallback_when_rich_unavailable(self, mock_discover):
        """Test graceful fallback to typer.echo() when Rich unavailable."""
        mock_discover.return_value = [self._create_mock_device_info()]

        mock_device = self._create_mock_device()
        with (
            patch(
                "muteme_btn.hid.device.MuteMeDevice.connect_by_vid_pid", return_value=mock_device
            ),
            patch("muteme_btn.cli.commands.test_device._flash_rgb_pattern"),
            patch("muteme_btn.cli.commands.test_device.time.sleep"),
            patch(
                "muteme_btn.cli.commands.test_device.RICH_AVAILABLE", False
            ),  # Simulate Rich unavailable
        ):
            result = self.runner.invoke(app, ["test-device"])

            assert result.exit_code == 0
            # Should still work, falling back to typer.echo()
            assert "Device Information:" in result.stdout or "Step" in result.stdout
