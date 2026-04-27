"""Tests for Windows support scaffolding that can be validated on Linux."""

import sys
from typing import cast
from unittest.mock import Mock

import pytest

from muteme_btn.config import AudioConfig, PTTConfig
from muteme_btn.input.key_emitter import (
    F19KeyEmitter,
    KeyCode,
    WindowsSendInputKeyDevice,
)


def test_ptt_config_accepts_auto_and_sendinput_backends() -> None:
    """PTT config should allow platform auto-selection and Windows SendInput."""
    assert PTTConfig(emitter_backend="AUTO").emitter_backend == "auto"
    assert PTTConfig(emitter_backend="SendInput").emitter_backend == "sendinput"


def test_audio_config_accepts_auto_and_coreaudio_backends() -> None:
    """Audio config should allow platform auto-selection and Windows Core Audio."""
    assert AudioConfig(backend="AUTO").backend == "auto"
    assert AudioConfig(backend="CoreAudio").backend == "coreaudio"


def test_windows_sendinput_device_emits_f19_down_and_up() -> None:
    """Windows SendInput backend should translate F19 hold events to VK_F19 down/up."""
    sent: list[tuple[int, int]] = []
    device = WindowsSendInputKeyDevice(sender=lambda vk, flags: sent.append((vk, flags)))

    device.write(KeyCode.F19, 1)
    device.syn()
    device.write(KeyCode.F19, 0)
    device.syn()

    assert sent == [(0x82, 0), (0x82, WindowsSendInputKeyDevice.KEYEVENTF_KEYUP)]


def test_windows_sendinput_device_rejects_non_f19_codes() -> None:
    """Windows SendInput backend should preserve the initial F19-only contract."""
    device = WindowsSendInputKeyDevice(sender=Mock())

    with pytest.raises(ValueError, match="Unsupported key code"):
        device.write(cast(KeyCode, 190), 1)


def test_windows_sendinput_device_rejects_unknown_key_values() -> None:
    """Windows SendInput backend should only emit key-down and key-up values."""
    device = WindowsSendInputKeyDevice(sender=Mock())

    with pytest.raises(ValueError, match="Unsupported key value"):
        device.write(KeyCode.F19, 2)


def test_f19_emitter_sendinput_backend_uses_windows_device() -> None:
    """The explicit sendinput backend should use the Windows SendInput device."""
    factory = F19KeyEmitter._device_factory_for_backend("sendinput")

    assert factory is WindowsSendInputKeyDevice


def test_auto_backend_uses_sendinput_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """The auto backend should map to SendInput on win32."""
    monkeypatch.setattr(sys, "platform", "win32")

    factory = F19KeyEmitter._device_factory_for_backend("auto")

    assert factory is WindowsSendInputKeyDevice


def test_f19_emitter_auto_backend_preserves_ydotool_default_on_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The auto backend should preserve the existing ydotool default on Linux."""
    from muteme_btn.input.key_emitter import YdotoolKeyDevice

    monkeypatch.setattr(sys, "platform", "linux")

    factory = F19KeyEmitter._device_factory_for_backend("auto")

    assert factory is YdotoolKeyDevice
