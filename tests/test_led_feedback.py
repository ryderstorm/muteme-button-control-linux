"""Tests for LED feedback synchronization with mute status."""

from unittest.mock import Mock

import pytest

from muteme_btn.core.led_feedback import LEDFeedbackController
from muteme_btn.hid.device import LEDColor


class TestLEDFeedbackController:
    """Test suite for LED feedback controller."""

    @pytest.fixture
    def mock_device(self):
        """Create a mock HID device."""
        device = Mock()
        device.set_led_color = Mock()
        device.set_led_color_by_name = Mock()
        device.is_connected = Mock(return_value=True)
        return device

    @pytest.fixture
    def mock_audio_backend(self):
        """Create a mock audio backend."""
        backend = Mock()
        backend.is_muted = Mock(return_value=False)
        return backend

    @pytest.fixture
    def led_controller(self, mock_device, mock_audio_backend):
        """Create LED feedback controller with mocked dependencies."""
        return LEDFeedbackController(
            device=mock_device,
            audio_backend=mock_audio_backend,
            muted_color=LEDColor.RED,
            unmuted_color=LEDColor.GREEN,
        )

    def test_initialization(self, mock_device, mock_audio_backend):
        """Test LED feedback controller initialization."""
        controller = LEDFeedbackController(
            device=mock_device,
            audio_backend=mock_audio_backend,
            muted_color=LEDColor.RED,
            unmuted_color=LEDColor.GREEN,
        )

        assert controller.device == mock_device
        assert controller.audio_backend == mock_audio_backend
        assert controller.muted_color == LEDColor.RED
        assert controller.unmuted_color == LEDColor.GREEN

    def test_update_led_when_unmuted(self, led_controller, mock_audio_backend):
        """Test LED updates when audio is unmuted."""
        mock_audio_backend.is_muted.return_value = False

        led_controller.update_led_to_mute_status()

        led_controller.device.set_led_color.assert_called_once_with(LEDColor.GREEN)

    def test_update_led_when_muted(self, led_controller, mock_audio_backend):
        """Test LED updates when audio is muted."""
        mock_audio_backend.is_muted.return_value = True

        led_controller.update_led_to_mute_status()

        led_controller.device.set_led_color.assert_called_once_with(LEDColor.RED)

    def test_update_led_with_device_disconnected(self, led_controller, mock_device):
        """Test LED update handles disconnected device gracefully."""
        mock_device.is_connected.return_value = False

        # Should not raise exception
        led_controller.update_led_to_mute_status()

        # Should not attempt to set LED color
        led_controller.device.set_led_color.assert_not_called()

    def test_update_led_with_audio_error(self, led_controller, mock_audio_backend):
        """Test LED update handles audio backend errors gracefully."""
        mock_audio_backend.is_muted.side_effect = Exception("Audio error")

        # Should not raise exception
        led_controller.update_led_to_mute_status()

        # Should not attempt to set LED color
        led_controller.device.set_led_color.assert_not_called()

    def test_update_led_with_device_error(self, led_controller, mock_device):
        """Test LED update handles device errors gracefully."""
        mock_device.set_led_color.side_effect = Exception("Device error")

        # Should not raise exception
        led_controller.update_led_to_mute_status()

        # Should still attempt to set LED color
        mock_device.set_led_color.assert_called_once()

    def test_set_muted_color(self, led_controller):
        """Test setting muted color."""
        led_controller.set_muted_color(LEDColor.BLUE)

        assert led_controller.muted_color == LEDColor.BLUE

    def test_set_unmuted_color(self, led_controller):
        """Test setting unmuted color."""
        led_controller.set_unmuted_color(LEDColor.YELLOW)

        assert led_controller.unmuted_color == LEDColor.YELLOW

    def test_set_colors_by_name(self, led_controller):
        """Test setting colors by name."""
        led_controller.set_colors_by_name("blue", "yellow")

        assert led_controller.muted_color == LEDColor.BLUE
        assert led_controller.unmuted_color == LEDColor.YELLOW

    def test_get_current_status(self, led_controller, mock_audio_backend):
        """Test getting current LED and mute status."""
        mock_audio_backend.is_muted.return_value = True

        status = led_controller.get_current_status()

        assert status["muted"] is True
        assert status["led_color"] == LEDColor.RED
        assert status["device_connected"] is True

    def test_force_led_color(self, led_controller):
        """Test forcing LED to specific color."""
        led_controller.force_led_color(LEDColor.PURPLE)

        led_controller.device.set_led_color.assert_called_once_with(LEDColor.PURPLE)

    def test_force_led_color_by_name(self, led_controller):
        """Test forcing LED to specific color by name."""
        led_controller.force_led_color_by_name("purple")

        led_controller.device.set_led_color.assert_called_once_with(LEDColor.PURPLE)

    def test_create_with_default_colors(self, mock_device, mock_audio_backend):
        """Test creating controller with default colors."""
        controller = LEDFeedbackController(device=mock_device, audio_backend=mock_audio_backend)

        assert controller.muted_color == LEDColor.RED
        assert controller.unmuted_color == LEDColor.GREEN

    def test_create_with_custom_colors(self, mock_device, mock_audio_backend):
        """Test creating controller with custom colors."""
        controller = LEDFeedbackController(
            device=mock_device,
            audio_backend=mock_audio_backend,
            muted_color=LEDColor.BLUE,
            unmuted_color=LEDColor.YELLOW,
        )

        assert controller.muted_color == LEDColor.BLUE
        assert controller.unmuted_color == LEDColor.YELLOW
