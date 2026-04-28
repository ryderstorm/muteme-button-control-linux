"""LED feedback synchronization with mute and operating-mode status."""

import asyncio
import logging
from typing import Literal

from muteme_btn.audio.pulse import PulseAudioBackend
from muteme_btn.hid.device import LEDColor, MuteMeDevice

logger = logging.getLogger(__name__)

OperatingMode = Literal["normal", "ptt"]


class LEDFeedbackController:
    """Controls LED feedback based on audio mute status and operating mode."""

    def __init__(
        self,
        device: MuteMeDevice,
        audio_backend: PulseAudioBackend,
        muted_color: LEDColor = LEDColor.RED,
        unmuted_color: LEDColor = LEDColor.GREEN,
        ptt_idle_color: LEDColor = LEDColor.BLUE,
        ptt_active_color: LEDColor = LEDColor.YELLOW,
    ):
        """Initialize LED feedback controller."""
        self.device = device
        self.audio_backend = audio_backend
        self.muted_color = muted_color
        self.unmuted_color = unmuted_color
        self.ptt_idle_color = ptt_idle_color
        self.ptt_active_color = ptt_active_color
        self._last_applied_color: LEDColor | None = None

        logger.info(
            f"Initialized LED feedback controller: "
            f"muted_color={muted_color.name}, unmuted_color={unmuted_color.name}, "
            f"ptt_idle_color={ptt_idle_color.name}, ptt_active_color={ptt_active_color.name}"
        )

    def set_device(self, device: MuteMeDevice) -> None:
        """Swap to a new HID device and force next LED update to re-apply state."""
        self.device = device
        self._last_applied_color = None

    def update_led_to_mute_status(self) -> None:
        """Update LED color based on current audio mute status."""
        try:
            if not self.device.is_connected():
                self._last_applied_color = None
                logger.debug("Device not connected, skipping LED update")
                return

            is_muted = self.audio_backend.is_muted(None)
            target_color = self.muted_color if is_muted else self.unmuted_color
            self._apply_color_if_needed(target_color, check_connected=False)
            logger.debug(f"Updated LED color: muted={is_muted}, color={target_color.name}")
        except Exception as e:
            logger.error(f"Failed to update LED based on mute status: {e}")

    def update_led_for_mode(self, mode: OperatingMode, active: bool = False) -> None:
        """Update LED for a mode-specific presentation.

        Args:
            mode: Current operating mode ("normal" or "ptt")
            active: Whether the PTT hold is active
        """
        if mode == "ptt":
            target_color = self.ptt_active_color if active else self.ptt_idle_color
            try:
                self._apply_color_if_needed(target_color)
                logger.debug(f"Updated PTT LED: active={active}, color={target_color.name}")
            except Exception:
                logger.exception(
                    "Failed to update PTT LED: "
                    f"active={active}, attempted_color={target_color.name}"
                )
            return

        self.update_led_to_mute_status()

    async def show_mode_switch_confirmation(self) -> None:
        """Show a short visible confirmation that the operating mode changed."""
        try:
            if not self.device.is_connected():
                return
            for color in (LEDColor.WHITE, LEDColor.NOCOLOR, LEDColor.WHITE):
                self.device.set_led_color(color)
                await asyncio.sleep(0.08)
            self._last_applied_color = None
        except Exception as e:
            logger.error(f"Failed to show mode switch confirmation: {e}")

    def _apply_color_if_needed(self, target_color: LEDColor, check_connected: bool = True) -> None:
        """Apply color while avoiding duplicate LED writes."""
        if check_connected and not self.device.is_connected():
            self._last_applied_color = None
            logger.debug("Device not connected, skipping LED update")
            return
        if self._last_applied_color == target_color:
            return
        self.device.set_led_color(target_color)
        self._last_applied_color = target_color

    def set_muted_color(self, color: LEDColor) -> None:
        """Set the LED color for muted state."""
        self.muted_color = color
        logger.debug(f"Set muted color to {color.name}")

    def set_unmuted_color(self, color: LEDColor) -> None:
        """Set the LED color for unmuted state."""
        self.unmuted_color = color
        logger.debug(f"Set unmuted color to {color.name}")

    def set_colors_by_name(self, muted_color_name: str, unmuted_color_name: str) -> None:
        """Set LED colors by name."""
        self.muted_color = LEDColor.from_name(muted_color_name)
        self.unmuted_color = LEDColor.from_name(unmuted_color_name)
        logger.debug(f"Set colors by name: muted={muted_color_name}, unmuted={unmuted_color_name}")

    def get_current_status(self) -> dict:
        """Get current LED and mute status."""
        try:
            is_muted = self.audio_backend.is_muted(None)
            current_led_color = self._last_applied_color
            if current_led_color is None:
                current_led_color = self.muted_color if is_muted else self.unmuted_color
            device_connected = self.device.is_connected()

            return {
                "muted": is_muted,
                "led_color": current_led_color,
                "device_connected": device_connected,
                "muted_color": self.muted_color,
                "unmuted_color": self.unmuted_color,
                "ptt_idle_color": self.ptt_idle_color,
                "ptt_active_color": self.ptt_active_color,
            }
        except Exception as e:
            logger.error(f"Failed to get current status: {e}")
            return {
                "muted": None,
                "led_color": None,
                "device_connected": False,
                "error": str(e),
            }

    def force_led_color(self, color: LEDColor) -> None:
        """Force LED to specific color, ignoring mute status."""
        try:
            if not self.device.is_connected():
                logger.debug("Device not connected, cannot force LED color")
                return

            self.device.set_led_color(color)
            self._last_applied_color = color
            logger.debug(f"Forced LED color to {color.name}")
        except Exception as e:
            logger.error(f"Failed to force LED color: {e}")

    def force_led_color_by_name(self, color_name: str) -> None:
        """Force LED to specific color by name, ignoring mute status."""
        color = LEDColor.from_name(color_name)
        self.force_led_color(color)
