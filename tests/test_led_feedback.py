"""Tests for LED feedback synchronization with mute status."""

from unittest.mock import Mock, call

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

    def test_update_led_skips_duplicate_color_updates(self, led_controller, mock_audio_backend):
        """Test duplicate LED writes are skipped when color is unchanged."""
        mock_audio_backend.is_muted.return_value = False

        led_controller.update_led_to_mute_status()
        led_controller.update_led_to_mute_status()

        # First call writes GREEN, second call is a no-op
        led_controller.device.set_led_color.assert_called_once_with(LEDColor.GREEN)

    def test_update_led_reapplies_after_disconnect(
        self, led_controller, mock_audio_backend, mock_device
    ):
        """Test LED state is re-applied after a disconnect/reconnect cycle."""
        mock_audio_backend.is_muted.return_value = False
        mock_device.is_connected.side_effect = [True, False, True]

        led_controller.update_led_to_mute_status()  # apply GREEN
        led_controller.update_led_to_mute_status()  # disconnected, reset cache
        led_controller.update_led_to_mute_status()  # reconnected, apply GREEN again

        assert led_controller.device.set_led_color.call_count == 2

    def test_set_device_resets_cached_led_state(self, led_controller, mock_audio_backend):
        """Test swapping devices forces LED re-apply for current mute state."""
        first_device = led_controller.device
        second_device = Mock()
        second_device.set_led_color = Mock()
        second_device.is_connected = Mock(return_value=True)
        mock_audio_backend.is_muted.return_value = True

        led_controller.update_led_to_mute_status()
        first_device.set_led_color.assert_called_once_with(LEDColor.RED)

        led_controller.set_device(second_device)
        led_controller.update_led_to_mute_status()

        second_device.set_led_color.assert_called_once_with(LEDColor.RED)

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


class TestModeAwareLEDFeedback:
    """Tests for mode-aware LED rendering."""

    @pytest.fixture
    def mode_led_controller(self):
        """Create a LED controller for mode-aware tests."""
        device = Mock()
        device.set_led_color = Mock()
        device.is_connected = Mock(return_value=True)
        audio_backend = Mock()
        audio_backend.is_muted = Mock(return_value=False)
        return LEDFeedbackController(device=device, audio_backend=audio_backend)

    def test_update_ptt_idle_sets_blue(self, mode_led_controller):
        """PTT idle should use the configured idle color."""
        mode_led_controller.update_led_for_mode("ptt", active=False)

        mode_led_controller.device.set_led_color.assert_called_once_with(LEDColor.BLUE)

    def test_update_ptt_active_sets_yellow(self, mode_led_controller):
        """PTT active should use the configured active color."""
        mode_led_controller.update_led_for_mode("ptt", active=True)

        mode_led_controller.device.set_led_color.assert_called_once_with(LEDColor.YELLOW)

    def test_show_mode_switch_confirmation_animates(self, mode_led_controller):
        """Mode switches should produce a short visible confirmation."""
        mode_led_controller.show_mode_switch_confirmation()

        assert mode_led_controller.device.set_led_color.call_args_list == [
            call(LEDColor.WHITE),
            call(LEDColor.NOCOLOR),
            call(LEDColor.WHITE),
        ]

    def test_update_ptt_led_logs_and_swallows_device_errors(self, mode_led_controller, caplog):
        """PTT LED update failures should not escape the mode-state path."""
        mode_led_controller.device.set_led_color.side_effect = RuntimeError("USB write failed")

        mode_led_controller.update_led_for_mode("ptt", active=True)

        assert "Failed to update PTT LED" in caplog.text
        assert "YELLOW" in caplog.text
