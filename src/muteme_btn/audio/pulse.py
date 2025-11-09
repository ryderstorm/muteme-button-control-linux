"""PulseAudio backend implementation using pulsectl."""

import logging
from typing import Any

import pulsectl

from muteme_btn.config import AudioConfig

logger = logging.getLogger(__name__)


class PulseAudioBackend:
    """PulseAudio backend for audio control using pulsectl."""

    def __init__(self, config: AudioConfig):
        """Initialize PulseAudio backend.

        Args:
            config: Audio configuration containing sink settings
        """
        self.config = config
        self._pulse: pulsectl.Pulse = pulsectl.Pulse("muteme-btn-control")
        logger.info(f"Initialized PulseAudio backend with sink: {config.sink_name or 'default'}")

    def get_default_sink(self) -> dict[str, Any]:
        """Get information about the default sink.

        Returns:
            Dictionary containing sink information (name, description, muted, index)

        Raises:
            Exception: If default sink cannot be found or accessed
        """
        try:
            # Get the server info to find default sink name
            server_info = self._pulse.server_info()
            default_sink_name = server_info.default_sink_name

            # Get the sink object
            sink = self._pulse.get_sink_by_name(default_sink_name)

            return {
                "name": sink.name,
                "description": sink.description,
                "muted": bool(sink.mute),
                "index": sink.index,
            }
        except Exception as e:
            logger.error(f"Failed to get default sink: {e}")
            raise

    def set_mute_state(self, sink_name: str | None, muted: bool) -> None:
        """Set mute state for a specific sink or default sink.

        Args:
            sink_name: Name of sink to control, or None for default sink
            muted: True to mute, False to unmute
        """
        try:
            # Use specified sink, configured sink, or get default sink
            target_sink = sink_name or self.config.sink_name
            if target_sink is None:
                default_info = self.get_default_sink()
                target_sink = default_info["name"]

            # Get the sink and set mute state
            sink = self._pulse.get_sink_by_name(target_sink)
            self._pulse.sink_mute(sink.index, int(muted))

            logger.debug(f"Set mute state for sink '{target_sink}': {muted}")
        except Exception as e:
            logger.error(f"Failed to set mute state for sink '{sink_name}': {e}")
            raise

    def is_muted(self, sink_name: str | None) -> bool:
        """Check if a sink is currently muted.

        Args:
            sink_name: Name of sink to check, or None for default sink

        Returns:
            True if sink is muted, False otherwise
        """
        try:
            # Use specified sink, configured sink, or get default sink
            target_sink = sink_name or self.config.sink_name
            if target_sink is None:
                default_info = self.get_default_sink()
                target_sink = default_info["name"]

            # Get the sink and check mute state
            sink = self._pulse.get_sink_by_name(target_sink)
            return bool(sink.mute)
        except Exception as e:
            logger.error(f"Failed to get mute state for sink '{sink_name}': {e}")
            raise

    def list_sinks(self) -> list[dict[str, Any]]:
        """List all available audio sinks.

        Returns:
            List of dictionaries containing sink information
        """
        try:
            sinks = []
            for sink in self._pulse.sink_list():
                sinks.append(
                    {
                        "name": sink.name,
                        "description": sink.description,
                        "muted": bool(sink.mute),
                        "index": sink.index,
                    }
                )
            return sinks
        except Exception as e:
            logger.error(f"Failed to list sinks: {e}")
            raise

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup PulseAudio connection."""
        try:
            if hasattr(self, "_pulse") and self._pulse:
                self._pulse.close()
                logger.debug("Closed PulseAudio connection")
        except Exception as e:
            logger.warning(f"Error closing PulseAudio connection: {e}")

    def close(self) -> None:
        """Explicitly close the PulseAudio connection."""
        self.__exit__(None, None, None)
