"""Tests for HID device discovery and connection logic."""

import io
import os
from unittest.mock import Mock, patch

import pytest

from muteme_btn.hid.device import DeviceError, DeviceInfo, LEDColor, MuteMeDevice


class TestLEDColor:
    """Test cases for LEDColor enum."""

    def test_led_color_values(self):
        """Test LED color enum values."""
        assert LEDColor.NOCOLOR.value == 0x00
        assert LEDColor.RED.value == 0x01
        assert LEDColor.GREEN.value == 0x02
        assert LEDColor.YELLOW.value == 0x03  # Swapped: was BLUE
        assert LEDColor.BLUE.value == 0x04  # Swapped: was YELLOW
        assert LEDColor.PURPLE.value == 0x05  # Swapped: was CYAN
        assert LEDColor.CYAN.value == 0x06  # Swapped: was PURPLE
        assert LEDColor.WHITE.value == 0x07

    def test_led_color_from_name(self):
        """Test creating LEDColor from string name."""
        assert LEDColor.from_name("red") == LEDColor.RED
        assert LEDColor.from_name("green") == LEDColor.GREEN
        assert LEDColor.from_name("nocolor") == LEDColor.NOCOLOR
        assert LEDColor.from_name("nocolor") == LEDColor.NOCOLOR

    def test_led_color_from_name_case_insensitive(self):
        """Test LEDColor from name is case insensitive."""
        assert LEDColor.from_name("RED") == LEDColor.RED
        assert LEDColor.from_name("Green") == LEDColor.GREEN
        assert LEDColor.from_name("NoColor") == LEDColor.NOCOLOR

    def test_led_color_from_name_invalid(self):
        """Test LEDColor from invalid name raises error."""
        with pytest.raises(ValueError, match="Invalid LED color"):
            LEDColor.from_name("invalid")


class TestMuteMeDevice:
    """Test cases for MuteMeDevice class."""

    def test_device_info_creation(self):
        """Test DeviceInfo data class creation."""
        device_info = DeviceInfo(
            vendor_id=0x20A0,
            product_id=0x42DA,
            path="/dev/hidraw0",
            manufacturer="MuteMe",
            product="MuteMe Button",
        )

        assert device_info.vendor_id == 0x20A0
        assert device_info.product_id == 0x42DA
        assert device_info.path == "/dev/hidraw0"
        assert device_info.manufacturer == "MuteMe"
        assert device_info.product == "MuteMe Button"

    @patch("hid.enumerate")
    def test_discover_muteme_devices_found(self, mock_enumerate):
        """Test successful device discovery."""
        # Mock device list from hidapi
        mock_devices = [
            {
                "vendor_id": 0x20A0,
                "product_id": 0x42DA,
                "path": b"/dev/hidraw0",
                "manufacturer_string": "MuteMe",
                "product_string": "MuteMe Button",
            }
        ]
        mock_enumerate.return_value = mock_devices

        devices = MuteMeDevice.discover_devices()

        assert len(devices) == 1
        assert devices[0].vendor_id == 0x20A0
        assert devices[0].product_id == 0x42DA
        assert devices[0].path == "/dev/hidraw0"

    @patch("hid.enumerate")
    def test_discover_muteme_devices_multiple_found(self, mock_enumerate):
        """Test discovery of multiple MuteMe devices."""
        mock_devices = [
            {
                "vendor_id": 0x20A0,
                "product_id": 0x42DA,
                "path": b"/dev/hidraw0",
                "manufacturer_string": "MuteMe",
                "product_string": "MuteMe Button",
            },
            {
                "vendor_id": 0x20A0,
                "product_id": 0x42DB,
                "path": b"/dev/hidraw1",
                "manufacturer_string": "MuteMe",
                "product_string": "MuteMe Button",
            },
        ]
        mock_enumerate.return_value = mock_devices

        devices = MuteMeDevice.discover_devices()

        assert len(devices) == 2
        assert devices[0].product_id == 0x42DA
        assert devices[1].product_id == 0x42DB

    @patch("hid.enumerate")
    def test_discover_muteme_devices_none_found(self, mock_enumerate):
        """Test no MuteMe devices found."""
        mock_devices = [
            {
                "vendor_id": 0x1234,
                "product_id": 0x5678,
                "path": b"/dev/hidraw2",
                "manufacturer_string": "Other",
                "product_string": "Other Device",
            }
        ]
        mock_enumerate.return_value = mock_devices

        devices = MuteMeDevice.discover_devices()

        assert len(devices) == 0

    @patch("hid.enumerate")
    def test_discover_muteme_devices_with_minis(self, mock_enumerate):
        """Test discovery includes MuteMe Mini variants."""
        mock_devices = [
            {
                "vendor_id": 0x3603,
                "product_id": 0x0001,
                "path": b"/dev/hidraw2",
                "manufacturer_string": "MuteMe",
                "product_string": "MuteMe Mini",
            }
        ]
        mock_enumerate.return_value = mock_devices

        devices = MuteMeDevice.discover_devices()

        assert len(devices) == 1
        assert devices[0].vendor_id == 0x3603
        assert devices[0].product_id == 0x0001

    @patch("hid.enumerate")
    @patch("hid.device")
    def test_connect_to_device_success(self, mock_device, mock_enumerate):
        """Test successful device connection."""
        # Mock device discovery
        mock_devices = [
            {
                "vendor_id": 0x20A0,
                "product_id": 0x42DA,
                "path": b"/dev/hidraw0",
                "manufacturer_string": "MuteMe",
                "product_string": "MuteMe Button",
            }
        ]
        mock_enumerate.return_value = mock_devices

        # Mock hid.device()
        mock_hid_device = Mock()
        mock_device.return_value = mock_hid_device

        # Connect to device
        device = MuteMeDevice.connect("/dev/hidraw0")

        assert device is not None
        mock_hid_device.open_path.assert_called_once_with(b"/dev/hidraw0")

    @patch("hid.device")
    def test_connect_to_device_failure(self, mock_device):
        """Test device connection failure."""
        mock_hid_device = Mock()
        mock_device.return_value = mock_hid_device
        mock_hid_device.open_path.side_effect = Exception("Permission denied")

        with pytest.raises(DeviceError, match="Failed to connect"):
            MuteMeDevice.connect("/dev/hidraw0")

    @patch("muteme_btn.hid.device.logger")
    @patch("hid.device")
    def test_connect_open_failed_logs_warning(self, mock_device, mock_logger):
        """Test expected path open failures are logged as warnings."""
        mock_hid_device = Mock()
        mock_device.return_value = mock_hid_device
        mock_hid_device.open_path.side_effect = OSError("open failed")

        with pytest.raises(DeviceError, match="Failed to connect"):
            MuteMeDevice.connect("1-1.4.2.4.2:1.0")

        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()

    @patch("muteme_btn.hid.device.logger")
    @patch("hid.device")
    def test_connect_by_vid_pid_open_failed_logs_warning(self, mock_device, mock_logger):
        """Test expected VID/PID open failures are logged as warnings."""
        mock_hid_device = Mock()
        mock_device.return_value = mock_hid_device
        mock_hid_device.open.side_effect = OSError("open failed")

        with pytest.raises(DeviceError, match="Failed to connect"):
            MuteMeDevice.connect_by_vid_pid(0x20A0, 0x42DA)

        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()

    def test_device_disconnect(self):
        """Test device disconnection."""
        mock_hid_device = Mock()
        device = MuteMeDevice(mock_hid_device)

        device.disconnect()

        mock_hid_device.close.assert_called_once()

    def test_is_connected_true(self):
        """Test is_connected returns True when device is open."""
        mock_hid_device = Mock()
        mock_hid_device.open_path.return_value = None
        device = MuteMeDevice(mock_hid_device)

        # Mock the device to appear connected
        device._device = mock_hid_device

        assert device.is_connected() is True

    def test_is_connected_false(self):
        """Test is_connected returns False when device is None."""
        device = MuteMeDevice(None)

        assert device.is_connected() is False

    def test_get_device_info(self):
        """Test getting device information."""
        mock_hid_device = Mock()
        device_info = DeviceInfo(
            vendor_id=0x20A0,
            product_id=0x42DA,
            path="/dev/hidraw0",
            manufacturer="MuteMe",
            product="MuteMe Button",
        )
        device = MuteMeDevice(mock_hid_device, device_info)

        info = device.get_device_info()
        assert info is not None

        assert info.vendor_id == 0x20A0
        assert info.product_id == 0x42DA
        assert info.path == "/dev/hidraw0"

    def test_set_led_color_success(self):
        """Test successful LED color setting."""
        mock_hid_device = Mock()
        device = MuteMeDevice(mock_hid_device)

        device.set_led_color(LEDColor.RED)

        # Verify the correct HID report was sent (default format is report_id_0: [0x00, color])
        mock_hid_device.write.assert_called_once_with(bytes([0x00, 0x01]))  # Report ID 0, Color RED

    def test_set_led_color_green(self):
        """Test setting LED to green."""
        mock_hid_device = Mock()
        device = MuteMeDevice(mock_hid_device)

        device.set_led_color(LEDColor.GREEN)

        mock_hid_device.write.assert_called_once_with(
            bytes([0x00, 0x02])
        )  # Report ID 0, Color GREEN

    def test_set_led_color_no_color(self):
        """Test setting LED to no color."""
        mock_hid_device = Mock()
        device = MuteMeDevice(mock_hid_device)

        device.set_led_color(LEDColor.NOCOLOR)

        mock_hid_device.write.assert_called_once_with(
            bytes([0x00, 0x00])
        )  # Report ID 0, Color NOCOLOR

    def test_set_led_color_not_connected(self):
        """Test setting LED color when device not connected."""
        device = MuteMeDevice(None)

        with pytest.raises(DeviceError, match="Device not connected"):
            device.set_led_color(LEDColor.RED)

    def test_set_led_color_write_failure(self):
        """Test LED color setting when write fails."""
        mock_hid_device = Mock()
        mock_hid_device.write.side_effect = Exception("Write failed")
        device = MuteMeDevice(mock_hid_device)

        with pytest.raises(DeviceError, match="LED control failed"):
            device.set_led_color(LEDColor.RED)

    def test_set_led_color_by_name(self):
        """Test setting LED color by name."""
        mock_hid_device = Mock()
        device = MuteMeDevice(mock_hid_device)

        device.set_led_color_by_name("blue")

        mock_hid_device.write.assert_called_once_with(
            bytes([0x00, 0x04])
        )  # Report ID 0, Color BLUE (now 0x04, was 0x03)

    def test_set_led_color_by_name_invalid(self):
        """Test setting LED color by invalid name."""
        device = MuteMeDevice(Mock())

        with pytest.raises(ValueError, match="Invalid LED color"):
            device.set_led_color_by_name("invalid")

    def test_read_failure_disconnects_device(self):
        """Test read failure closes and disconnects device handle."""
        mock_hid_device = Mock()
        mock_hid_device.read.side_effect = Exception("read error")
        device = MuteMeDevice(mock_hid_device)

        with pytest.raises(DeviceError, match="Device read failed"):
            device.read(64)

        mock_hid_device.close.assert_called_once()
        assert device.is_connected() is False

    @patch("time.sleep")
    def test_set_led_color_flashing_brightness(self, mock_sleep):
        """Test setting LED color with flashing brightness."""
        mock_hid_device = Mock()
        device = MuteMeDevice(mock_hid_device)

        device.set_led_color(LEDColor.RED, brightness="flashing")

        # Flashing uses software-side animation (rapid on/off cycles)
        # Should have multiple write calls: 20 cycles * 2 (on/off) + 1 final on = 41 calls
        assert mock_hid_device.write.call_count >= 20  # At least 20 cycles
        # Verify it alternates between RED and NOCOLOR
        calls = mock_hid_device.write.call_args_list
        assert bytes([0x00, 0x01]) in [call[0][0] for call in calls]  # RED
        assert bytes([0x00, 0x00]) in [call[0][0] for call in calls]  # NOCOLOR
        # Final call should be RED
        assert calls[-1][0][0] == bytes([0x00, 0x01])
        # Verify sleep was called (20 cycles * 2 sleeps per cycle = 40 calls)
        assert mock_sleep.call_count == 40

    @patch("time.sleep")
    def test_set_led_color_flashing_brightness_white(self, mock_sleep):
        """Test setting LED color to white with flashing brightness."""
        mock_hid_device = Mock()
        device = MuteMeDevice(mock_hid_device)

        device.set_led_color(LEDColor.WHITE, brightness="flashing")

        # Flashing uses software-side animation (rapid on/off cycles)
        # Should have multiple write calls: 20 cycles * 2 (on/off) + 1 final on = 41 calls
        assert mock_hid_device.write.call_count >= 20  # At least 20 cycles
        # Verify it alternates between WHITE and NOCOLOR
        calls = mock_hid_device.write.call_args_list
        assert bytes([0x00, 0x07]) in [call[0][0] for call in calls]  # WHITE
        assert bytes([0x00, 0x00]) in [call[0][0] for call in calls]  # NOCOLOR
        # Final call should be WHITE
        assert calls[-1][0][0] == bytes([0x00, 0x07])
        # Verify sleep was called (20 cycles * 2 sleeps per cycle = 40 calls)
        assert mock_sleep.call_count == 40

    def test_check_device_permissions_success(self):
        """Test successful device permission check."""
        with patch("os.access") as mock_access:
            mock_access.return_value = True

            result = MuteMeDevice.check_device_permissions("/dev/hidraw0")

            assert result is True
            mock_access.assert_called_once_with("/dev/hidraw0", os.R_OK | os.W_OK)

    def test_check_device_permissions_failure(self):
        """Test device permission check failure."""
        with patch("os.access") as mock_access:
            mock_access.return_value = False

            result = MuteMeDevice.check_device_permissions("/dev/hidraw0")

            assert result is False

    def test_check_device_permissions_exception(self):
        """Test device permission check with exception."""
        with patch("os.access") as mock_access:
            mock_access.side_effect = OSError("Device not found")

            result = MuteMeDevice.check_device_permissions("/dev/hidraw0")

            assert result is False

    def test_get_device_permissions_error_message(self):
        """Test getting detailed permission error message."""
        with patch("os.access") as mock_access:
            mock_access.return_value = False

            with patch("os.stat") as mock_stat:
                mock_stat.return_value.st_mode = 0o444
                with patch("pwd.getpwuid") as mock_pwuid:
                    mock_pwuid.return_value.pw_name = "user"
                    with patch("grp.getgrgid") as mock_grgid:
                        mock_grgid.return_value.gr_name = "plugdev"

                        error_msg = MuteMeDevice.get_device_permissions_error("/dev/hidraw0")

                        assert "/dev/hidraw0" in error_msg
                        assert "permissions" in error_msg.lower()
                        assert "user:plugdev" in error_msg
                        assert "just install-udev" in error_msg
                        assert 'TAG+="uaccess"' in error_msg
                        assert "chmod 666" not in error_msg

    def test_find_usb_device_node_success(self):
        """Test finding USB device node for matching VID/PID."""
        sysfs_root = "/sys/bus/usb/devices"
        files = {
            f"{sysfs_root}/1-1/idVendor": "20a0\n",
            f"{sysfs_root}/1-1/idProduct": "42da\n",
            f"{sysfs_root}/1-1/busnum": "3\n",
            f"{sysfs_root}/1-1/devnum": "12\n",
        }

        def fake_open(path, *args, **kwargs):
            if path in files:
                return io.StringIO(files[path])
            raise OSError("missing file")

        with (
            patch("os.listdir", return_value=["1-1"]),
            patch("os.path.isdir", return_value=True),
            patch("builtins.open", side_effect=fake_open),
        ):
            result = MuteMeDevice._find_usb_device_node(0x20A0, 0x42DA)

        assert result == "/dev/bus/usb/003/012"

    def test_find_usb_device_node_skips_non_matching_devices(self):
        """Test USB node finder skips non-matching devices and finds next match."""
        sysfs_root = "/sys/bus/usb/devices"
        files = {
            f"{sysfs_root}/1-1/idVendor": "1234\n",
            f"{sysfs_root}/1-1/idProduct": "5678\n",
            f"{sysfs_root}/2-1/idVendor": "20a0\n",
            f"{sysfs_root}/2-1/idProduct": "42db\n",
            f"{sysfs_root}/2-1/busnum": "1\n",
            f"{sysfs_root}/2-1/devnum": "5\n",
        }

        def fake_open(path, *args, **kwargs):
            if path in files:
                return io.StringIO(files[path])
            raise OSError("missing file")

        with (
            patch("os.listdir", return_value=["1-1", "2-1"]),
            patch("os.path.isdir", return_value=True),
            patch("builtins.open", side_effect=fake_open),
        ):
            result = MuteMeDevice._find_usb_device_node(0x20A0, 0x42DB)

        assert result == "/dev/bus/usb/001/005"

    def test_find_usb_device_node_ignores_malformed_hex_ids(self):
        """Test USB node finder ignores malformed VID/PID values."""
        sysfs_root = "/sys/bus/usb/devices"
        files = {
            f"{sysfs_root}/1-1/idVendor": "nothex\n",
            f"{sysfs_root}/1-1/idProduct": "42da\n",
        }

        def fake_open(path, *args, **kwargs):
            if path in files:
                return io.StringIO(files[path])
            raise OSError("missing file")

        with (
            patch("os.listdir", return_value=["1-1"]),
            patch("os.path.isdir", return_value=True),
            patch("builtins.open", side_effect=fake_open),
        ):
            result = MuteMeDevice._find_usb_device_node(0x20A0, 0x42DA)

        assert result is None

    def test_find_usb_device_node_missing_bus_or_device_numbers(self):
        """Test USB node finder handles missing busnum/devnum files."""
        sysfs_root = "/sys/bus/usb/devices"
        files = {
            f"{sysfs_root}/1-1/idVendor": "20a0\n",
            f"{sysfs_root}/1-1/idProduct": "42da\n",
        }

        def fake_open(path, *args, **kwargs):
            if path in files:
                return io.StringIO(files[path])
            raise OSError("missing file")

        with (
            patch("os.listdir", return_value=["1-1"]),
            patch("os.path.isdir", return_value=True),
            patch("builtins.open", side_effect=fake_open),
        ):
            result = MuteMeDevice._find_usb_device_node(0x20A0, 0x42DA)

        assert result is None

    def test_find_usb_device_node_ignores_malformed_bus_or_device_numbers(self):
        """Test USB node finder handles malformed busnum/devnum values."""
        sysfs_root = "/sys/bus/usb/devices"
        files = {
            f"{sysfs_root}/1-1/idVendor": "20a0\n",
            f"{sysfs_root}/1-1/idProduct": "42da\n",
            f"{sysfs_root}/1-1/busnum": "not-a-number\n",
            f"{sysfs_root}/1-1/devnum": "12\n",
        }

        def fake_open(path, *args, **kwargs):
            if path in files:
                return io.StringIO(files[path])
            raise OSError("missing file")

        with (
            patch("os.listdir", return_value=["1-1"]),
            patch("os.path.isdir", return_value=True),
            patch("builtins.open", side_effect=fake_open),
        ):
            result = MuteMeDevice._find_usb_device_node(0x20A0, 0x42DA)

        assert result is None

    def test_find_usb_device_node_returns_none_when_sysfs_unreadable(self):
        """Test USB node finder returns None when sysfs cannot be listed."""
        with patch("os.listdir", side_effect=OSError("permission denied")):
            result = MuteMeDevice._find_usb_device_node(0x20A0, 0x42DA)

        assert result is None


class TestMuteMeButtonEdgeNormalization:
    """Tests for normalizing noisy MuteMe raw reports into stable button edges."""

    @pytest.mark.asyncio
    async def test_repeated_press_reports_emit_single_press_edge(self):
        """A long hold should not emit repeated logical press events."""
        mock_hid_device = Mock()
        mock_hid_device.read.side_effect = [
            [0x00, 0x00, 0x00, 0x01],
            [0x00, 0x00, 0x00, 0x01],
            [0x00, 0x00, 0x00, 0x01],
        ]
        device = MuteMeDevice(mock_hid_device)

        first = await device.read_events()
        second = await device.read_events()
        third = await device.read_events()

        assert [event.type for event in first] == ["press"]
        assert second == []
        assert third == []

    @pytest.mark.asyncio
    async def test_noisy_release_tail_emits_single_release_edge(self):
        """Release-like packet tails should collapse to one logical release."""
        mock_hid_device = Mock()
        mock_hid_device.read.side_effect = [
            [0x00, 0x00, 0x00, 0x01],
            [0x00, 0x00, 0x00, 0x02],
            [0x00, 0x00, 0x00, 0x00],
            [0x00, 0x00, 0x00, 0x04],
        ]
        device = MuteMeDevice(mock_hid_device)

        press = await device.read_events()
        release = await device.read_events()
        tail_zero = await device.read_events()
        tail_four = await device.read_events()

        assert [event.type for event in press] == ["press"]
        assert [event.type for event in release] == ["release"]
        assert tail_zero == []
        assert tail_four == []

    @pytest.mark.asyncio
    async def test_initial_release_like_packet_is_ignored(self):
        """Startup release-like packets should not produce logical release events."""
        mock_hid_device = Mock()
        mock_hid_device.read.side_effect = [[0x00, 0x00, 0x00, 0x04]]
        device = MuteMeDevice(mock_hid_device)

        events = await device.read_events()

        assert events == []

    @pytest.mark.asyncio
    @patch("muteme_btn.hid.device.logger")
    async def test_duplicate_button_reports_do_not_log_every_poll(self, mock_logger):
        """Duplicate raw reports should be counted without debug log spam every poll."""
        mock_hid_device = Mock()
        mock_hid_device.read.side_effect = [[0x00, 0x00, 0x00, 0x00]] * 3
        device = MuteMeDevice(mock_hid_device)

        assert await device.read_events() == []
        assert await device.read_events() == []
        assert await device.read_events() == []

        assert device.duplicate_report_count == 3
        duplicate_logs = [
            call_args
            for call_args in mock_logger.debug.call_args_list
            if call_args.args and call_args.args[0] == "Ignored duplicate button report"
        ]
        assert duplicate_logs == []

    @pytest.mark.asyncio
    @patch("muteme_btn.hid.device.logger")
    async def test_button_event_log_uses_structured_fields(self, mock_logger):
        """Button-event logs should expose event metadata as structured fields."""
        mock_hid_device = Mock()
        mock_hid_device.read.side_effect = [[0x00, 0x00, 0x00, 0x01]]
        device = MuteMeDevice(mock_hid_device)

        events = await device.read_events()

        assert [event.type for event in events] == ["press"]
        mock_logger.info.assert_called_once_with(
            "Button event detected",
            event_type="press",
            raw_data="00000001",
            button_byte="0x01",
        )
