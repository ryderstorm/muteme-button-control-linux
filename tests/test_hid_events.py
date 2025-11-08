"""Tests for HID button event handling and processing."""

from unittest.mock import Mock, patch
from muteme_btn.hid.events import ButtonEvent, ButtonState, EventHandler


class TestButtonEvent:
    """Test cases for ButtonEvent data class."""
    
    def test_button_event_creation(self):
        """Test ButtonEvent creation."""
        event = ButtonEvent(
            state=ButtonState.PRESSED,
            timestamp=1234567890.123,
            device_path="/dev/hidraw0"
        )
        
        assert event.state == ButtonState.PRESSED
        assert event.timestamp == 1234567890.123
        assert event.device_path == "/dev/hidraw0"
        assert event.is_press is True
        assert event.is_release is False
    
    def test_button_event_release(self):
        """Test ButtonEvent for release state."""
        event = ButtonEvent(
            state=ButtonState.RELEASED,
            timestamp=1234567890.123,
            device_path="/dev/hidraw0"
        )
        
        assert event.state == ButtonState.RELEASED
        assert event.is_press is False
        assert event.is_release is True


class TestEventHandler:
    """Test cases for EventHandler class."""
    
    def test_event_handler_creation(self):
        """Test EventHandler creation."""
        handler = EventHandler("/dev/hidraw0")
        
        assert handler.device_path == "/dev/hidraw0"
        assert handler._event_callback is None
    
    def test_set_event_callback(self):
        """Test setting event callback."""
        handler = EventHandler("/dev/hidraw0")
        callback = Mock()
        
        handler.set_event_callback(callback)
        
        assert handler._event_callback == callback
    
    def test_process_hid_data_press_event(self):
        """Test processing HID data for press event."""
        handler = EventHandler("/dev/hidraw0")
        callback = Mock()
        handler.set_event_callback(callback)
        
        # Simulate press data (0x01)
        handler.process_hid_data(b'\x01')
        
        # Verify callback was called
        callback.assert_called_once()
        event = callback.call_args[0][0]
        
        assert isinstance(event, ButtonEvent)
        assert event.state == ButtonState.PRESSED
        assert event.device_path == "/dev/hidraw0"
        assert event.is_press is True
        assert event.timestamp > 0
    
    def test_process_hid_data_release_event(self):
        """Test processing HID data for release event."""
        handler = EventHandler("/dev/hidraw0")
        callback = Mock()
        handler.set_event_callback(callback)
        
        # Simulate release data (0x00)
        handler.process_hid_data(b'\x00')
        
        # Verify callback was called
        callback.assert_called_once()
        event = callback.call_args[0][0]
        
        assert event.state == ButtonState.RELEASED
        assert event.is_release is True
        assert event.device_path == "/dev/hidraw0"
    
    def test_process_hid_data_no_callback(self):
        """Test processing HID data without callback set."""
        handler = EventHandler("/dev/hidraw0")
        
        # Should not raise exception
        handler.process_hid_data(b'\x01')
    
    def test_process_hid_data_empty_data(self):
        """Test processing empty HID data."""
        handler = EventHandler("/dev/hidraw0")
        callback = Mock()
        handler.set_event_callback(callback)
        
        # Empty data should not trigger callback
        handler.process_hid_data(b'')
        
        callback.assert_not_called()
    
    def test_process_hid_data_multi_byte_data(self):
        """Test processing multi-byte HID data."""
        handler = EventHandler("/dev/hidraw0")
        callback = Mock()
        handler.set_event_callback(callback)
        
        # Multi-byte data, only first byte matters for button state
        handler.process_hid_data(b'\x01\x02\x03')
        
        callback.assert_called_once()
        event = callback.call_args[0][0]
        assert event.state == ButtonState.PRESSED
    
    @patch('time.time')
    def test_process_hid_data_timestamp(self, mock_time):
        """Test that event timestamp is set correctly."""
        mock_time.return_value = 1234567890.5
        
        handler = EventHandler("/dev/hidraw0")
        callback = Mock()
        handler.set_event_callback(callback)
        
        handler.process_hid_data(b'\x01')
        
        event = callback.call_args[0][0]
        assert event.timestamp == 1234567890.5
    
    def test_process_hid_data_unknown_button_value(self):
        """Test processing unknown button values."""
        handler = EventHandler("/dev/hidraw0")
        callback = Mock()
        handler.set_event_callback(callback)
        
        # Unknown value should be treated as released
        handler.process_hid_data(b'\xff')
        
        callback.assert_called_once()
        event = callback.call_args[0][0]
        assert event.state == ButtonState.RELEASED
