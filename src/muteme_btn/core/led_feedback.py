"""LED feedback synchronization with mute status."""

import logging
from typing import Optional

from muteme_btn.hid.device import MuteMeDevice, LEDColor
from muteme_btn.audio.pulse import PulseAudioBackend


logger = logging.getLogger(__name__)


class LEDFeedbackController:
    """Controls LED feedback based on audio mute status."""
    
    def __init__(
        self,
        device: MuteMeDevice,
        audio_backend: PulseAudioBackend,
        muted_color: LEDColor = LEDColor.RED,
        unmuted_color: LEDColor = LEDColor.GREEN
    ):
        """Initialize LED feedback controller.
        
        Args:
            device: MuteMe HID device instance
            audio_backend: Audio backend for checking mute status
            muted_color: LED color to show when muted
            unmuted_color: LED color to show when unmuted
        """
        self.device = device
        self.audio_backend = audio_backend
        self.muted_color = muted_color
        self.unmuted_color = unmuted_color
        
        logger.info(
            "Initialized LED feedback controller",
            muted_color=muted_color.name,
            unmuted_color=unmuted_color.name
        )

    def update_led_to_mute_status(self) -> None:
        """Update LED color based on current audio mute status."""
        try:
            # Check if device is connected
            if not self.device.is_connected():
                logger.debug("Device not connected, skipping LED update")
                return
            
            # Get current mute status
            is_muted = self.audio_backend.is_muted()
            
            # Set appropriate LED color
            target_color = self.muted_color if is_muted else self.unmuted_color
            
            try:
                self.device.set_led_color(target_color)
                logger.debug(
                    "Updated LED color",
                    muted=is_muted,
                    color=target_color.name
                )
            except Exception as e:
                logger.error(f"Failed to set LED color: {e}")
                
        except Exception as e:
            logger.error(f"Failed to update LED based on mute status: {e}")

    def set_muted_color(self, color: LEDColor) -> None:
        """Set the LED color for muted state.
        
        Args:
            color: LED color to use when muted
        """
        self.muted_color = color
        logger.debug(f"Set muted color to {color.name}")

    def set_unmuted_color(self, color: LEDColor) -> None:
        """Set the LED color for unmuted state.
        
        Args:
            color: LED color to use when unmuted
        """
        self.unmuted_color = color
        logger.debug(f"Set unmuted color to {color.name}")

    def set_colors_by_name(self, muted_color_name: str, unmuted_color_name: str) -> None:
        """Set LED colors by name.
        
        Args:
            muted_color_name: Name of color for muted state
            unmuted_color_name: Name of color for unmuted state
            
        Raises:
            ValueError: If color names are invalid
        """
        self.muted_color = LEDColor.from_name(muted_color_name)
        self.unmuted_color = LEDColor.from_name(unmuted_color_name)
        logger.debug(
            f"Set colors by name: muted={muted_color_name}, unmuted={unmuted_color_name}"
        )

    def get_current_status(self) -> dict:
        """Get current LED and mute status.
        
        Returns:
            Dictionary containing current status information
        """
        try:
            is_muted = self.audio_backend.is_muted()
            current_led_color = self.muted_color if is_muted else self.unmuted_color
            device_connected = self.device.is_connected()
            
            return {
                "muted": is_muted,
                "led_color": current_led_color,
                "device_connected": device_connected,
                "muted_color": self.muted_color,
                "unmuted_color": self.unmuted_color,
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
        """Force LED to specific color, ignoring mute status.
        
        Args:
            color: LED color to set
        """
        try:
            if not self.device.is_connected():
                logger.debug("Device not connected, cannot force LED color")
                return
                
            self.device.set_led_color(color)
            logger.debug(f"Forced LED color to {color.name}")
        except Exception as e:
            logger.error(f"Failed to force LED color: {e}")

    def force_led_color_by_name(self, color_name: str) -> None:
        """Force LED to specific color by name, ignoring mute status.
        
        Args:
            color_name: Name of LED color to set
            
        Raises:
            ValueError: If color name is invalid
        """
        color = LEDColor.from_name(color_name)
        self.force_led_color(color)
