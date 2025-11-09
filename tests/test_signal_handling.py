"""Tests for signal handling in daemon."""

import asyncio
import signal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from muteme_btn.core.daemon import MuteMeDaemon


class TestSignalHandling:
    """Test suite for signal handling functionality."""

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
    def daemon(self, mock_device, mock_audio_backend):
        """Create daemon with mocked dependencies."""
        return MuteMeDaemon(device=mock_device, audio_backend=mock_audio_backend)

    @pytest.mark.asyncio
    async def test_signal_handlers_registration(self, daemon):
        """Test that signal handlers are properly registered."""
        # Mock signal.signal to track calls
        with patch("signal.signal") as mock_signal:
            daemon._setup_signal_handlers()

            # Should register handlers for SIGINT and SIGTERM
            assert mock_signal.call_count == 2

            # Check that the correct signals were registered
            signal_calls = [call[0][0] for call in mock_signal.call_args_list]
            assert signal.SIGINT in signal_calls
            assert signal.SIGTERM in signal_calls

    @pytest.mark.asyncio
    async def test_sigint_handler_stops_daemon(self, daemon):
        """Test that SIGINT handler stops the daemon gracefully."""
        daemon._setup_signal_handlers()
        # Mock startup methods to avoid device connection and delays
        daemon._connect_device = AsyncMock()
        daemon._update_led_feedback = AsyncMock()
        daemon._show_startup_pattern = AsyncMock()

        # Make main loop wait so daemon stays running
        async def mock_main_loop():
            while daemon.running:
                await asyncio.sleep(0.1)

        daemon._main_loop = mock_main_loop

        # Start daemon in background
        start_task = asyncio.create_task(daemon.start())

        # Give it a moment to start
        await asyncio.sleep(0.05)
        assert daemon.running is True

        # Send SIGINT signal
        daemon._signal_handler(signal.SIGINT, None)

        # Wait for daemon to stop (may raise CancelledError which is expected)
        try:
            await asyncio.wait_for(start_task, timeout=1.0)
        except (asyncio.CancelledError, TimeoutError):
            # Cancellation is expected when signal handler stops the daemon
            pass

        assert daemon.running is False

    @pytest.mark.asyncio
    async def test_sigterm_handler_stops_daemon(self, daemon):
        """Test that SIGTERM handler stops the daemon gracefully."""
        daemon._setup_signal_handlers()
        # Mock startup methods to avoid device connection and delays
        daemon._connect_device = AsyncMock()
        daemon._update_led_feedback = AsyncMock()
        daemon._show_startup_pattern = AsyncMock()

        # Make main loop wait so daemon stays running
        async def mock_main_loop():
            while daemon.running:
                await asyncio.sleep(0.1)

        daemon._main_loop = mock_main_loop

        # Start daemon in background
        start_task = asyncio.create_task(daemon.start())

        # Give it a moment to start
        await asyncio.sleep(0.05)
        assert daemon.running is True

        # Send SIGTERM signal
        daemon._signal_handler(signal.SIGTERM, None)

        # Wait for daemon to stop (may raise CancelledError which is expected)
        try:
            await asyncio.wait_for(start_task, timeout=1.0)
        except (asyncio.CancelledError, TimeoutError):
            # Cancellation is expected when signal handler stops the daemon
            pass

        assert daemon.running is False

    @pytest.mark.asyncio
    async def test_signal_handler_cleanup(self, daemon):
        """Test that signal handler performs proper cleanup."""
        daemon._setup_signal_handlers()
        # Mock startup methods to avoid device connection and delays
        daemon._connect_device = AsyncMock()
        daemon._update_led_feedback = AsyncMock()
        daemon._show_startup_pattern = AsyncMock()
        daemon._main_loop = AsyncMock()
        # Mock cleanup method
        daemon.cleanup = Mock()

        # Start daemon
        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.01)

        # Send signal
        daemon._signal_handler(signal.SIGINT, None)
        await asyncio.wait_for(start_task, timeout=1.0)

        # Cleanup should be called
        daemon.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_signal_handlers(self, daemon):
        """Test that multiple signals don't cause issues."""
        daemon._setup_signal_handlers()
        # Mock startup methods to avoid device connection and delays
        daemon._connect_device = AsyncMock()
        daemon._update_led_feedback = AsyncMock()
        daemon._show_startup_pattern = AsyncMock()
        daemon._main_loop = AsyncMock()

        # Start daemon
        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.01)

        # Send multiple signals
        daemon._signal_handler(signal.SIGINT, None)
        daemon._signal_handler(signal.SIGTERM, None)

        # Should still stop gracefully
        await asyncio.wait_for(start_task, timeout=1.0)
        assert daemon.running is False

    @pytest.mark.asyncio
    async def test_signal_handler_with_daemon_not_running(self, daemon):
        """Test signal handler when daemon is not running."""
        daemon._setup_signal_handlers()

        # Should not raise exception even if daemon not running
        daemon._signal_handler(signal.SIGINT, None)

        assert daemon.running is False

    def test_signal_handler_error_handling(self, daemon):
        """Test that signal handler errors don't crash the application."""
        daemon._setup_signal_handlers()

        # Mock the shutdown event to raise an exception
        daemon._shutdown_event.set = Mock(side_effect=Exception("Shutdown error"))

        # Should not raise exception
        daemon._signal_handler(signal.SIGINT, None)

    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_cleanup(self, daemon):
        """Test graceful shutdown includes cleanup."""
        daemon._setup_signal_handlers()
        # Mock startup methods to avoid device connection and delays
        daemon._connect_device = AsyncMock()
        daemon._update_led_feedback = AsyncMock()
        daemon._show_startup_pattern = AsyncMock()
        daemon._main_loop = AsyncMock()

        # Track cleanup
        cleanup_called = False
        original_cleanup = daemon.cleanup

        def mock_cleanup():
            nonlocal cleanup_called
            cleanup_called = True
            original_cleanup()

        daemon.cleanup = mock_cleanup

        # Start and stop daemon
        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.01)

        daemon._signal_handler(signal.SIGINT, None)
        await asyncio.wait_for(start_task, timeout=1.0)

        assert cleanup_called
        assert daemon.running is False

    @pytest.mark.asyncio
    async def test_signal_handler_idempotency(self, daemon):
        """Test that calling signal handler multiple times is safe."""
        daemon._setup_signal_handlers()
        # Mock startup methods to avoid device connection and delays
        daemon._connect_device = AsyncMock()
        daemon._update_led_feedback = AsyncMock()
        daemon._show_startup_pattern = AsyncMock()
        daemon._main_loop = AsyncMock()

        # Start daemon
        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.01)

        # Call signal handler multiple times
        daemon._signal_handler(signal.SIGINT, None)
        daemon._signal_handler(signal.SIGINT, None)
        daemon._signal_handler(signal.SIGINT, None)

        # Should still stop gracefully
        await asyncio.wait_for(start_task, timeout=1.0)
        assert daemon.running is False
