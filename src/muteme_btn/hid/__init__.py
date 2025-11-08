"""HID communication layer for MuteMe button control."""

from .device import MuteMeDevice, DeviceInfo, DeviceError, LEDColor
from .events import ButtonEvent, EventHandler

__all__ = [
    "MuteMeDevice",
    "DeviceInfo", 
    "DeviceError",
    "LEDColor",
    "ButtonEvent",
    "EventHandler",
]
