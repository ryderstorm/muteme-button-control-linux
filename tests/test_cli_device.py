"""Tests for CLI device status checking functionality."""

from unittest.mock import patch
from typer.testing import CliRunner
from muteme_btn.cli import app


class TestCLIDeviceCommands:
    """Test cases for CLI device-related commands."""
    
    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()
    
    @patch('muteme_btn.hid.device.MuteMeDevice.discover_devices')
    def test_check_device_command_found(self, mock_discover):
        """Test check-device command when devices are found."""
        # Mock device discovery
        from muteme_btn.hid.device import DeviceInfo
        mock_devices = [
            DeviceInfo(
                vendor_id=0x20a0,
                product_id=0x42da,
                path="/dev/hidraw0",
                manufacturer="MuteMe",
                product="MuteMe Button"
            ),
            DeviceInfo(
                vendor_id=0x3603,
                product_id=0x0001,
                path="/dev/hidraw1",
                manufacturer="MuteMe",
                product="MuteMe Mini"
            )
        ]
        mock_discover.return_value = mock_devices
        
        # Mock permission check to succeed
        with patch('muteme_btn.hid.device.MuteMeDevice.check_device_permissions', return_value=True):
            # Run check-device command
            result = self.runner.invoke(app, ["check-device"])
            
            assert result.exit_code == 0
            assert "Found 2 MuteMe device(s)" in result.stdout
            assert "VID:PID: 0x20a0:0x42da" in result.stdout
            assert "VID:PID: 0x3603:0x0001" in result.stdout
            assert "Permissions: ✅ OK" in result.stdout
            assert "All devices are accessible and ready to use!" in result.stdout
    
    @patch('muteme_btn.hid.device.MuteMeDevice.discover_devices')
    def test_check_device_command_none_found(self, mock_discover):
        """Test check-device command when no devices are found."""
        mock_discover.return_value = []
        
        result = self.runner.invoke(app, ["check-device"])
        
        assert result.exit_code == 1  # Should exit with error code
        assert "No MuteMe devices found" in result.stdout
        assert "Make sure your MuteMe device is connected" in result.stdout
    
    @patch('muteme_btn.hid.device.MuteMeDevice.discover_devices')
    def test_check_device_command_discovery_error(self, mock_discover):
        """Test check-device command when device discovery fails."""
        mock_discover.side_effect = Exception("HID enumeration failed")
        
        result = self.runner.invoke(app, ["check-device"])
        
        assert result.exit_code != 0
        assert "Device discovery failed" in result.stdout
    
    @patch('muteme_btn.hid.device.MuteMeDevice.discover_devices')
    @patch('muteme_btn.hid.device.MuteMeDevice.check_device_permissions')
    def test_check_device_command_permission_check(self, mock_check_perms, mock_discover):
        """Test check-device command with permission checking."""
        # Mock device discovery
        from muteme_btn.hid.device import DeviceInfo
        mock_devices = [
            DeviceInfo(
                vendor_id=0x20a0,
                product_id=0x42da,
                path="/dev/hidraw0",
                manufacturer="MuteMe",
                product="MuteMe Button"
            )
        ]
        mock_discover.return_value = mock_devices
        
        # Mock permission check
        mock_check_perms.return_value = True
        
        result = self.runner.invoke(app, ["check-device"])
        
        assert result.exit_code == 0
        assert "Permissions: ✅ OK" in result.stdout
        mock_check_perms.assert_called_once_with("/dev/hidraw0")
    
    @patch('muteme_btn.hid.device.MuteMeDevice.discover_devices')
    @patch('muteme_btn.hid.device.MuteMeDevice.check_device_permissions')
    @patch('muteme_btn.hid.device.MuteMeDevice.get_device_permissions_error')
    def test_check_device_command_permission_error(self, mock_get_error, mock_check_perms, mock_discover):
        """Test check-device command when permission check fails."""
        # Mock device discovery
        from muteme_btn.hid.device import DeviceInfo
        mock_devices = [
            DeviceInfo(
                vendor_id=0x20a0,
                product_id=0x42da,
                path="/dev/hidraw0",
                manufacturer="MuteMe",
                product="MuteMe Button"
            )
        ]
        mock_discover.return_value = mock_devices
        
        # Mock permission check failure
        mock_check_perms.return_value = False
        mock_get_error.return_value = "Permission denied for /dev/hidraw0"
        
        # Test with verbose flag to see error details
        result = self.runner.invoke(app, ["check-device", "--verbose"])
        
        assert result.exit_code != 0
        assert "Permissions: ❌ FAILED" in result.stdout
        assert "Permission denied for /dev/hidraw0" in result.stdout
    
    @patch('muteme_btn.hid.device.MuteMeDevice.discover_devices')
    def test_check_device_command_verbose_output(self, mock_discover):
        """Test check-device command with verbose output."""
        # Mock device discovery
        from muteme_btn.hid.device import DeviceInfo
        mock_devices = [
            DeviceInfo(
                vendor_id=0x20a0,
                product_id=0x42da,
                path="/dev/hidraw0",
                manufacturer="MuteMe",
                product="MuteMe Button"
            )
        ]
        mock_discover.return_value = mock_devices
        
        # Mock permission check to succeed
        with patch('muteme_btn.hid.device.MuteMeDevice.check_device_permissions', return_value=True):
            result = self.runner.invoke(app, ["check-device", "--verbose"])
            
            assert result.exit_code == 0
            assert "Device Details:" in result.stdout
            assert "Vendor ID: 0x20a0" in result.stdout
            assert "Product ID: 0x42da" in result.stdout
            assert "Manufacturer: MuteMe" in result.stdout
            assert "Product: MuteMe Button" in result.stdout
            assert "Device Path: /dev/hidraw0" in result.stdout
