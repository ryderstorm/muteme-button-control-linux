"""HID communication layer for MuteMe button control."""

from .device import DeviceError, DeviceInfo, LEDColor, MuteMeDevice
from .events import ButtonEvent, EventHandler

__all__ = [
    "MuteMeDevice",
    "DeviceInfo",
    "DeviceError",
    "LEDColor",
    "ButtonEvent",
    "EventHandler",
]
