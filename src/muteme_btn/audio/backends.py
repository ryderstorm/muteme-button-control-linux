"""Platform-aware audio backend selection."""

import sys
from typing import Any, Protocol

from muteme_btn.config import AudioConfig


class AudioBackend(Protocol):
    """Minimal audio backend protocol consumed by the daemon and LED controller."""

    def get_default_source(self) -> dict[str, Any]:
        """Get information about the default microphone input."""

    def set_mute_state(self, source_name: str | None, muted: bool) -> None:
        """Set mute state for a source or the default microphone input."""

    def is_muted(self, source_name: str | None) -> bool:
        """Return whether a source or the default microphone input is muted."""

    def list_sources(self) -> list[dict[str, Any]]:
        """List available microphone inputs."""

    def close(self) -> None:
        """Release backend resources."""


class UnsupportedAudioBackendError(RuntimeError):
    """Raised when a configured audio backend cannot be selected."""


def PulseAudioBackend(config: AudioConfig) -> AudioBackend:
    """Create the Linux PulseAudio backend without importing pulsectl on module import."""
    from muteme_btn.audio.pulse import PulseAudioBackend as _PulseAudioBackend

    return _PulseAudioBackend(config)


def WindowsCoreAudioBackend(config: AudioConfig) -> AudioBackend:
    """Create the Windows Core Audio backend without importing Windows-only packages early."""
    from muteme_btn.audio.coreaudio import WindowsCoreAudioBackend as _WindowsCoreAudioBackend

    return _WindowsCoreAudioBackend(config)


def create_audio_backend(config: AudioConfig) -> AudioBackend:
    """Create the configured platform-specific audio backend."""
    backend = config.backend.lower()
    if backend == "auto":
        backend = "coreaudio" if sys.platform == "win32" else "pulseaudio"

    if backend in {"pulseaudio", "pipewire"}:
        return PulseAudioBackend(config)
    if backend == "coreaudio":
        return WindowsCoreAudioBackend(config)

    raise UnsupportedAudioBackendError(f"Unsupported audio backend: {config.backend}")
