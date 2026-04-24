"""Button state machine for toggle, PTT, and mode-switch logic."""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from muteme_btn.config import OperationMode

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
    """State machine for button press events, mode switching, and actions."""

    def __init__(
        self,
        double_tap_timeout_ms: int = 300,
        debounce_time_ms: int = 10,
        default_mode: OperationMode = OperationMode.NORMAL,
        switch_hold_threshold_ms: int = 800,
    ):
        """Initialize button state machine."""
        self.current_state: ButtonState = ButtonState.IDLE
        self.current_mode: OperationMode = OperationMode(default_mode)
        self.last_press_time: datetime | None = None
        self.press_count: int = 0
        self.state_entry_time: datetime = datetime.now()
        self._suppress_next_release = False
        self._switch_fired_for_current_press = False

        self.double_tap_timeout_ms = double_tap_timeout_ms
        self.debounce_time_ms = debounce_time_ms
        self.switch_hold_threshold_ms = switch_hold_threshold_ms

        logger.debug(
            "Initialized ButtonStateMachine with "
            f"mode={self.current_mode.value}, "
            f"double_tap_timeout={double_tap_timeout_ms}ms, "
            f"switch_hold_threshold={switch_hold_threshold_ms}ms, "
            f"debounce_time={debounce_time_ms}ms"
        )

    def process_event(self, event: ButtonEvent) -> list[str]:
        """Process a button event and return action strings to execute."""
        if self._should_debounce_event(event):
            logger.debug(f"Debouncing event: {event.type}")
            return []

        try:
            if self.current_state == ButtonState.IDLE:
                return self._handle_idle_state(event)
            if self.current_state == ButtonState.PRESSED:
                return self._handle_pressed_state(event)
            logger.warning(f"Unknown state: {self.current_state}")
        except Exception as e:
            logger.error(f"Error processing event {event.type} in state {self.current_state}: {e}")
            self.reset()

        return []

    def _should_debounce_event(self, event: ButtonEvent) -> bool:
        """Check if an event should be debounced."""
        if event.type != "press":
            return False
        if self.last_press_time is None:
            return False
        time_since_last = (event.timestamp - self.last_press_time).total_seconds() * 1000
        return time_since_last < self.debounce_time_ms

    def _handle_idle_state(self, event: ButtonEvent) -> list[str]:
        """Handle events when in IDLE state."""
        if event.type == "press":
            now = event.timestamp
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
            self._switch_fired_for_current_press = False
            logger.debug(f"Transitioned to PRESSED state (press #{self.press_count})")
            return ["ptt_press"] if self.current_mode == OperationMode.PTT else []

        if event.type == "timeout" and self._should_timeout(event.timestamp):
            self._reset_press_count()
            logger.debug("Timeout reset press count")

        return []

    def _handle_pressed_state(self, event: ButtonEvent) -> list[str]:
        """Handle events when in PRESSED state."""
        if event.type == "timeout":
            return self._handle_pressed_timeout(event)

        if event.type == "release":
            return self._handle_release(event)

        if event.type == "press":
            self._handle_extra_press(event)

        return []

    def _handle_pressed_timeout(self, event: ButtonEvent) -> list[str]:
        """Handle hold-timeout checks while the button remains pressed."""
        if self.press_count < 2 or self._switch_fired_for_current_press:
            return []

        held_ms = (event.timestamp - self.state_entry_time).total_seconds() * 1000
        if held_ms < self.switch_hold_threshold_ms:
            return []

        self.current_mode = (
            OperationMode.PTT if self.current_mode == OperationMode.NORMAL else OperationMode.NORMAL
        )
        self._switch_fired_for_current_press = True
        self._suppress_next_release = True
        self.press_count = 0
        self.last_press_time = None
        logger.info(f"Switched button mode to {self.current_mode.value}")
        return ["switch_mode"]

    def _handle_release(self, event: ButtonEvent) -> list[str]:
        """Handle button release in the current operating mode."""
        if self._suppress_next_release:
            self._suppress_next_release = False
            self.current_state = ButtonState.IDLE
            self.state_entry_time = event.timestamp
            logger.debug("Suppressed release after mode-switch gesture")
            return []

        actions: list[str]
        if self.current_mode == OperationMode.PTT:
            actions = ["ptt_release"]
        else:
            actions = ["toggle"]
            if self.press_count >= 2:
                actions.append("double_tap")
                self.press_count = 0
                self.last_press_time = None

        self.current_state = ButtonState.IDLE
        self.state_entry_time = event.timestamp
        logger.debug("Release handled, returned to IDLE state")
        return actions

    def _handle_extra_press(self, event: ButtonEvent) -> None:
        """Handle unexpected repeated press events while already pressed."""
        if self.last_press_time is None:
            time_since_last = float("inf")
        else:
            time_since_last = (event.timestamp - self.last_press_time).total_seconds() * 1000

        if time_since_last < self.double_tap_timeout_ms:
            self.press_count += 1
            self.last_press_time = event.timestamp
            logger.debug(f"Double-tap detected (press #{self.press_count})")
        else:
            self.press_count = 1
            self.last_press_time = event.timestamp
            logger.debug(f"New press sequence (press #{self.press_count})")

    def _should_timeout(self, current_time: datetime) -> bool:
        """Check if the idle tap window should timeout due to inactivity."""
        if self.last_press_time is None:
            return False
        time_since_last = (current_time - self.last_press_time).total_seconds() * 1000
        return time_since_last > self.double_tap_timeout_ms

    def _reset_press_count(self) -> None:
        """Reset the press count and related state."""
        self.press_count = 0
        self.last_press_time = None

    def reset(self) -> None:
        """Reset the state machine to initial button state without changing mode."""
        self.current_state = ButtonState.IDLE
        self.last_press_time = None
        self.press_count = 0
        self._suppress_next_release = False
        self._switch_fired_for_current_press = False
        self.state_entry_time = datetime.now()
        logger.debug("State machine reset to IDLE state")

    def get_state_info(self) -> dict[str, Any]:
        """Get current state information for debugging/monitoring."""
        duration_in_state = (datetime.now() - self.state_entry_time).total_seconds()
        return {
            "state": self.current_state,
            "mode": self.current_mode,
            "press_count": self.press_count,
            "last_press_time": self.last_press_time,
            "duration_in_state": duration_in_state,
            "double_tap_timeout_ms": self.double_tap_timeout_ms,
            "switch_hold_threshold_ms": self.switch_hold_threshold_ms,
            "debounce_time_ms": self.debounce_time_ms,
        }
