"""Tests for main daemon orchestration with asyncio."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from muteme_btn.config import AudioConfig, DeviceConfig, ModeConfig, OperationMode
from muteme_btn.core.daemon import MuteMeDaemon
from muteme_btn.hid.device import DeviceError


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
        controller.set_device = Mock()
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

    def test_daemon_initializes_components(self, mock_device, mock_audio_backend):
        """Test daemon initializes with correct components."""
        device_config = DeviceConfig()
        audio_config = AudioConfig()

        with (
            patch("muteme_btn.core.daemon.MuteMeDevice") as mock_device_class,
            patch("muteme_btn.core.daemon.PulseAudioBackend") as mock_audio_class,
        ):
            mock_device_class.return_value = mock_device
            mock_audio_class.return_value = mock_audio_backend

            daemon = MuteMeDaemon(device_config, audio_config)

            # Device is now None initially (created in start())
            assert daemon.device is None
            assert daemon.device_config == device_config
            assert daemon.audio_config == audio_config
            assert daemon.audio_backend == mock_audio_backend
            assert daemon.running is False
            # Device class should not be called in __init__ anymore.
            mock_device_class.assert_not_called()
            mock_audio_class.assert_called_once_with(audio_config)

    def test_daemon_passes_triple_tap_mode_config_to_state_machine(
        self, mock_device, mock_audio_backend
    ):
        """Daemon should wire triple-tap tuning knobs into the state machine."""
        mode_config = ModeConfig(
            switch_gesture="triple_tap",
            triple_tap_window_ms=625,
            tap_max_duration_ms=130,
            inter_tap_timeout_ms=240,
            ptt_hold_threshold_ms=100,
        )

        daemon = MuteMeDaemon(
            device=mock_device,
            audio_backend=mock_audio_backend,
            mode_config=mode_config,
        )

        assert daemon.state_machine.switch_gesture == "triple_tap"
        assert daemon.state_machine.triple_tap_window_ms == 625
        assert daemon.state_machine.tap_max_duration_ms == 130
        assert daemon.state_machine.inter_tap_timeout_ms == 240
        assert daemon.state_machine.ptt_hold_threshold_ms == 100

    @pytest.mark.asyncio
    async def test_start_stop_daemon(self, daemon):
        """Test starting and stopping the daemon."""
        # Mock device connection and main loop to avoid infinite loop
        daemon._connect_device = AsyncMock()
        daemon._main_loop = AsyncMock()
        daemon._update_led_feedback = AsyncMock()
        daemon._show_startup_pattern = AsyncMock()

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
        # Set running state using the lock for thread safety
        async with daemon._running_lock:
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

            daemon = MuteMeDaemon(device=mock_device)
            async with daemon:
                assert daemon is not None

            # Cleanup should close device and audio backend
            mock_device.close.assert_called_once()
            mock_audio_backend.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_device_disconnection_during_operation(self, daemon, mock_state_machine):
        """Test handling device disconnection during active operation."""
        daemon.device.read_events.return_value = []

        # Simulate stale handle detection after the initial connected check.
        call_count = 0

        def is_connected_side_effect():
            nonlocal call_count
            call_count += 1
            return call_count == 1

        daemon.device.is_connected.side_effect = is_connected_side_effect

        # Should avoid feeding synthetic timeout events after read-side disconnect.
        await daemon._process_button_events()

        assert call_count == 2
        mock_state_machine.process_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_device_disconnection_during_led_update(self, daemon, mock_led_controller):
        """Test handling device disconnection during LED update."""
        # Simulate device disconnection
        daemon.device.is_connected.return_value = False

        # Should handle disconnection gracefully
        await daemon._update_led_feedback()
        # LED controller should not be called when device is disconnected
        mock_led_controller.update_led_to_mute_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_rapid_button_presses(self, daemon, mock_state_machine):
        """Test handling multiple rapid button presses (stress test)."""
        # Create many rapid button events
        events = []
        base_time = datetime.now()
        for i in range(50):
            event = Mock()
            event.type = "press" if i % 2 == 0 else "release"
            event.timestamp = base_time
            events.append(event)

        daemon.device.read_events.return_value = events
        daemon.device.is_connected.return_value = True

        # Mock state machine to return toggle on every release
        def side_effect(event):
            return ["toggle"] if event.type == "release" else []

        mock_state_machine.process_event.side_effect = side_effect
        daemon._handle_action = AsyncMock()

        # Process all events
        await daemon._process_button_events()

        # Should have processed all events
        assert mock_state_machine.process_event.call_count == 50
        # Should have handled toggle actions (one per release = 25)
        assert daemon._handle_action.call_count == 25

    @pytest.mark.asyncio
    async def test_pulseaudio_connection_failure_during_runtime(self, daemon, mock_audio_backend):
        """Test handling PulseAudio connection failures during runtime."""
        # Simulate PulseAudio connection failure during toggle
        mock_audio_backend.is_muted.side_effect = Exception("PulseAudio connection lost")

        # Should handle error gracefully
        await daemon._handle_action("toggle")
        # Error should be logged but not crash the daemon

    @pytest.mark.asyncio
    async def test_device_cleanup_on_startup_exception(self, mock_device, mock_audio_backend):
        """Test device cleanup when exception occurs during startup."""
        device_config = DeviceConfig()
        audio_config = AudioConfig()

        with (
            patch("muteme_btn.core.daemon.MuteMeDevice") as mock_device_class,
            patch("muteme_btn.core.daemon.PulseAudioBackend") as mock_audio_class,
        ):
            mock_device_class.connect_by_vid_pid.return_value = mock_device
            mock_device.is_connected.return_value = True
            mock_audio_class.return_value = mock_audio_backend

            daemon = MuteMeDaemon(device_config, audio_config)

            # Simulate exception during LED controller creation
            # First, ensure device is connected
            daemon.device = mock_device
            mock_device.is_connected.return_value = True

            with patch(
                "muteme_btn.core.daemon.LEDFeedbackController",
                side_effect=Exception("LED controller creation failed"),
            ):
                # The daemon catches exceptions internally, so it won't raise
                # but we can verify cleanup happened
                await daemon.start()

            # Device should be cleaned up even if exception occurs
            assert daemon.running is False
            # Verify cleanup was actually called (cleanup() calls device.close())
            mock_device.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_loop_with_configurable_timing(self, daemon):
        """Test main loop uses configurable poll interval and timeout."""
        # Set custom timing in device config
        daemon.device_config.poll_interval_ms = 20
        daemon.device_config.poll_timeout_ms = 200

        daemon._process_button_events = AsyncMock()
        daemon._update_led_feedback = AsyncMock()
        # Set running state using the lock for thread safety
        async with daemon._running_lock:
            daemon.running = True

        # Mock asyncio.sleep to verify timing
        sleep_calls = []

        async def mock_sleep(duration):
            sleep_calls.append(duration)
            if len(sleep_calls) == 1:
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            try:
                await daemon._main_loop()
            except asyncio.CancelledError:
                pass

            # Should have used configured poll interval (20ms = 0.02s)
            assert len(sleep_calls) > 0
            assert sleep_calls[0] == 0.02

    @pytest.mark.asyncio
    async def test_concurrent_start_stop(self, daemon):
        """Test concurrent start/stop operations are handled safely."""
        daemon._connect_device = AsyncMock()
        daemon._main_loop = AsyncMock()
        daemon._update_led_feedback = AsyncMock()
        daemon._show_startup_pattern = AsyncMock()

        # Start daemon
        start_task = asyncio.create_task(daemon.start())

        # Try to stop while starting
        await asyncio.sleep(0.01)
        stop_task = asyncio.create_task(daemon.stop())

        # Both should complete without errors
        await asyncio.gather(start_task, stop_task, return_exceptions=True)

        # Daemon should be stopped
        assert daemon.running is False

    @pytest.mark.asyncio
    async def test_attempt_reconnect_success_rebinds_led_controller(
        self, daemon, mock_led_controller
    ):
        """Test successful reconnect updates device references and resets backoff."""
        disconnected_device = Mock()
        disconnected_device.is_connected.return_value = False
        daemon.device = disconnected_device

        reconnected_device = Mock()
        reconnected_device.is_connected.return_value = True

        async def connect_side_effect():
            daemon.device = reconnected_device

        daemon._connect_device = AsyncMock(side_effect=connect_side_effect)
        daemon._update_led_feedback = AsyncMock()

        await daemon._attempt_reconnect_if_needed()

        daemon._connect_device.assert_called_once()
        daemon.led_controller.set_device.assert_called_once_with(reconnected_device)
        daemon._update_led_feedback.assert_awaited_once()
        assert daemon._reconnect_delay_seconds == daemon._reconnect_initial_delay_seconds

    @pytest.mark.asyncio
    async def test_attempt_reconnect_failure_uses_backoff(self, daemon):
        """Test failed reconnect attempts are backed off and not retried early."""
        disconnected_device = Mock()
        disconnected_device.is_connected.return_value = False
        daemon.device = disconnected_device
        daemon._connect_device = AsyncMock(side_effect=DeviceError("reconnect failed"))

        with patch("muteme_btn.core.daemon.time.monotonic", side_effect=[100.0, 100.8, 101.0]):
            await daemon._attempt_reconnect_if_needed()
            await daemon._attempt_reconnect_if_needed()

        # Second call is within backoff window, so reconnect should only be attempted once
        daemon._connect_device.assert_called_once()
        assert daemon._next_reconnect_attempt_at == 101.3
        assert daemon._reconnect_delay_seconds == 1.0


class TestMuteMeDaemonPTTMode:
    """Tests for daemon integration with hold-to-talk mode."""

    @pytest.fixture
    def mock_key_emitter(self):
        emitter = Mock()
        emitter.press_f19 = Mock()
        emitter.release_f19 = Mock()
        emitter.release_all = Mock()
        emitter.close = Mock()
        return emitter

    @pytest.fixture
    def ptt_daemon_parts(self, mock_key_emitter):
        """Create daemon dependencies for PTT integration tests."""
        device = Mock()
        device.is_connected = Mock(return_value=True)
        device.read_events = AsyncMock(return_value=[])
        device.close = Mock()
        audio_backend = Mock()
        audio_backend.is_muted = Mock(return_value=False)
        audio_backend.set_mute_state = Mock()
        audio_backend.close = Mock()
        state_machine = Mock()
        state_machine.process_event = Mock(return_value=[])
        state_machine.reset = Mock()
        led_controller = Mock()
        led_controller.update_led_to_mute_status = Mock()
        led_controller.update_led_for_mode = Mock()
        led_controller.show_mode_switch_confirmation = AsyncMock()
        led_controller.force_led_color = Mock()
        return device, audio_backend, state_machine, led_controller, mock_key_emitter

    @pytest.mark.asyncio
    async def test_handle_ptt_actions_restore_mute_state_after_temporary_unmute(
        self, ptt_daemon_parts
    ):
        """PTT should restore mute if it temporarily unmuted the microphone."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        audio_backend.is_muted.side_effect = [True]
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )

        await daemon._handle_action("ptt_press")
        await daemon._handle_action("ptt_release")

        key_emitter.press_f19.assert_called_once()
        key_emitter.release_f19.assert_called_once()
        assert audio_backend.set_mute_state.call_args_list == [
            ((None, False),),
            ((None, True),),
        ]

    @pytest.mark.asyncio
    async def test_ptt_press_restores_mute_if_key_press_fails(self, ptt_daemon_parts):
        """PTT press failures should not leave a temporarily unmuted mic live."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        audio_backend.is_muted.return_value = True
        key_emitter.press_f19.side_effect = RuntimeError("ydotoold unavailable")
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )

        await daemon._handle_action("ptt_press")

        assert audio_backend.set_mute_state.call_args_list == [
            ((None, False),),
            ((None, True),),
        ]
        assert daemon._ptt_active is False

    @pytest.mark.asyncio
    async def test_ptt_release_keeps_ptt_active_if_key_release_fails(self, ptt_daemon_parts):
        """PTT release failures should keep active state so cleanup can retry key release."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        key_emitter.release_f19.side_effect = RuntimeError("release failed")
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )
        daemon._ptt_active = True
        daemon._ptt_restore_mute_after_release = True

        await daemon._handle_action("ptt_release")

        audio_backend.set_mute_state.assert_called_once_with(None, True)
        assert daemon._ptt_active is True

    @pytest.mark.asyncio
    async def test_handle_ptt_actions_leave_originally_unmuted_microphone_unmuted(
        self, ptt_daemon_parts
    ):
        """PTT release should not mute a microphone that was already unmuted."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        audio_backend.is_muted.return_value = False
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )

        await daemon._handle_action("ptt_press")
        await daemon._handle_action("ptt_release")

        key_emitter.press_f19.assert_called_once()
        key_emitter.release_f19.assert_called_once()
        audio_backend.set_mute_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_switching_into_ptt_does_not_unmute_before_hold(self, ptt_daemon_parts):
        """Entering PTT mode should wait for an actual PTT press before unmuting."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        audio_backend.is_muted.return_value = True
        state_machine.current_mode = OperationMode.PTT
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )

        await daemon._handle_action("switch_mode")

        audio_backend.set_mute_state.assert_not_called()
        key_emitter.release_all.assert_not_called()
        led_controller.show_mode_switch_confirmation.assert_called_once()

    def test_release_ptt_key_skips_backend_when_no_ptt_cleanup_needed(self, ptt_daemon_parts):
        """Forced cleanup should avoid backend I/O when no PTT state is active."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )

        daemon._release_ptt_key_if_needed()

        key_emitter.release_all.assert_not_called()
        audio_backend.set_mute_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_switch_mode_schedules_confirmation_without_blocking(self, ptt_daemon_parts):
        """Mode-switch confirmation should not stall the button action loop."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        confirmation_started = asyncio.Event()
        confirmation_release = asyncio.Event()

        async def confirmation() -> None:
            confirmation_started.set()
            await confirmation_release.wait()

        led_controller.show_mode_switch_confirmation.side_effect = confirmation
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )

        await daemon._handle_action("switch_mode")

        assert confirmation_started.is_set()
        assert daemon._mode_switch_confirmation_task is not None
        led_controller.update_led_to_mute_status.assert_not_called()
        confirmation_release.set()
        await asyncio.sleep(0)
        led_controller.update_led_to_mute_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_second_switch_mode_cancels_existing_confirmation_task(self, ptt_daemon_parts):
        """A new mode switch should not orphan an older LED confirmation task."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        confirmation_started = [asyncio.Event(), asyncio.Event()]
        confirmation_release = [asyncio.Event(), asyncio.Event()]
        call_index = 0

        async def confirmation() -> None:
            nonlocal call_index
            index = call_index
            call_index += 1
            confirmation_started[index].set()
            await confirmation_release[index].wait()

        led_controller.show_mode_switch_confirmation.side_effect = confirmation
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )

        await daemon._handle_action("switch_mode")
        first_task = daemon._mode_switch_confirmation_task
        assert first_task is not None
        assert confirmation_started[0].is_set()

        await daemon._handle_action("switch_mode")

        assert first_task.cancelled()
        assert confirmation_started[1].is_set()
        assert daemon._mode_switch_confirmation_task is not None
        assert daemon._mode_switch_confirmation_task is not first_task
        confirmation_release[1].set()
        await asyncio.sleep(0)

    @pytest.mark.asyncio
    async def test_led_feedback_skips_steady_state_while_confirmation_is_active(
        self, ptt_daemon_parts
    ):
        """Periodic LED refreshes should not repaint over an active switch flash."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        confirmation_release = asyncio.Event()

        async def confirmation() -> None:
            await confirmation_release.wait()

        led_controller.show_mode_switch_confirmation.side_effect = confirmation
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )

        await daemon._handle_action("switch_mode")
        led_controller.update_led_to_mute_status.reset_mock()

        await daemon._update_led_feedback()

        led_controller.update_led_to_mute_status.assert_not_called()
        confirmation_release.set()
        await asyncio.sleep(0)

    @pytest.mark.asyncio
    async def test_ptt_press_unmutes_if_microphone_was_muted_after_mode_switch(
        self, ptt_daemon_parts
    ):
        """PTT press should defensively unmute before emitting F19 down."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        audio_backend.is_muted.return_value = True
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )

        await daemon._handle_action("ptt_press")

        audio_backend.set_mute_state.assert_called_once_with(None, False)
        key_emitter.press_f19.assert_called_once()

    def test_cleanup_releases_any_held_ptt_key(self, ptt_daemon_parts):
        """Daemon cleanup should force-release synthetic keys and close emitter resources."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )
        daemon._ptt_active = True

        daemon.cleanup()

        key_emitter.release_all.assert_called_once()
        key_emitter.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_cancels_active_mode_switch_confirmation_task(self, ptt_daemon_parts):
        """Daemon cleanup should cancel in-flight LED confirmation before closing resources."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        confirmation_started = asyncio.Event()
        confirmation_release = asyncio.Event()

        async def confirmation() -> None:
            confirmation_started.set()
            await confirmation_release.wait()

        led_controller.show_mode_switch_confirmation.side_effect = confirmation
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )
        await daemon._handle_action("switch_mode")
        assert confirmation_started.is_set()
        task = daemon._mode_switch_confirmation_task
        assert task is not None

        daemon.cleanup()
        await asyncio.sleep(0)

        assert task.cancelled()
        assert daemon._mode_switch_confirmation_task is None
        device.close.assert_called_once()
        key_emitter.close.assert_called_once()

    def test_forced_ptt_release_keeps_ptt_active_when_key_release_fails(self, ptt_daemon_parts):
        """Forced cleanup should keep active state after failed key I/O for later retry."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        key_emitter.release_all.side_effect = RuntimeError("release failed")
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )
        daemon._ptt_active = True
        daemon._ptt_restore_mute_after_release = True

        daemon._release_ptt_key_if_needed()

        audio_backend.set_mute_state.assert_called_once_with(None, True)
        assert daemon._ptt_active is True

        key_emitter.release_all.side_effect = None
        daemon._release_ptt_key_if_needed()

        assert key_emitter.release_all.call_count == 2
        assert daemon._ptt_active is False

    @pytest.mark.asyncio
    async def test_process_button_events_checks_timeout_for_hold_gesture(self, ptt_daemon_parts):
        """Main loop event processing should feed timeout ticks to gesture logic."""
        device, audio_backend, state_machine, led_controller, key_emitter = ptt_daemon_parts
        daemon = MuteMeDaemon(
            device=device,
            audio_backend=audio_backend,
            state_machine=state_machine,
            led_controller=led_controller,
            key_emitter=key_emitter,
        )
        device.read_events.return_value = []
        state_machine.process_event.return_value = []

        await daemon._process_button_events()

        assert state_machine.process_event.call_count == 1
        timeout_event = state_machine.process_event.call_args.args[0]
        assert timeout_event.type == "timeout"
