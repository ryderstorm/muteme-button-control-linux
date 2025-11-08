"""Tests for main daemon orchestration with asyncio."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from muteme_btn.config import AudioConfig, DeviceConfig
from muteme_btn.core.daemon import MuteMeDaemon


class TestMuteMeDaemon:
    """Test suite for MuteMe daemon."""

    @pytest.fixture
    def mock_device(self):
        """Create a mock HID device."""
        device = Mock()
        device.is_connected = Mock(return_value=True)
        device.read_events = AsyncMock()
        device.close = Mock()
        return device

    @pytest.fixture
    def mock_audio_backend(self):
        """Create a mock audio backend."""
        backend = Mock()
        backend.is_muted = Mock(return_value=False)
        backend.set_mute_state = Mock()
        backend.close = Mock()
        return backend

    @pytest.fixture
    def mock_state_machine(self):
        """Create a mock button state machine."""
        sm = Mock()
        sm.process_event = Mock(return_value=[])
        sm.reset = Mock()
        return sm

    @pytest.fixture
    def mock_led_controller(self):
        """Create a mock LED feedback controller."""
        controller = Mock()
        controller.update_led_to_mute_status = Mock()
        controller.force_led_color = Mock()
        return controller

    @pytest.fixture
    def daemon(self, mock_device, mock_audio_backend, mock_state_machine, mock_led_controller):
        """Create daemon with mocked dependencies."""
        return MuteMeDaemon(
            device=mock_device,
            audio_backend=mock_audio_backend,
            state_machine=mock_state_machine,
            led_controller=mock_led_controller,
        )

    def test_daemon_initialization(self, mock_device, mock_audio_backend):
        """Test daemon initialization with real components."""
        device_config = DeviceConfig()
        audio_config = AudioConfig()

        with (
            patch("muteme_btn.core.daemon.MuteMeDevice") as mock_device_class,
            patch("muteme_btn.core.daemon.PulseAudioBackend") as mock_audio_class,
        ):
            mock_device_class.return_value = mock_device
            mock_audio_class.return_value = mock_audio_backend

            daemon = MuteMeDaemon(device_config, audio_config)

            assert daemon.device == mock_device
            assert daemon.audio_backend == mock_audio_backend
            assert daemon.running is False
            mock_device_class.assert_called_once_with(device_config)
            mock_audio_class.assert_called_once_with(audio_config)

    @pytest.mark.asyncio
    async def test_start_stop_daemon(self, daemon):
        """Test starting and stopping the daemon."""
        # Mock the main loop to avoid infinite loop
        daemon._main_loop = AsyncMock()

        # Start daemon
        start_task = asyncio.create_task(daemon.start())

        # Give it a moment to start and complete the mocked main loop
        await asyncio.wait_for(start_task, timeout=1.0)

        # The daemon should have started and stopped
        assert daemon.running is False

    @pytest.mark.asyncio
    async def test_handle_toggle_action(self, daemon, mock_audio_backend, mock_led_controller):
        """Test handling toggle action from state machine."""
        await daemon._handle_action("toggle")

        mock_audio_backend.set_mute_state.assert_called_once()
        mock_led_controller.update_led_to_mute_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_unknown_action(self, daemon):
        """Test handling unknown action gracefully."""
        # Should not raise exception
        await daemon._handle_action("unknown")

    @pytest.mark.asyncio
    async def test_process_button_events(self, daemon, mock_state_machine):
        """Test processing button events from device."""
        # Mock button events
        press_event = Mock()
        press_event.type = "press"
        press_event.timestamp = datetime.now()

        release_event = Mock()
        release_event.type = "release"
        release_event.timestamp = datetime.now()

        daemon.device.read_events.return_value = [press_event, release_event]

        # Mock state machine to return toggle only on release
        def side_effect(event):
            if event.type == "press":
                return []
            elif event.type == "release":
                return ["toggle"]
            return []

        mock_state_machine.process_event.side_effect = side_effect

        # Mock the action handler
        daemon._handle_action = AsyncMock()

        await daemon._process_button_events()

        # Should have processed both events
        assert mock_state_machine.process_event.call_count == 2
        daemon._handle_action.assert_called_once_with("toggle")

    @pytest.mark.asyncio
    async def test_process_button_events_with_device_error(self, daemon):
        """Test handling device errors during event processing."""
        daemon.device.read_events.side_effect = Exception("Device error")

        # Should not raise exception
        await daemon._process_button_events()

    @pytest.mark.asyncio
    async def test_update_led_feedback(self, daemon, mock_led_controller):
        """Test periodic LED feedback updates."""
        await daemon._update_led_feedback()

        mock_led_controller.update_led_to_mute_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_led_feedback_with_error(self, daemon, mock_led_controller):
        """Test handling LED feedback errors gracefully."""
        mock_led_controller.update_led_to_mute_status.side_effect = Exception("LED error")

        # Should not raise exception
        await daemon._update_led_feedback()

    @pytest.mark.asyncio
    async def test_main_loop_execution(self, daemon):
        """Test main daemon loop execution."""
        # Mock individual components
        daemon._process_button_events = AsyncMock()
        daemon._update_led_feedback = AsyncMock()
        daemon.running = True

        # Mock asyncio.sleep to avoid actual delays
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Make sleep raise CancelledError to exit loop after one iteration
            mock_sleep.side_effect = asyncio.CancelledError()

            try:
                await daemon._main_loop()
            except asyncio.CancelledError:
                pass

            # Should have executed one iteration
            daemon._process_button_events.assert_called_once()
            daemon._update_led_feedback.assert_called_once()

    def test_cleanup_resources(self, daemon):
        """Test resource cleanup on shutdown."""
        daemon.cleanup()

        daemon.device.close.assert_called_once()
        daemon.audio_backend.close.assert_called_once()
        daemon.state_machine.reset.assert_called_once()

    def test_cleanup_with_errors(self, daemon):
        """Test cleanup handles errors gracefully."""
        daemon.device.close.side_effect = Exception("Device error")
        daemon.audio_backend.close.side_effect = Exception("Audio error")

        # Should not raise exception
        daemon.cleanup()

    @pytest.mark.asyncio
    async def test_daemon_context_manager(self, mock_device, mock_audio_backend):
        """Test daemon as async context manager."""
        with (
            patch("muteme_btn.core.daemon.MuteMeDevice") as mock_device_class,
            patch("muteme_btn.core.daemon.PulseAudioBackend") as mock_audio_class,
        ):
            mock_device_class.return_value = mock_device
            mock_audio_class.return_value = mock_audio_backend

            async with MuteMeDaemon() as daemon:
                assert daemon is not None

            mock_device.close.assert_called_once()
            mock_audio_backend.close.assert_called_once()
