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
        switch_gesture: str = "double_tap_hold",
        triple_tap_count: int = 3,
        triple_tap_window_ms: int = 650,
        tap_max_duration_ms: int = 140,
        inter_tap_timeout_ms: int = 275,
        ptt_hold_threshold_ms: int = 120,
    ):
        """Initialize button state machine."""
        self.current_state: ButtonState = ButtonState.IDLE
        self.current_mode: OperationMode = OperationMode(default_mode)
        self.last_press_time: datetime | None = None
        self.press_count: int = 0
        self.state_entry_time: datetime = datetime.now()
        self._suppress_next_release = False
        self._switch_fired_for_current_press = False

        self.switch_gesture = self._validate_switch_gesture(switch_gesture)
        self.double_tap_timeout_ms = self._validate_positive_int(
            "double_tap_timeout_ms", double_tap_timeout_ms
        )
        self.debounce_time_ms = self._validate_non_negative_int(
            "debounce_time_ms", debounce_time_ms
        )
        self.switch_hold_threshold_ms = self._validate_positive_int(
            "switch_hold_threshold_ms", switch_hold_threshold_ms
        )
        self.triple_tap_count = self._validate_positive_int("triple_tap_count", triple_tap_count)
        self.triple_tap_window_ms = self._validate_positive_int(
            "triple_tap_window_ms", triple_tap_window_ms
        )
        self.tap_max_duration_ms = self._validate_positive_int(
            "tap_max_duration_ms", tap_max_duration_ms
        )
        self.inter_tap_timeout_ms = self._validate_positive_int(
            "inter_tap_timeout_ms", inter_tap_timeout_ms
        )
        self.ptt_hold_threshold_ms = self._validate_positive_int(
            "ptt_hold_threshold_ms", ptt_hold_threshold_ms
        )

        self._triple_sequence_start_time: datetime | None = None
        self._last_tap_release_time: datetime | None = None
        self._ptt_hold_active = False

        logger.debug(
            "Initialized ButtonStateMachine with "
            f"mode={self.current_mode.value}, "
            f"switch_gesture={self.switch_gesture}, "
            f"double_tap_timeout={double_tap_timeout_ms}ms, "
            f"switch_hold_threshold={switch_hold_threshold_ms}ms, "
            f"triple_tap_window={triple_tap_window_ms}ms, "
            f"inter_tap_timeout={inter_tap_timeout_ms}ms, "
            f"ptt_hold_threshold={ptt_hold_threshold_ms}ms, "
            f"debounce_time={debounce_time_ms}ms"
        )

    @staticmethod
    def _validate_switch_gesture(value: str) -> str:
        """Validate the supported mode-switch gesture for direct callers."""
        normalized = value.lower()
        if normalized not in {"double_tap_hold", "triple_tap"}:
            raise ValueError("Unsupported switch_gesture; expected double_tap_hold or triple_tap")
        return normalized

    @staticmethod
    def _validate_positive_int(option: str, value: int) -> int:
        """Validate timing/count options that must be positive."""
        if value <= 0:
            raise ValueError(f"{option} must be greater than 0")
        return value

    @staticmethod
    def _validate_non_negative_int(option: str, value: int) -> int:
        """Validate timing options that may be zero but not negative."""
        if value < 0:
            raise ValueError(f"{option} must be greater than or equal to 0")
        return value

    def process_event(self, event: ButtonEvent) -> list[str]:
        """Process a button event and return action strings to execute."""
        if self._should_debounce_event(event):
            logger.debug(f"Debouncing event: {event.type}")
            return []

        try:
            if self.switch_gesture == "triple_tap":
                return self._process_triple_tap_event(event)
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
        """Handle events when in IDLE state for double-tap-hold mode."""
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
            if self.current_mode == OperationMode.PTT:
                self._ptt_hold_active = True
                return ["ptt_press"]
            return []

        if event.type == "timeout" and self._should_timeout(event.timestamp):
            self._reset_press_count()
            logger.debug("Timeout reset press count")

        return []

    def _handle_pressed_state(self, event: ButtonEvent) -> list[str]:
        """Handle events when in PRESSED state for double-tap-hold mode."""
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

        self._switch_modes()
        self._switch_fired_for_current_press = True
        self._suppress_next_release = True
        self._reset_press_count()
        logger.info(f"Switched button mode to {self.current_mode.value}")
        return ["switch_mode"]

    def _handle_release(self, event: ButtonEvent) -> list[str]:
        """Handle button release in the current operating mode."""
        if self._suppress_next_release:
            self._suppress_next_release = False
            self.current_state = ButtonState.IDLE
            self.state_entry_time = event.timestamp
            actions = ["ptt_release"] if self._ptt_hold_active else []
            self._ptt_hold_active = False
            logger.debug("Suppressed release after mode-switch gesture")
            return actions

        actions: list[str]
        if self.current_mode == OperationMode.PTT:
            actions = ["ptt_release"]
            self._ptt_hold_active = False
        else:
            actions = ["toggle"]
            if self.press_count >= 2:
                actions.append("double_tap")
                self._reset_press_count()

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

    def _process_triple_tap_event(self, event: ButtonEvent) -> list[str]:
        """Handle optional triple-tap mode switching with deferred quick-tap actions."""
        if self.current_state == ButtonState.IDLE:
            return self._handle_triple_idle(event)
        if self.current_state == ButtonState.PRESSED:
            return self._handle_triple_pressed(event)
        logger.warning(f"Unknown state: {self.current_state}")
        return []

    def _handle_triple_idle(self, event: ButtonEvent) -> list[str]:
        """Handle triple-tap events while idle."""
        if event.type == "timeout":
            return self._commit_expired_triple_tap_sequence(event.timestamp)

        if event.type != "press":
            return []

        actions = self._commit_expired_triple_tap_sequence(event.timestamp)
        self.current_state = ButtonState.PRESSED
        self.state_entry_time = event.timestamp
        self.last_press_time = event.timestamp
        self._ptt_hold_active = False
        return actions

    def _handle_triple_pressed(self, event: ButtonEvent) -> list[str]:
        """Handle triple-tap events while pressed."""
        if event.type == "timeout":
            return self._handle_triple_pressed_timeout(event)
        if event.type == "release":
            return self._handle_triple_release(event)
        if event.type == "press":
            return []
        return []

    def _handle_triple_pressed_timeout(self, event: ButtonEvent) -> list[str]:
        """Start PTT only after a quick tap has become an intentional hold."""
        if self.current_mode != OperationMode.PTT or self._ptt_hold_active:
            return []

        held_ms = (event.timestamp - self.state_entry_time).total_seconds() * 1000
        if held_ms < self.ptt_hold_threshold_ms:
            return []

        self._ptt_hold_active = True
        self._clear_triple_tap_sequence()
        return ["ptt_press"]

    def _handle_triple_release(self, event: ButtonEvent) -> list[str]:
        """Handle a release for triple-tap switching."""
        self.current_state = ButtonState.IDLE
        self.state_entry_time = event.timestamp

        if self._ptt_hold_active:
            self._ptt_hold_active = False
            self._clear_triple_tap_sequence()
            return ["ptt_release"]

        held_ms = (
            (event.timestamp - self.last_press_time).total_seconds() * 1000
            if self.last_press_time is not None
            else 0
        )

        if held_ms > self.tap_max_duration_ms:
            self._clear_triple_tap_sequence()
            return ["toggle"] if self.current_mode == OperationMode.NORMAL else []

        return self._record_quick_tap(event.timestamp)

    def _record_quick_tap(self, release_time: datetime) -> list[str]:
        """Record a quick tap and switch modes if the sequence is complete."""
        if self._should_start_new_triple_sequence(release_time):
            self._clear_triple_tap_sequence()

        if self._triple_sequence_start_time is None:
            self._triple_sequence_start_time = self.last_press_time or release_time

        self.press_count += 1
        self._last_tap_release_time = release_time

        sequence_ms = (release_time - self._triple_sequence_start_time).total_seconds() * 1000
        if self.press_count >= self.triple_tap_count and sequence_ms <= self.triple_tap_window_ms:
            self._switch_modes()
            self._clear_triple_tap_sequence()
            logger.info(f"Switched button mode to {self.current_mode.value}")
            return ["switch_mode"]

        if sequence_ms > self.triple_tap_window_ms:
            self._clear_triple_tap_sequence()
            return ["toggle"] if self.current_mode == OperationMode.NORMAL else []

        return []

    def _commit_expired_triple_tap_sequence(self, current_time: datetime) -> list[str]:
        """Commit deferred quick-tap behavior after the next-tap timeout expires."""
        if self.press_count == 0 or self._last_tap_release_time is None:
            return []

        elapsed_ms = (current_time - self._last_tap_release_time).total_seconds() * 1000
        if elapsed_ms <= self.inter_tap_timeout_ms:
            return []

        actions = ["toggle"] if self.current_mode == OperationMode.NORMAL else []
        self._clear_triple_tap_sequence()
        return actions

    def _should_start_new_triple_sequence(self, release_time: datetime) -> bool:
        """Check whether this tap should start a new triple-tap sequence."""
        if self.press_count == 0:
            return False
        if self._triple_sequence_start_time is None or self._last_tap_release_time is None:
            return True

        total_ms = (release_time - self._triple_sequence_start_time).total_seconds() * 1000
        if total_ms > self.triple_tap_window_ms:
            return True

        gap_ms = 0.0
        if self.last_press_time is not None:
            gap_ms = (self.last_press_time - self._last_tap_release_time).total_seconds() * 1000
        return gap_ms > self.inter_tap_timeout_ms

    def _clear_triple_tap_sequence(self) -> None:
        """Reset pending triple-tap sequence state."""
        self.press_count = 0
        self._triple_sequence_start_time = None
        self._last_tap_release_time = None

    def _switch_modes(self) -> None:
        """Toggle between normal and push-to-talk modes."""
        self.current_mode = (
            OperationMode.PTT if self.current_mode == OperationMode.NORMAL else OperationMode.NORMAL
        )

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
        self._ptt_hold_active = False
        self._triple_sequence_start_time = None
        self._last_tap_release_time = None
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
            "switch_gesture": self.switch_gesture,
            "double_tap_timeout_ms": self.double_tap_timeout_ms,
            "switch_hold_threshold_ms": self.switch_hold_threshold_ms,
            "triple_tap_count": self.triple_tap_count,
            "triple_tap_window_ms": self.triple_tap_window_ms,
            "tap_max_duration_ms": self.tap_max_duration_ms,
            "inter_tap_timeout_ms": self.inter_tap_timeout_ms,
            "ptt_hold_threshold_ms": self.ptt_hold_threshold_ms,
            "debounce_time_ms": self.debounce_time_ms,
        }
