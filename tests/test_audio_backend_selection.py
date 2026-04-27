"""Tests for platform-specific audio backend selection."""

import sys
from unittest.mock import Mock, patch

import pytest

from muteme_btn.audio.backends import UnsupportedAudioBackendError, create_audio_backend
from muteme_btn.config import AudioConfig


def test_audio_backend_auto_uses_coreaudio_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto audio backend should map to Windows Core Audio on win32."""
    monkeypatch.setattr(sys, "platform", "win32")

    with patch("muteme_btn.audio.backends.WindowsCoreAudioBackend") as backend_class:
        config = AudioConfig(backend="auto")
        backend = create_audio_backend(config)

    backend_class.assert_called_once_with(config)
    assert backend == backend_class.return_value


def test_audio_backend_auto_preserves_pulseaudio_on_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto audio backend should preserve existing PulseAudio behavior on Linux."""
    monkeypatch.setattr(sys, "platform", "linux")

    with patch("muteme_btn.audio.backends.PulseAudioBackend") as backend_class:
        config = AudioConfig(backend="auto")
        backend = create_audio_backend(config)

    backend_class.assert_called_once_with(config)
    assert backend == backend_class.return_value


def test_audio_backend_coreaudio_uses_windows_backend() -> None:
    """Explicit coreaudio backend should use the Windows backend factory path."""
    with patch("muteme_btn.audio.backends.WindowsCoreAudioBackend") as backend_class:
        config = AudioConfig(backend="coreaudio")
        backend = create_audio_backend(config)

    backend_class.assert_called_once_with(config)
    assert backend == backend_class.return_value


def test_audio_backend_rejects_unreachable_backend_even_if_config_is_bypassed() -> None:
    """Backend factory should fail clearly if called with an unsupported backend name."""
    config = Mock(spec=AudioConfig)
    config.backend = "alsa"

    with pytest.raises(UnsupportedAudioBackendError, match="Unsupported audio backend"):
        create_audio_backend(config)
