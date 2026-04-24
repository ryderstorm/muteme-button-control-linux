"""Tests for synthetic key emission abstraction."""

from unittest.mock import Mock

from muteme_btn.input.key_emitter import F19KeyEmitter, KeyCode


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
