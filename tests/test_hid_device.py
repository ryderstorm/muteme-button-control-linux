"""Tests for HID device discovery and connection logic."""

import os
import pytest
from unittest.mock import Mock, patch
from muteme_btn.hid.device import MuteMeDevice, DeviceInfo, DeviceError, LEDColor


class TestLEDColor:
    """Test cases for LEDColor enum."""
    
    def test_led_color_values(self):
        """Test LED color enum values."""
        assert LEDColor.NOCOLOR.value == 0x00
        assert LEDColor.RED.value == 0x01
        assert LEDColor.GREEN.value == 0x02
        assert LEDColor.BLUE.value == 0x03
        assert LEDColor.YELLOW.value == 0x04
        assert LEDColor.CYAN.value == 0x05
        assert LEDColor.PURPLE.value == 0x06
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
            vendor_id=0x20a0,
            product_id=0x42da,
            path="/dev/hidraw0",
            manufacturer="MuteMe",
            product="MuteMe Button"
        )
        
        assert device_info.vendor_id == 0x20a0
        assert device_info.product_id == 0x42da
        assert device_info.path == "/dev/hidraw0"
        assert device_info.manufacturer == "MuteMe"
        assert device_info.product == "MuteMe Button"

    @patch('hid.enumerate')
    def test_discover_muteme_devices_found(self, mock_enumerate):
        """Test successful device discovery."""
        # Mock device list from hidapi
        mock_devices = [
            {
                'vendor_id': 0x20a0,
                'product_id': 0x42da,
                'path': b'/dev/hidraw0',
                'manufacturer_string': 'MuteMe',
                'product_string': 'MuteMe Button'
            }
        ]
        mock_enumerate.return_value = mock_devices
        
        devices = MuteMeDevice.discover_devices()
        
        assert len(devices) == 1
        assert devices[0].vendor_id == 0x20a0
        assert devices[0].product_id == 0x42da
        assert devices[0].path == "/dev/hidraw0"

    @patch('hid.enumerate')
    def test_discover_muteme_devices_multiple_found(self, mock_enumerate):
        """Test discovery of multiple MuteMe devices."""
        mock_devices = [
            {
                'vendor_id': 0x20a0,
                'product_id': 0x42da,
                'path': b'/dev/hidraw0',
                'manufacturer_string': 'MuteMe',
                'product_string': 'MuteMe Button'
            },
            {
                'vendor_id': 0x20a0,
                'product_id': 0x42db,
                'path': b'/dev/hidraw1',
                'manufacturer_string': 'MuteMe',
                'product_string': 'MuteMe Button'
            }
        ]
        mock_enumerate.return_value = mock_devices
        
        devices = MuteMeDevice.discover_devices()
        
        assert len(devices) == 2
        assert devices[0].product_id == 0x42da
        assert devices[1].product_id == 0x42db

    @patch('hid.enumerate')
    def test_discover_muteme_devices_none_found(self, mock_enumerate):
        """Test no MuteMe devices found."""
        mock_devices = [
            {
                'vendor_id': 0x1234,
                'product_id': 0x5678,
                'path': b'/dev/hidraw2',
                'manufacturer_string': 'Other',
                'product_string': 'Other Device'
            }
        ]
        mock_enumerate.return_value = mock_devices
        
        devices = MuteMeDevice.discover_devices()
        
        assert len(devices) == 0

    @patch('hid.enumerate')
    def test_discover_muteme_devices_with_minis(self, mock_enumerate):
        """Test discovery includes MuteMe Mini variants."""
        mock_devices = [
            {
                'vendor_id': 0x3603,
                'product_id': 0x0001,
                'path': b'/dev/hidraw2',
                'manufacturer_string': 'MuteMe',
                'product_string': 'MuteMe Mini'
            }
        ]
        mock_enumerate.return_value = mock_devices
        
        devices = MuteMeDevice.discover_devices()
        
        assert len(devices) == 1
        assert devices[0].vendor_id == 0x3603
        assert devices[0].product_id == 0x0001

    @patch('hid.enumerate')
    @patch('hid.device')
    def test_connect_to_device_success(self, mock_device, mock_enumerate):
        """Test successful device connection."""
        # Mock device discovery
        mock_devices = [
            {
                'vendor_id': 0x20a0,
                'product_id': 0x42da,
                'path': b'/dev/hidraw0',
                'manufacturer_string': 'MuteMe',
                'product_string': 'MuteMe Button'
            }
        ]
        mock_enumerate.return_value = mock_devices
        
        # Mock hid.device()
        mock_hid_device = Mock()
        mock_device.return_value = mock_hid_device
        
        # Connect to device
        device = MuteMeDevice.connect("/dev/hidraw0")
        
        assert device is not None
        mock_hid_device.open_path.assert_called_once_with(b'/dev/hidraw0')

    @patch('hid.device')
    def test_connect_to_device_failure(self, mock_device):
        """Test device connection failure."""
        mock_hid_device = Mock()
        mock_device.return_value = mock_hid_device
        mock_hid_device.open_path.side_effect = Exception("Permission denied")
        
        with pytest.raises(DeviceError, match="Failed to connect"):
            MuteMeDevice.connect("/dev/hidraw0")

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
            vendor_id=0x20a0,
            product_id=0x42da,
            path="/dev/hidraw0",
            manufacturer="MuteMe",
            product="MuteMe Button"
        )
        device = MuteMeDevice(mock_hid_device, device_info)
        
        info = device.get_device_info()
        
        assert info.vendor_id == 0x20a0
        assert info.product_id == 0x42da
        assert info.path == "/dev/hidraw0"

    def test_set_led_color_success(self):
        """Test successful LED color setting."""
        mock_hid_device = Mock()
        device = MuteMeDevice(mock_hid_device)
        
        device.set_led_color(LEDColor.RED)
        
        # Verify the correct HID report was sent
        mock_hid_device.write.assert_called_once_with([0x01, 0x01])  # Report ID 1, Color RED

    def test_set_led_color_green(self):
        """Test setting LED to green."""
        mock_hid_device = Mock()
        device = MuteMeDevice(mock_hid_device)
        
        device.set_led_color(LEDColor.GREEN)
        
        mock_hid_device.write.assert_called_once_with([0x01, 0x02])  # Report ID 1, Color GREEN

    def test_set_led_color_no_color(self):
        """Test setting LED to no color."""
        mock_hid_device = Mock()
        device = MuteMeDevice(mock_hid_device)
        
        device.set_led_color(LEDColor.NOCOLOR)
        
        mock_hid_device.write.assert_called_once_with([0x01, 0x00])  # Report ID 1, Color NOCOLOR

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
        
        mock_hid_device.write.assert_called_once_with([0x01, 0x03])  # Report ID 1, Color BLUE

    def test_set_led_color_by_name_invalid(self):
        """Test setting LED color by invalid name."""
        device = MuteMeDevice(Mock())
        
        with pytest.raises(ValueError, match="Invalid LED color"):
            device.set_led_color_by_name("invalid")

    def test_check_device_permissions_success(self):
        """Test successful device permission check."""
        with patch('os.access') as mock_access:
            mock_access.return_value = True
            
            result = MuteMeDevice.check_device_permissions("/dev/hidraw0")
            
            assert result is True
            mock_access.assert_called_once_with("/dev/hidraw0", os.R_OK | os.W_OK)

    def test_check_device_permissions_failure(self):
        """Test device permission check failure."""
        with patch('os.access') as mock_access:
            mock_access.return_value = False
            
            result = MuteMeDevice.check_device_permissions("/dev/hidraw0")
            
            assert result is False

    def test_check_device_permissions_exception(self):
        """Test device permission check with exception."""
        with patch('os.access') as mock_access:
            mock_access.side_effect = OSError("Device not found")
            
            result = MuteMeDevice.check_device_permissions("/dev/hidraw0")
            
            assert result is False

    def test_get_device_permissions_error_message(self):
        """Test getting detailed permission error message."""
        with patch('os.access') as mock_access:
            mock_access.return_value = False
            
            with patch('os.stat') as mock_stat:
                mock_stat.return_value.st_mode = 0o644
                with patch('pwd.getpwuid') as mock_pwuid:
                    mock_pwuid.return_value.pw_name = "user"
                    with patch('grp.getgrgid') as mock_grgid:
                        mock_grgid.return_value.gr_name = "plugdev"
                        
                        error_msg = MuteMeDevice.get_device_permissions_error("/dev/hidraw0")
                        
                        assert "/dev/hidraw0" in error_msg
                        assert "permissions" in error_msg.lower()
                        assert "user:plugdev" in error_msg
