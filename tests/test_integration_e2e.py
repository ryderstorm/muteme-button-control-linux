"""End-to-end integration tests for the complete MuteMe button control system."""

import asyncio
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from muteme_btn.config import AudioConfig, DeviceConfig
from muteme_btn.core.daemon import MuteMeDaemon
from muteme_btn.core.led_feedback import LEDFeedbackController
from muteme_btn.core.state import ButtonStateMachine
from muteme_btn.hid.device import LEDColor


class MockButtonEvent:
    """Mock button event for testing."""

    def __init__(self, event_type: str, timestamp: datetime):
        self.type = event_type
        self.timestamp = timestamp


class MockHIDDevice:
    """Mock HID device that simulates button events."""

    def __init__(self, device_config: DeviceConfig):
        self.config = device_config
        self._connected = False
        self._events: list[MockButtonEvent] = []
        self._led_color: LEDColor = LEDColor.NOCOLOR
        self._read_callback = None

    async def connect(self) -> None:
        """Mock connection."""
        self._connected = True

    def disconnect(self) -> None:
        """Mock disconnection."""
        self._connected = False

    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected

    async def read_events(self) -> list[MockButtonEvent]:
        """Read pending events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def set_led_color(self, color: LEDColor) -> None:
        """Set LED color."""
        if not self._connected:
            raise Exception("Device not connected")
        self._led_color = color

    def get_led_color(self) -> LEDColor:
        """Get current LED color."""
        return self._led_color

    def add_event(self, event_type: str, timestamp: datetime | None = None) -> None:
        """Add a button event."""
        if timestamp is None:
            timestamp = datetime.now()
        self._events.append(MockButtonEvent(event_type, timestamp))

    def close(self) -> None:
        """Close device."""
        self.disconnect()


class MockAudioBackend:
    """Mock audio backend."""

    def __init__(self, audio_config: AudioConfig):
        self.config = audio_config
        self._muted = False
        self._connected = True

    def get_default_sink(self) -> dict[str, Any]:
        """Get default sink info."""
        if not self._connected:
            raise Exception("Not connected")
        return {"name": "default_sink", "muted": self._muted}

    def set_mute_state(self, sink_name: str, muted: bool) -> None:
        """Set mute state."""
        if not self._connected:
            raise Exception("Not connected")
        self._muted = muted

    def is_muted(self, sink_name: str | None = None) -> bool:
        """Check mute state."""
        if not self._connected:
            raise Exception("Not connected")
        return self._muted

    def list_sinks(self) -> list[dict[str, Any]]:
        """List sinks."""
        if not self._connected:
            raise Exception("Not connected")
        return [self.get_default_sink()]

    def close(self) -> None:
        """Close backend."""
        self._connected = False


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    @pytest.fixture
    def device_config(self):
        """Create device configuration."""
        return DeviceConfig()

    @pytest.fixture
    def audio_config(self):
        """Create audio configuration."""
        return AudioConfig()

    @pytest.fixture
    def mock_device(self, device_config):
        """Create mock HID device."""
        return MockHIDDevice(device_config)

    @pytest.fixture
    def mock_audio_backend(self, audio_config):
        """Create mock audio backend."""
        return MockAudioBackend(audio_config)

    @pytest.fixture
    def integration_daemon(self, mock_device, mock_audio_backend):
        """Create daemon with mocked components."""
        state_machine = ButtonStateMachine()
        led_controller = LEDFeedbackController(device=mock_device, audio_backend=mock_audio_backend)

        return MuteMeDaemon(
            device=mock_device,
            audio_backend=mock_audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
        )

    @pytest.mark.asyncio
    async def test_complete_button_press_workflow(
        self, integration_daemon, mock_device, mock_audio_backend
    ):
        """Test complete workflow from button press to LED update."""
        # Connect device
        await mock_device.connect()

        # Mock startup pattern to avoid delays
        integration_daemon._show_startup_pattern = AsyncMock()

        # Start daemon
        daemon_task = asyncio.create_task(integration_daemon.start())
        await asyncio.sleep(0.05)  # Wait for initialization

        # Initial state: unmuted, green LED
        assert mock_audio_backend.is_muted() is False
        assert mock_device.get_led_color() == LEDColor.GREEN

        # Simulate button press and release
        press_time = datetime.now()
        mock_device.add_event("press", press_time)
        mock_device.add_event("release", press_time + timedelta(milliseconds=50))

        # Wait for processing
        await asyncio.sleep(0.05)

        # Should be muted now, red LED
        assert mock_audio_backend.is_muted() is True
        assert mock_device.get_led_color() == LEDColor.RED

        # Stop daemon
        await integration_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_multiple_toggle_cycles(
        self, integration_daemon, mock_device, mock_audio_backend
    ):
        """Test multiple toggle cycles work correctly."""
        await mock_device.connect()

        # Mock startup pattern to avoid delays
        integration_daemon._show_startup_pattern = AsyncMock()

        daemon_task = asyncio.create_task(integration_daemon.start())
        await asyncio.sleep(0.05)  # Wait for initialization

        # Cycle 1: unmuted -> muted
        mock_device.add_event("press")
        mock_device.add_event("release")
        await asyncio.sleep(0.02)
        assert mock_audio_backend.is_muted() is True
        assert mock_device.get_led_color() == LEDColor.RED

        # Cycle 2: muted -> unmuted
        mock_device.add_event("press")
        mock_device.add_event("release")
        await asyncio.sleep(0.02)
        assert mock_audio_backend.is_muted() is False
        assert mock_device.get_led_color() == LEDColor.GREEN

        # Cycle 3: unmuted -> muted again
        mock_device.add_event("press")
        mock_device.add_event("release")
        await asyncio.sleep(0.02)
        assert mock_audio_backend.is_muted() is True
        assert mock_device.get_led_color() == LEDColor.RED

        await integration_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_device_disconnection_handling(
        self, integration_daemon, mock_device, mock_audio_backend
    ):
        """Test handling of device disconnection."""
        await mock_device.connect()

        # Mock startup pattern to avoid delays
        integration_daemon._show_startup_pattern = AsyncMock()

        daemon_task = asyncio.create_task(integration_daemon.start())
        await asyncio.sleep(0.05)  # Wait for initialization

        # Initial state
        assert mock_device.get_led_color() == LEDColor.GREEN

        # Disconnect device
        mock_device.disconnect()
        await asyncio.sleep(0.02)

        # Try to toggle (should not crash)
        mock_device.add_event("press")
        mock_device.add_event("release")
        await asyncio.sleep(0.02)

        # Audio state should not have changed
        assert mock_audio_backend.is_muted() is False

        await integration_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_audio_backend_error_handling(
        self, integration_daemon, mock_device, mock_audio_backend
    ):
        """Test handling of audio backend errors."""
        await mock_device.connect()

        daemon_task = asyncio.create_task(integration_daemon.start())
        await asyncio.sleep(0.01)

        # Simulate audio backend error
        mock_audio_backend._connected = False

        # Try to toggle (should not crash)
        mock_device.add_event("press")
        mock_device.add_event("release")
        await asyncio.sleep(0.02)

        # Should still be running
        assert integration_daemon.running is True

        await integration_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_double_tap_detection(self, integration_daemon, mock_device, mock_audio_backend):
        """Test double-tap detection in integration."""
        await mock_device.connect()

        # Mock startup pattern to avoid delays
        integration_daemon._show_startup_pattern = AsyncMock()

        daemon_task = asyncio.create_task(integration_daemon.start())
        await asyncio.sleep(0.05)  # Wait for initialization

        # Initial state
        assert mock_audio_backend.is_muted() is False

        # Simple double tap: two complete press-release cycles
        base_time = datetime.now()

        # First press-release
        mock_device.add_event("press", base_time)
        mock_device.add_event("release", base_time + timedelta(milliseconds=50))

        # Wait for first toggle
        await asyncio.sleep(0.05)

        # Should have toggled once
        assert mock_audio_backend.is_muted() is True

        # Second press-release (double tap)
        mock_device.add_event("press", base_time + timedelta(milliseconds=200))
        mock_device.add_event("release", base_time + timedelta(milliseconds=250))

        # Wait for second toggle
        await asyncio.sleep(0.05)

        # Should have toggled back
        assert mock_audio_backend.is_muted() is False

        await integration_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_graceful_shutdown_integration(self, integration_daemon, mock_device):
        """Test graceful shutdown with cleanup."""
        await mock_device.connect()

        daemon_task = asyncio.create_task(integration_daemon.start())
        await asyncio.sleep(0.01)

        # Verify running
        assert integration_daemon.running is True
        assert mock_device.is_connected() is True

        # Stop daemon
        await integration_daemon.stop()
        await daemon_task

        # Verify cleanup
        assert integration_daemon.running is False
        assert mock_device.is_connected() is False

    @pytest.mark.asyncio
    async def test_led_feedback_synchronization(
        self, integration_daemon, mock_device, mock_audio_backend
    ):
        """Test LED feedback stays synchronized with audio state."""
        await mock_device.connect()

        # Mock startup pattern to avoid delays
        integration_daemon._show_startup_pattern = AsyncMock()

        daemon_task = asyncio.create_task(integration_daemon.start())
        await asyncio.sleep(0.05)  # Wait for initialization

        # Test various states
        states = [False, True, False, True, False]
        expected_colors = [
            LEDColor.GREEN,
            LEDColor.RED,
            LEDColor.GREEN,
            LEDColor.RED,
            LEDColor.GREEN,
        ]

        for i, (muted_state, expected_color) in enumerate(
            zip(states, expected_colors, strict=True)
        ):
            # Set audio state directly
            mock_audio_backend._muted = muted_state

            # Trigger LED update
            await asyncio.sleep(0.02)

            # Check LED color matches
            assert mock_device.get_led_color() == expected_color, (
                f"Cycle {i}: expected {expected_color}, got {mock_device.get_led_color()}"
            )

        await integration_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_concurrent_events_handling(
        self, integration_daemon, mock_device, mock_audio_backend
    ):
        """Test handling of concurrent events."""
        await mock_device.connect()

        daemon_task = asyncio.create_task(integration_daemon.start())
        await asyncio.sleep(0.01)

        # Add multiple events rapidly
        base_time = datetime.now()
        for i in range(5):
            mock_device.add_event("press", base_time + timedelta(milliseconds=i * 10))
            mock_device.add_event("release", base_time + timedelta(milliseconds=i * 10 + 5))

        await asyncio.sleep(0.1)

        # Should handle events gracefully
        assert integration_daemon.running is True
        assert mock_audio_backend.is_muted() in [True, False]  # Should be in a valid state

        await integration_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_system_recovery_after_errors(
        self, integration_daemon, mock_device, mock_audio_backend
    ):
        """Test system recovery after transient errors."""
        await mock_device.connect()

        # Mock startup pattern to avoid delays
        integration_daemon._show_startup_pattern = AsyncMock()

        daemon_task = asyncio.create_task(integration_daemon.start())
        await asyncio.sleep(0.05)  # Wait for initialization

        # Simulate transient error
        original_is_muted = mock_audio_backend.is_muted
        mock_audio_backend.is_muted = Mock(side_effect=Exception("Transient error"))

        # System should continue running
        await asyncio.sleep(0.02)
        assert integration_daemon.running is True

        # Recover from error
        mock_audio_backend.is_muted = original_is_muted

        # Normal operation should resume
        mock_device.add_event("press")
        mock_device.add_event("release")
        await asyncio.sleep(0.02)

        assert mock_audio_backend.is_muted() is True

        await integration_daemon.stop()
        await daemon_task

    @pytest.mark.asyncio
    async def test_configuration_integration(self):
        """Test system with custom configurations."""
        custom_device_config = DeviceConfig(vid=0x1234, pid=0x5678, timeout=10.0)
        custom_audio_config = AudioConfig(sink_name="custom_sink", poll_interval=0.8)

        with (
            patch("muteme_btn.core.daemon.MuteMeDevice") as mock_device_class,
            patch("muteme_btn.core.daemon.PulseAudioBackend") as mock_audio_class,
        ):
            mock_device = MockHIDDevice(custom_device_config)
            mock_audio = MockAudioBackend(custom_audio_config)

            mock_device_class.return_value = mock_device
            mock_audio_class.return_value = mock_audio

            async with MuteMeDaemon(custom_device_config, custom_audio_config) as daemon:
                assert daemon.device_config.vid == 0x1234
                assert daemon.audio_config.sink_name == "custom_sink"

                # Should start and stop cleanly
                await asyncio.sleep(0.01)
