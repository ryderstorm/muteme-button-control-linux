"""Comprehensive mocked HID device tests for CI compatibility."""

from unittest.mock import Mock, patch
import pytest
from muteme_btn.hid.device import MuteMeDevice, DeviceInfo, DeviceError, LEDColor
from muteme_btn.hid.events import ButtonEvent, ButtonState, EventHandler


class TestMockedHIDIntegration:
    """Integration tests with fully mocked HID layer for CI environments."""
    
    @patch('muteme_btn.hid.device.hid.enumerate')
    def test_full_device_discovery_workflow(self, mock_enumerate):
        """Test complete device discovery workflow with mocked devices."""
        # Mock multiple MuteMe devices
        mock_devices = [
            {
                'vendor_id': 0x20a0,
                'product_id': 0x42da,
                'path': b'/dev/hidraw0',
                'manufacturer_string': 'MuteMe',
                'product_string': 'MuteMe Button'
            },
            {
                'vendor_id': 0x3603,
                'product_id': 0x0001,
                'path': b'/dev/hidraw1',
                'manufacturer_string': 'MuteMe',
                'product_string': 'MuteMe Mini'
            },
            {
                'vendor_id': 0x1234,  # Non-MuteMe device
                'product_id': 0x5678,
                'path': b'/dev/hidraw2',
                'manufacturer_string': 'Other',
                'product_string': 'Other Device'
            }
        ]
        mock_enumerate.return_value = mock_devices
        
        # Discover devices
        devices = MuteMeDevice.discover_devices()
        
        # Should only find MuteMe devices
        assert len(devices) == 2
        assert all(device.vendor_id in [0x20a0, 0x3603] for device in devices)
        assert devices[0].product == "MuteMe Button"
        assert devices[1].product == "MuteMe Mini"
    
    @patch('muteme_btn.hid.device.hid.enumerate')
    @patch('muteme_btn.hid.device.hid.device')
    def test_full_connection_and_led_workflow(self, mock_device_class, mock_enumerate):
        """Test complete connection and LED control workflow."""
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
        
        # Mock device instance
        mock_device = Mock()
        mock_device_class.return_value = mock_device
        
        # Connect to device
        device = MuteMeDevice.connect("/dev/hidraw0")
        
        assert device is not None
        assert device.is_connected()
        
        # Test LED color changes
        device.set_led_color(LEDColor.RED)
        mock_device.write.assert_called_with([0x01, 0x01])
        
        device.set_led_color(LEDColor.GREEN)
        mock_device.write.assert_called_with([0x01, 0x02])
        
        device.set_led_color_by_name("blue")
        mock_device.write.assert_called_with([0x01, 0x03])
        
        # Disconnect
        device.disconnect()
        mock_device.close.assert_called_once()
    
    @patch('muteme_btn.hid.device.hid.enumerate')
    @patch('muteme_btn.hid.device.hid.device')
    def test_full_event_handling_workflow(self, mock_device_class, mock_enumerate):
        """Test complete event handling workflow."""
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
        
        # Mock device instance
        mock_device = Mock()
        mock_device_class.return_value = mock_device
        
        # Connect and create event handler
        MuteMeDevice.connect("/dev/hidraw0")
        event_handler = EventHandler("/dev/hidraw0")
        
        # Mock event callback
        events_received = []
        def event_callback(event):
            events_received.append(event)
        
        event_handler.set_event_callback(event_callback)
        
        # Simulate button press events
        event_handler.process_hid_data(b'\x01')  # Press
        event_handler.process_hid_data(b'\x00')  # Release
        
        # Verify events were processed
        assert len(events_received) == 2
        assert events_received[0].is_press is True
        assert events_received[1].is_release is True
        assert events_received[0].device_path == "/dev/hidraw0"
    
    def test_error_handling_workflow(self):
        """Test error handling in various failure scenarios."""
        # Test connection failure
        with patch('muteme_btn.hid.device.hid.device') as mock_device_class:
            mock_device = Mock()
            mock_device_class.return_value = mock_device
            mock_device.open_path.side_effect = Exception("Permission denied")
            
            with pytest.raises(DeviceError, match="Failed to connect"):
                MuteMeDevice.connect("/dev/hidraw0")
        
        # Test LED control failure
        mock_device = Mock()
        mock_device.write.side_effect = Exception("Device disconnected")
        device = MuteMeDevice(mock_device)
        
        with pytest.raises(DeviceError, match="LED control failed"):
            device.set_led_color(LEDColor.RED)
        
        # Test read failure
        mock_device.read.side_effect = Exception("Read timeout")
        
        with pytest.raises(DeviceError, match="Device read failed"):
            device.read(64)
    
    @patch('muteme_btn.hid.device.os.access')
    def test_permission_checking_workflow(self, mock_access):
        """Test permission checking workflow."""
        # Test successful permission check
        mock_access.return_value = True
        assert MuteMeDevice.check_device_permissions("/dev/hidraw0") is True
        
        # Test failed permission check
        mock_access.return_value = False
        assert MuteMeDevice.check_device_permissions("/dev/hidraw0") is False
        
        # Test exception during permission check
        mock_access.side_effect = OSError("Device not found")
        assert MuteMeDevice.check_device_permissions("/dev/hidraw0") is False
    
    def test_led_color_validation_workflow(self):
        """Test LED color validation workflow."""
        # Test valid colors
        valid_colors = ["red", "green", "blue", "yellow", "cyan", "purple", "white", "nocolor"]
        for color_name in valid_colors:
            color = LEDColor.from_name(color_name)
            assert color is not None
        
        # Test case insensitive validation
        assert LEDColor.from_name("RED") == LEDColor.RED
        assert LEDColor.from_name("Green") == LEDColor.GREEN
        assert LEDColor.from_name("NoColor") == LEDColor.NOCOLOR
        
        # Test invalid color
        with pytest.raises(ValueError, match="Invalid LED color"):
            LEDColor.from_name("invalid_color")
    
    def test_device_info_workflow(self):
        """Test device information handling workflow."""
        device_info = DeviceInfo(
            vendor_id=0x20a0,
            product_id=0x42da,
            path="/dev/hidraw0",
            manufacturer="MuteMe",
            product="MuteMe Button"
        )
        
        # Test device info properties
        assert device_info.vendor_id == 0x20a0
        assert device_info.product_id == 0x42da
        assert device_info.path == "/dev/hidraw0"
        assert device_info.manufacturer == "MuteMe"
        assert device_info.product == "MuteMe Button"
        
        # Test device with info
        mock_device = Mock()
        device = MuteMeDevice(mock_device, device_info)
        
        retrieved_info = device.get_device_info()
        assert retrieved_info == device_info


class TestMockedCIEnvironment:
    """Tests specifically for CI environment compatibility."""
    
    def test_no_hardware_required(self):
        """Test that all functionality works without actual hardware."""
        # These tests should run in any environment without requiring
        # actual MuteMe hardware to be connected
        
        # Test device discovery (returns empty list when no devices)
        with patch('muteme_btn.hid.device.hid.enumerate', return_value=[]):
            devices = MuteMeDevice.discover_devices()
            assert devices == []
        
        # Test LED color creation
        color = LEDColor.from_name("red")
        assert color == LEDColor.RED
        
        # Test event creation
        event = ButtonEvent(
            state=ButtonState.PRESSED,
            timestamp=1234567890.0,
            device_path="/dev/hidraw0"
        )
        assert event.is_press is True
        
        # Test event handler creation
        handler = EventHandler("/dev/hidraw0")
        assert handler.device_path == "/dev/hidraw0"
    
    def test_all_mocked_components(self):
        """Test that all components can be fully mocked."""
        # Mock the entire HID stack
        with patch('muteme_btn.hid.device.hid.enumerate') as mock_enumerate, \
             patch('muteme_btn.hid.device.hid.device') as mock_device_class:
            
            # Setup mocks
            mock_enumerate.return_value = []
            mock_device = Mock()
            mock_device_class.return_value = mock_device
            
            # Test all operations work with mocks
            devices = MuteMeDevice.discover_devices()
            assert devices == []
            
            # Even connection attempts should work with mocks
            try:
                MuteMeDevice.connect("/dev/hidraw0")
            except DeviceError:
                pass  # Expected when no device is available
            
            # All LED operations should work with mocked device
            device = MuteMeDevice(mock_device)
            device.set_led_color(LEDColor.GREEN)
            mock_device.write.assert_called_once()
