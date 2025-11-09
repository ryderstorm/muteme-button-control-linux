"""Button state machine for toggle logic and button event handling."""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ButtonState(Enum):
    """Button states for the state machine."""

    IDLE = "idle"
    PRESSED = "pressed"


@dataclass
class ButtonEvent:
    """Button event data structure."""

    type: str  # "press", "release", "timeout"
    timestamp: datetime


class ButtonStateMachine:
    """State machine for handling button press events and toggle logic."""

    def __init__(self, double_tap_timeout_ms: int = 300, debounce_time_ms: int = 10):
        """Initialize button state machine.

        Args:
            double_tap_timeout_ms: Timeout for double-tap detection in milliseconds
            debounce_time_ms: Minimum time between events to prevent bouncing
        """
        self.current_state: ButtonState = ButtonState.IDLE
        self.last_press_time: datetime | None = None
        self.press_count: int = 0
        self.state_entry_time: datetime = datetime.now()

        self.double_tap_timeout_ms = double_tap_timeout_ms
        self.debounce_time_ms = debounce_time_ms

        logger.debug(
            f"Initialized ButtonStateMachine with "
            f"double_tap_timeout={double_tap_timeout_ms}ms, "
            f"debounce_time={debounce_time_ms}ms"
        )

    def process_event(self, event: ButtonEvent) -> list[str]:
        """Process a button event and return any actions to be taken.

        Args:
            event: Button event to process

        Returns:
            List of action strings to be executed (e.g., ["toggle"])
        """
        # Check for debouncing
        if self._should_debounce_event(event):
            logger.debug(f"Debouncing event: {event.type}")
            return []

        actions: list[str] = []

        try:
            if self.current_state == ButtonState.IDLE:
                actions = self._handle_idle_state(event)
            elif self.current_state == ButtonState.PRESSED:
                actions = self._handle_pressed_state(event)
            else:
                logger.warning(f"Unknown state: {self.current_state}")

        except Exception as e:
            logger.error(f"Error processing event {event.type} in state {self.current_state}: {e}")
            # Reset to safe state on error
            self.reset()

        return actions

    def _should_debounce_event(self, event: ButtonEvent) -> bool:
        """Check if an event should be debounced (ignored due to rapid timing)."""
        # Only debounce press events, not release events
        if event.type != "press":
            return False

        if self.last_press_time is None:
            return False

        time_since_last = (event.timestamp - self.last_press_time).total_seconds() * 1000
        return time_since_last < self.debounce_time_ms

    def _handle_idle_state(self, event: ButtonEvent) -> list[str]:
        """Handle events when in IDLE state."""
        actions: list[str] = []

        if event.type == "press":
            now = event.timestamp
            # Check if this press is within the double-tap timeout window
            if (
                self.last_press_time
                and (now - self.last_press_time).total_seconds() * 1000
                <= self.double_tap_timeout_ms
            ):
                self.press_count += 1
                logger.debug(f"Double-tap window hit (press #{self.press_count})")
            else:
                self.press_count = 1
            self.last_press_time = now
            self.current_state = ButtonState.PRESSED
            self.state_entry_time = now
            logger.debug(f"Transitioned to PRESSED state (press #{self.press_count})")

        elif event.type == "timeout":
            # Check if we should reset due to timeout
            if self._should_timeout(event.timestamp):
                self._reset_press_count()
                logger.debug("Timeout reset press count")

        return actions

    def _handle_pressed_state(self, event: ButtonEvent) -> list[str]:
        """Handle events when in PRESSED state."""
        actions: list[str] = []

        if event.type == "release":
            # Trigger toggle action on release
            actions.append("toggle")

            # Check for double-tap
            if self.press_count >= 2:
                actions.append("double_tap")
                self.press_count = 0
                self.last_press_time = None

            # Return to idle state
            self.current_state = ButtonState.IDLE
            self.state_entry_time = event.timestamp
            logger.debug("Toggle action triggered, returned to IDLE state")

        elif event.type == "press":
            # Another press while already pressed (could be double-tap)
            if self.last_press_time is None:
                time_since_last = float("inf")
            else:
                time_since_last = (event.timestamp - self.last_press_time).total_seconds() * 1000

            if time_since_last < self.double_tap_timeout_ms:
                self.press_count += 1
                self.last_press_time = event.timestamp
                logger.debug(f"Double-tap detected (press #{self.press_count})")
            else:
                # Treat as new press sequence
                self.press_count = 1
                self.last_press_time = event.timestamp
                logger.debug(f"New press sequence (press #{self.press_count})")

        return actions

    def _should_timeout(self, current_time: datetime) -> bool:
        """Check if the state should timeout due to inactivity."""
        if self.last_press_time is None:
            return False

        time_since_last = (current_time - self.last_press_time).total_seconds() * 1000
        return time_since_last > self.double_tap_timeout_ms

    def _reset_press_count(self) -> None:
        """Reset the press count and related state."""
        self.press_count = 0
        self.last_press_time = None

    def reset(self) -> None:
        """Reset the state machine to initial state."""
        self.current_state = ButtonState.IDLE
        self.last_press_time = None
        self.press_count = 0
        self.state_entry_time = datetime.now()
        logger.debug("State machine reset to IDLE state")

    def get_state_info(self) -> dict[str, Any]:
        """Get current state information for debugging/monitoring.

        Returns:
            Dictionary containing current state information
        """
        duration_in_state = (datetime.now() - self.state_entry_time).total_seconds()

        return {
            "state": self.current_state,
            "press_count": self.press_count,
            "last_press_time": self.last_press_time,
            "duration_in_state": duration_in_state,
            "double_tap_timeout_ms": self.double_tap_timeout_ms,
            "debounce_time_ms": self.debounce_time_ms,
        }
