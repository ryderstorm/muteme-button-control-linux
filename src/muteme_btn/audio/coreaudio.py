"""Windows Core Audio backend implementation using PyCAW when available."""

import logging
import sys
from typing import Any

from muteme_btn.config import AudioConfig

logger = logging.getLogger(__name__)


class WindowsCoreAudioBackend:
    """Windows Core Audio backend for microphone mute control."""

    def __init__(self, config: AudioConfig):
        """Initialize a Core Audio endpoint-volume controller for the default microphone."""
        self.config = config
        self._endpoint_volume: Any = self._create_endpoint_volume()
        logger.info("Initialized Windows Core Audio backend for default capture endpoint")

    @staticmethod
    def _create_endpoint_volume() -> Any:
        """Create a PyCAW IAudioEndpointVolume interface for the default microphone."""
        if sys.platform != "win32":  # pragma: no cover - production guard
            raise RuntimeError("The coreaudio backend requires Windows.")

        try:  # pragma: no cover - exercised on Windows hosts
            from ctypes import POINTER, cast

            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        except ImportError as exc:  # pragma: no cover - depends on optional Windows deps
            raise RuntimeError(
                "The coreaudio backend requires the Windows-only 'pycaw' and 'comtypes' packages."
            ) from exc

        device = AudioUtilities.GetMicrophone()
        if device is None:
            raise RuntimeError("No default Windows microphone capture endpoint was found.")
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))

    def get_default_source(self) -> dict[str, Any]:
        """Get information about the default capture endpoint."""
        return {
            "name": "default",
            "description": "Windows default microphone",
            "muted": self.is_muted(None),
            "index": 0,
        }

    def set_mute_state(self, source_name: str | None, muted: bool) -> None:
        """Set mute state for the default capture endpoint."""
        if source_name not in {None, "default"}:
            raise RuntimeError(
                "The initial Windows backend only supports the default microphone endpoint."
            )
        self._endpoint_volume.SetMute(int(muted), None)
        logger.debug("Set Windows default microphone mute state: %s", muted)

    def is_muted(self, source_name: str | None) -> bool:
        """Return whether the default capture endpoint is muted."""
        if source_name not in {None, "default"}:
            raise RuntimeError(
                "The initial Windows backend only supports the default microphone endpoint."
            )
        return bool(self._endpoint_volume.GetMute())

    def list_sources(self) -> list[dict[str, Any]]:
        """List the currently supported Windows microphone source."""
        return [self.get_default_source()]

    def close(self) -> None:
        """Release references to COM-backed endpoint objects."""
        self._endpoint_volume = None
