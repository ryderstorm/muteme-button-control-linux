"""Synthetic F19 key emission for hold-to-talk mode."""

from collections.abc import Callable
from enum import IntEnum
from importlib import import_module
from os import environ
from pathlib import Path
from socket import AF_UNIX, SOCK_DGRAM, socket
from struct import Struct
from tempfile import gettempdir
from typing import Any, Protocol


class KeyEmitterError(RuntimeError):
    """Raised when synthetic key emission cannot be initialized or used."""


class KeyCode(IntEnum):
    """Internal key codes used by the key-emitter abstraction."""

    F19 = 189


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


class YdotoolKeyDevice:
    """ydotoold socket implementation for Utter-compatible synthetic key events."""

    _EVENT = Struct("@llHHi")
    _EV_SYN = 0
    _EV_KEY = 1
    _SYN_REPORT = 0

    def __init__(
        self,
        socket_path: str | None = None,
        sender: Callable[[bytes], None] | None = None,
    ) -> None:
        """Initialize with an injectable sender for tests."""
        self._socket_path = socket_path or self._default_socket_path()
        self._sender = sender

    @staticmethod
    def _default_socket_path() -> str:
        """Return the socket path used by ydotool's CLI fallback order."""
        if socket_path := environ.get("YDOTOOL_SOCKET"):
            return socket_path
        if runtime_dir := environ.get("XDG_RUNTIME_DIR"):
            return str(Path(runtime_dir) / ".ydotool_socket")
        return str(Path(gettempdir()) / ".ydotool_socket")

    @classmethod
    def _pack_event(cls, event_type: int, code: int, value: int) -> bytes:
        """Pack a Linux input_event with an empty timestamp."""
        return cls._EVENT.pack(0, 0, event_type, code, value)

    def _send(self, payload: bytes) -> None:
        """Send a packed input_event to ydotoold's datagram socket."""
        if self._sender is not None:
            self._sender(payload)
            return
        try:
            with socket(AF_UNIX, SOCK_DGRAM) as sock:
                sock.connect(self._socket_path)
                sock.sendall(payload)
        except OSError as exc:
            raise KeyEmitterError(
                "PTT mode requires a reachable ydotoold socket for Utter-compatible "
                "F19 emission. Start ydotoold or set ptt.emitter_backend = 'evdev'."
            ) from exc

    def write(self, key_code: KeyCode, value: int) -> None:
        """Write key state where value 1=down and 0=up."""
        if key_code != KeyCode.F19:
            raise ValueError(f"Unsupported key code: {key_code}")
        if value not in {0, 1}:
            raise ValueError(f"Unsupported key value: {value}")
        self._send(self._pack_event(self._EV_KEY, int(key_code), value))

    def syn(self) -> None:
        """Synchronize the emitted input event."""
        self._send(self._pack_event(self._EV_SYN, self._SYN_REPORT, 0))

    def close(self) -> None:
        """No persistent resources are owned by this device."""


class F19KeyEmitter:
    """Idempotent synthetic F19 key-down/key-up emitter."""

    def __init__(
        self,
        device_factory: Callable[[], KeyDevice] | None = None,
        backend: str = "ydotool",
    ) -> None:
        """Initialize the emitter with an optional backend/device factory for tests."""
        self._device_factory = device_factory or self._device_factory_for_backend(backend)
        self._device: KeyDevice | None = None
        self._is_pressed = False

    @staticmethod
    def _device_factory_for_backend(backend: str) -> Callable[[], KeyDevice]:
        """Return the key device factory for the configured backend."""
        normalized = backend.lower()
        if normalized == "ydotool":
            return YdotoolKeyDevice
        if normalized == "evdev":
            return EvdevKeyDevice
        raise KeyEmitterError(f"Unsupported PTT emitter backend: {backend}")

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
