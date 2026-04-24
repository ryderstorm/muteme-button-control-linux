"""Synthetic F19 key emission for hold-to-talk mode."""

from collections.abc import Callable
from enum import IntEnum
from importlib import import_module
from typing import Any, Protocol


class KeyEmitterError(RuntimeError):
    """Raised when synthetic key emission cannot be initialized or used."""


class KeyCode(IntEnum):
    """Internal key codes used by the key-emitter abstraction."""

    F19 = 194


class KeyDevice(Protocol):
    """Minimal device protocol required by F19KeyEmitter."""

    def write(self, key_code: KeyCode, value: int) -> None:
        """Write key state where value 1=down and 0=up."""

    def syn(self) -> None:
        """Synchronize the emitted input event."""

    def close(self) -> None:
        """Close any underlying resources."""


class EvdevKeyDevice:
    """Linux evdev/uinput implementation for synthetic key events."""

    def __init__(self) -> None:
        """Create a uinput device that can emit F19."""
        try:
            evdev: Any = import_module("evdev")
        except ImportError as exc:  # pragma: no cover - exercised by integration/manual use
            raise KeyEmitterError(
                "PTT mode requires the 'evdev' Python package for F19 key emulation."
            ) from exc

        try:
            self._ecodes = evdev.ecodes
            self._device = evdev.UInput(
                {evdev.ecodes.EV_KEY: [evdev.ecodes.KEY_F19]}, name="muteme-btn-ptt"
            )
        except Exception as exc:  # pragma: no cover - depends on host uinput permissions
            raise KeyEmitterError(
                "Failed to create Linux uinput device for F19 emulation. "
                "Ensure /dev/uinput exists and the current user has permission to write it."
            ) from exc

    def write(self, key_code: KeyCode, value: int) -> None:
        """Write key state where value 1=down and 0=up."""
        if key_code != KeyCode.F19:
            raise KeyEmitterError(f"Unsupported key code: {key_code}")
        self._device.write(self._ecodes.EV_KEY, self._ecodes.KEY_F19, value)

    def syn(self) -> None:
        """Synchronize the emitted input event."""
        self._device.syn()

    def close(self) -> None:
        """Close the uinput device."""
        self._device.close()


class F19KeyEmitter:
    """Idempotent synthetic F19 key-down/key-up emitter."""

    def __init__(self, device_factory: Callable[[], KeyDevice] | None = None) -> None:
        """Initialize the emitter with an optional device factory for tests."""
        self._device_factory = device_factory or EvdevKeyDevice
        self._device: KeyDevice | None = None
        self._is_pressed = False

    @property
    def is_pressed(self) -> bool:
        """Return whether F19 is logically held by this emitter."""
        return self._is_pressed

    def _get_device(self) -> KeyDevice:
        """Create the backing key device lazily."""
        if self._device is None:
            self._device = self._device_factory()
        return self._device

    def press_f19(self) -> None:
        """Emit F19 key down unless it is already logically pressed."""
        if self._is_pressed:
            return
        device = self._get_device()
        device.write(KeyCode.F19, 1)
        device.syn()
        self._is_pressed = True

    def release_f19(self) -> None:
        """Emit F19 key up unless it is already logically released."""
        if not self._is_pressed:
            return
        device = self._get_device()
        device.write(KeyCode.F19, 0)
        device.syn()
        self._is_pressed = False

    def release_all(self) -> None:
        """Release any logically held synthetic keys."""
        self.release_f19()

    def close(self) -> None:
        """Release keys and close the backing device if it was created."""
        self.release_all()
        if self._device is not None:
            self._device.close()
            self._device = None
