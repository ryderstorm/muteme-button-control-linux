"""Tests for button state machine implementation."""

from datetime import datetime, timedelta

import pytest

from muteme_btn.core.state import ButtonEvent, ButtonState, ButtonStateMachine, OperationMode


class TestButtonStateMachine:
    """Test suite for button state machine."""

    @pytest.fixture
    def state_machine(self):
        """Create a button state machine instance."""
        return ButtonStateMachine()

    def test_initial_state(self, state_machine):
        """Test state machine starts in correct initial state."""
        assert state_machine.current_state == ButtonState.IDLE
        assert state_machine.last_press_time is None
        assert state_machine.press_count == 0

    def test_button_press_in_idle_state(self, state_machine):
        """Test handling button press from IDLE state."""
        event = ButtonEvent(type="press", timestamp=datetime.now())

        actions = state_machine.process_event(event)

        assert state_machine.current_state == ButtonState.PRESSED
        assert state_machine.last_press_time == event.timestamp
        assert state_machine.press_count == 1
        assert actions == []  # No actions on press

    def test_button_release_in_pressed_state(self, state_machine):
        """Test handling button release from PRESSED state."""
        # First press to get into PRESSED state
        press_event = ButtonEvent(type="press", timestamp=datetime.now())
        state_machine.process_event(press_event)

        # Now release
        release_event = ButtonEvent(type="release", timestamp=datetime.now())
        actions = state_machine.process_event(release_event)

        assert state_machine.current_state == ButtonState.IDLE
        assert "toggle" in actions

    def test_toggle_action_on_complete_press(self, state_machine):
        """Test that toggle action is triggered on complete press-release cycle."""
        press_time = datetime.now()
        release_time = press_time + timedelta(milliseconds=100)

        # Press
        press_event = ButtonEvent(type="press", timestamp=press_time)
        state_machine.process_event(press_event)

        # Release - should trigger toggle
        release_event = ButtonEvent(type="release", timestamp=release_time)
        actions = state_machine.process_event(release_event)

        assert "toggle" in actions
        assert len(actions) == 1

    def test_double_tap_detection(self, state_machine):
        """Test double-tap detection within timeout window."""
        now = datetime.now()

        # First press-release cycle
        press1 = ButtonEvent(type="press", timestamp=now)
        state_machine.process_event(press1)
        release1 = ButtonEvent(type="release", timestamp=now + timedelta(milliseconds=100))
        state_machine.process_event(release1)

        # Second press within double-tap window (300ms)
        press2 = ButtonEvent(type="press", timestamp=now + timedelta(milliseconds=200))
        state_machine.process_event(press2)
        release2 = ButtonEvent(type="release", timestamp=now + timedelta(milliseconds=300))
        actions = state_machine.process_event(release2)

        # After double-tap detection, press_count is reset to 0
        assert state_machine.press_count == 0
        # Should trigger both toggle and double_tap actions
        assert "toggle" in actions
        assert "double_tap" in actions

    def test_timeout_handling(self, state_machine):
        """Test timeout resets press count."""
        now = datetime.now()

        # Press and release
        press = ButtonEvent(type="press", timestamp=now)
        state_machine.process_event(press)
        release = ButtonEvent(type="release", timestamp=now + timedelta(milliseconds=100))
        state_machine.process_event(release)

        # Simulate timeout by processing a time-based event
        timeout_event = ButtonEvent(type="timeout", timestamp=now + timedelta(seconds=1))
        state_machine.process_event(timeout_event)

        assert state_machine.press_count == 0
        assert state_machine.current_state == ButtonState.IDLE

    def test_debounce_ignores_rapid_events(self, state_machine):
        """Test that very rapid events are debounced."""
        now = datetime.now()

        # Rapid press events within 10ms
        press1 = ButtonEvent(type="press", timestamp=now)
        press2 = ButtonEvent(type="press", timestamp=now + timedelta(milliseconds=5))

        state_machine.process_event(press1)
        # Second press should be ignored due to debouncing
        actions = state_machine.process_event(press2)

        assert state_machine.press_count == 1
        assert not actions  # No actions from debounced event

    def test_press_while_pressed_state(self, state_machine):
        """Test handling press event while already in PRESSED state.

        This tests the edge case where a second press arrives before the release,
        which can happen with hardware edge cases or missed release events.
        """
        now = datetime.now()

        # First press - enters PRESSED state
        press1 = ButtonEvent(type="press", timestamp=now)
        state_machine.process_event(press1)
        assert state_machine.current_state == ButtonState.PRESSED
        assert state_machine.press_count == 1

        # Second press while still in PRESSED state
        # (after debounce threshold but within double-tap window)
        # Use 50ms - enough to pass debounce (10ms) but within double-tap timeout (300ms)
        press2 = ButtonEvent(type="press", timestamp=now + timedelta(milliseconds=50))
        actions = state_machine.process_event(press2)

        # Should increment press_count and remain in PRESSED state
        assert state_machine.current_state == ButtonState.PRESSED
        assert state_machine.press_count == 2
        assert not actions  # No actions until release

        # Now release - should trigger double-tap
        release = ButtonEvent(type="release", timestamp=now + timedelta(milliseconds=100))
        actions = state_machine.process_event(release)

        # Should detect double-tap and return to IDLE
        assert state_machine.current_state == ButtonState.IDLE
        assert "toggle" in actions
        assert "double_tap" in actions
        assert state_machine.press_count == 0  # Reset after double-tap

    def test_press_while_pressed_exceeds_timeout(self, state_machine):
        """Test press while PRESSED that exceeds double-tap timeout is treated as new sequence."""
        now = datetime.now()

        # First press
        press1 = ButtonEvent(type="press", timestamp=now)
        state_machine.process_event(press1)
        assert state_machine.press_count == 1

        # Second press after timeout window (> 300ms)
        press2 = ButtonEvent(type="press", timestamp=now + timedelta(milliseconds=400))
        state_machine.process_event(press2)

        # Should reset press_count to 1 (new sequence)
        assert state_machine.current_state == ButtonState.PRESSED
        assert state_machine.press_count == 1

        # Release should only trigger single toggle, not double-tap
        release = ButtonEvent(type="release", timestamp=now + timedelta(milliseconds=500))
        actions = state_machine.process_event(release)

        assert state_machine.current_state == ButtonState.IDLE
        assert "toggle" in actions
        assert "double_tap" not in actions

    def test_invalid_event_handling(self, state_machine):
        """Test handling of unknown event types."""
        invalid_event = ButtonEvent(type="unknown", timestamp=datetime.now())

        actions = state_machine.process_event(invalid_event)

        assert state_machine.current_state == ButtonState.IDLE
        assert not actions

    def test_state_reset(self, state_machine):
        """Test manual state reset functionality."""
        # Put machine in a non-idle state
        press_event = ButtonEvent(type="press", timestamp=datetime.now())
        state_machine.process_event(press_event)

        assert state_machine.current_state == ButtonState.PRESSED
        assert state_machine.press_count == 1

        # Reset
        state_machine.reset()

        assert state_machine.current_state == ButtonState.IDLE
        assert state_machine.press_count == 0
        assert state_machine.last_press_time is None

    def test_get_state_info(self, state_machine):
        """Test getting current state information."""
        info = state_machine.get_state_info()

        assert info["state"] == ButtonState.IDLE
        assert info["press_count"] == 0
        assert info["last_press_time"] is None
        assert "duration_in_state" in info

    def test_async_action_processing(self, state_machine):
        """Test that actions can be processed asynchronously."""
        # This tests the interface for async action handling
        press_event = ButtonEvent(type="press", timestamp=datetime.now())
        state_machine.process_event(press_event)

        release_event = ButtonEvent(type="release", timestamp=datetime.now())
        actions = state_machine.process_event(release_event)

        # Actions should be returned for async processing
        assert isinstance(actions, list)
        assert "toggle" in actions

    def test_configurable_double_tap_timeout(self):
        """Test configurable double-tap timeout."""
        custom_timeout = 500  # ms
        machine = ButtonStateMachine(double_tap_timeout_ms=custom_timeout)

        assert machine.double_tap_timeout_ms == custom_timeout

    def test_configurable_debounce_time(self):
        """Test configurable debounce time."""
        custom_debounce = 20  # ms
        machine = ButtonStateMachine(debounce_time_ms=custom_debounce)

        assert machine.debounce_time_ms == custom_debounce


class TestDualModeButtonStateMachine:
    """Tests for normal/PTT mode behavior and double-tap-hold switching."""

    def test_ptt_mode_press_and_release_emit_hold_actions_without_toggle(self):
        """PTT mode should emit hold actions instead of toggles."""
        machine = ButtonStateMachine(default_mode=OperationMode.PTT)
        now = datetime.now()

        press_actions = machine.process_event(ButtonEvent(type="press", timestamp=now))
        release_actions = machine.process_event(
            ButtonEvent(type="release", timestamp=now + timedelta(milliseconds=200))
        )

        assert press_actions == ["ptt_press"]
        assert release_actions == ["ptt_release"]

    def test_double_tap_hold_switches_from_normal_to_ptt(self):
        """Double-tap-and-hold should deliberately switch operating modes."""
        machine = ButtonStateMachine(switch_hold_threshold_ms=800)
        now = datetime.now()

        assert machine.process_event(ButtonEvent(type="press", timestamp=now)) == []
        assert machine.process_event(
            ButtonEvent(type="release", timestamp=now + timedelta(milliseconds=80))
        ) == ["toggle"]
        assert (
            machine.process_event(
                ButtonEvent(type="press", timestamp=now + timedelta(milliseconds=180))
            )
            == []
        )

        actions = machine.process_event(
            ButtonEvent(type="timeout", timestamp=now + timedelta(milliseconds=1000))
        )

        assert actions == ["switch_mode"]
        assert machine.current_mode == OperationMode.PTT

        # Releasing the held switch gesture should not start or stop PTT.
        release_actions = machine.process_event(
            ButtonEvent(type="release", timestamp=now + timedelta(milliseconds=1050))
        )
        assert release_actions == []

    def test_short_double_tap_does_not_switch_modes(self):
        """A plain quick double-tap remains non-switching behavior."""
        machine = ButtonStateMachine(switch_hold_threshold_ms=800)
        now = datetime.now()

        machine.process_event(ButtonEvent(type="press", timestamp=now))
        machine.process_event(
            ButtonEvent(type="release", timestamp=now + timedelta(milliseconds=80))
        )
        machine.process_event(
            ButtonEvent(type="press", timestamp=now + timedelta(milliseconds=180))
        )
        actions = machine.process_event(
            ButtonEvent(type="release", timestamp=now + timedelta(milliseconds=260))
        )

        assert "switch_mode" not in actions
        assert machine.current_mode == OperationMode.NORMAL

    def test_get_state_info_includes_current_mode(self):
        """State diagnostics should expose the current operating mode."""
        machine = ButtonStateMachine(default_mode=OperationMode.PTT)

        info = machine.get_state_info()

        assert info["mode"] == OperationMode.PTT


class TestTripleTapModeSwitching:
    """Tests for optional triple-tap mode switching."""

    def _event(self, event_type: str, base: datetime, ms: int) -> ButtonEvent:
        return ButtonEvent(type=event_type, timestamp=base + timedelta(milliseconds=ms))

    def test_triple_tap_switches_modes_without_intermediate_toggles(self):
        """Three quick taps should switch modes and suppress pending toggles."""
        machine = ButtonStateMachine(switch_gesture="triple_tap")
        now = datetime.now()

        assert machine.process_event(self._event("press", now, 0)) == []
        assert machine.process_event(self._event("release", now, 80)) == []
        assert machine.process_event(self._event("press", now, 230)) == []
        assert machine.process_event(self._event("release", now, 300)) == []
        assert machine.process_event(self._event("press", now, 450)) == []
        actions = machine.process_event(self._event("release", now, 530))

        assert actions == ["switch_mode"]
        assert machine.current_mode == OperationMode.PTT
        assert machine.press_count == 0

    def test_single_triple_tap_candidate_commits_toggle_after_inter_tap_timeout(self):
        """A lone quick tap in normal mode should toggle after the next-tap window expires."""
        machine = ButtonStateMachine(switch_gesture="triple_tap", inter_tap_timeout_ms=275)
        now = datetime.now()

        assert machine.process_event(self._event("press", now, 0)) == []
        assert machine.process_event(self._event("release", now, 70)) == []
        assert machine.process_event(self._event("timeout", now, 300)) == []
        actions = machine.process_event(self._event("timeout", now, 360))

        assert actions == ["toggle"]
        assert machine.current_mode == OperationMode.NORMAL

    def test_slow_third_tap_does_not_switch_modes(self):
        """Triple taps outside the sequence window should not switch modes."""
        machine = ButtonStateMachine(
            switch_gesture="triple_tap",
            triple_tap_window_ms=650,
            inter_tap_timeout_ms=275,
        )
        now = datetime.now()

        machine.process_event(self._event("press", now, 0))
        machine.process_event(self._event("release", now, 80))
        machine.process_event(self._event("press", now, 230))
        machine.process_event(self._event("release", now, 300))
        assert machine.process_event(self._event("timeout", now, 576)) == ["toggle"]
        assert machine.process_event(self._event("press", now, 800)) == []
        assert machine.process_event(self._event("release", now, 880)) == []

        assert machine.current_mode == OperationMode.NORMAL

    def test_ptt_triple_tap_switches_modes_without_f19_pulses(self):
        """Quick triple taps in PTT mode should switch modes without tiny PTT pulses."""
        machine = ButtonStateMachine(
            default_mode=OperationMode.PTT,
            switch_gesture="triple_tap",
            ptt_hold_threshold_ms=120,
        )
        now = datetime.now()

        assert machine.process_event(self._event("press", now, 0)) == []
        assert machine.process_event(self._event("release", now, 70)) == []
        assert machine.process_event(self._event("press", now, 220)) == []
        assert machine.process_event(self._event("release", now, 290)) == []
        assert machine.process_event(self._event("press", now, 440)) == []
        actions = machine.process_event(self._event("release", now, 510))

        assert actions == ["switch_mode"]
        assert machine.current_mode == OperationMode.NORMAL

    def test_ptt_hold_starts_after_hold_threshold_and_releases_normally(self):
        """PTT mode should separate quick tap candidates from intentional holds."""
        machine = ButtonStateMachine(
            default_mode=OperationMode.PTT,
            switch_gesture="triple_tap",
            ptt_hold_threshold_ms=120,
        )
        now = datetime.now()

        assert machine.process_event(self._event("press", now, 0)) == []
        assert machine.process_event(self._event("timeout", now, 119)) == []
        assert machine.process_event(self._event("timeout", now, 120)) == ["ptt_press"]
        assert machine.process_event(self._event("release", now, 350)) == ["ptt_release"]
        assert machine.current_mode == OperationMode.PTT
