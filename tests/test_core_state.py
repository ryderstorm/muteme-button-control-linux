"""Tests for button state machine implementation."""

from datetime import datetime, timedelta

import pytest

from muteme_btn.core.state import ButtonEvent, ButtonState, ButtonStateMachine


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

        assert state_machine.press_count == 2
        # Should still trigger toggle for now (basic toggle mode)
        assert "toggle" in actions

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
