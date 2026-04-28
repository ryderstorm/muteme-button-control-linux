"""Tests for synthetic key emission abstraction."""

import struct
from typing import cast
from unittest.mock import Mock

import pytest

from muteme_btn.input.key_emitter import F19KeyEmitter, KeyCode, YdotoolKeyDevice


def test_f19_key_emitter_sends_press_and_release_once() -> None:
    """F19 emitter should guard against duplicate key-down and key-up calls."""
    fake_device = Mock()
    emitter = F19KeyEmitter(device_factory=lambda: fake_device)

    emitter.press_f19()
    emitter.press_f19()
    emitter.release_f19()
    emitter.release_f19()

    assert fake_device.write.call_args_list == [
        ((KeyCode.F19, 1),),
        ((KeyCode.F19, 0),),
    ]
    assert fake_device.syn.call_count == 2


def test_release_all_releases_f19_when_pressed() -> None:
    """Cleanup should release F19 if it is logically held."""
    fake_device = Mock()
    emitter = F19KeyEmitter(device_factory=lambda: fake_device)

    emitter.press_f19()
    emitter.release_all()

    assert fake_device.write.call_args_list[-1] == ((KeyCode.F19, 0),)
    assert fake_device.syn.call_count == 2


def test_f19_key_code_matches_linux_input_event_code() -> None:
    """F19 should use the Linux evdev code for the synthetic shortcut."""
    assert KeyCode.F19 == 189


def test_ydotool_key_device_emits_f19_down_up_and_syn_events() -> None:
    """ydotool backend should write input_event packets to ydotoold's socket path."""
    sent: list[bytes] = []
    device = YdotoolKeyDevice(sender=sent.append)

    device.write(KeyCode.F19, 1)
    device.syn()
    device.write(KeyCode.F19, 0)
    device.syn()

    assert sent == [
        struct.pack("llHHI", 0, 0, 1, 189, 1),
        struct.pack("llHHI", 0, 0, 0, 0, 0),
        struct.pack("llHHI", 0, 0, 1, 189, 0),
        struct.pack("llHHI", 0, 0, 0, 0, 0),
    ]


def test_f19_key_emitter_close_closes_device_even_when_release_fails() -> None:
    """Emitter close should always close the backend even if key release fails."""
    fake_device = Mock()
    fake_device.write.side_effect = [None, RuntimeError("release failed")]
    emitter = F19KeyEmitter(device_factory=lambda: fake_device)

    emitter.press_f19()

    with pytest.raises(RuntimeError, match="release failed"):
        emitter.close()

    fake_device.close.assert_called_once()


def test_ydotool_key_device_rejects_non_f19_codes() -> None:
    """Only F19 is supported for the first PTT implementation."""
    device = YdotoolKeyDevice(sender=Mock())

    with pytest.raises(ValueError, match="Unsupported key code"):
        device.write(cast(KeyCode, 190), 1)


def test_ydotool_key_device_rejects_unknown_key_values() -> None:
    """ydotool backend should only emit key-down and key-up values."""
    device = YdotoolKeyDevice(sender=Mock())

    with pytest.raises(ValueError, match="Unsupported key value"):
        device.write(KeyCode.F19, 2)
