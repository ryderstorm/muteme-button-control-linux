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
            config: Audio configuration containing source settings
        """
        self.config = config
        self._pulse: pulsectl.Pulse = pulsectl.Pulse("muteme-btn-control")
        logger.info(
            f"Initialized PulseAudio backend with source: {config.source_name or 'default'}"
        )

    def get_default_source(self) -> dict[str, Any]:
        """Get information about the default source (microphone input).

        Returns:
            Dictionary containing source information (name, description, muted, index)

        Raises:
            Exception: If default source cannot be found or accessed
        """
        try:
            # Get the server info to find default source name
            server_info = self._pulse.server_info()
            default_source_name = server_info.default_source_name

            # Get the source object
            source = self._pulse.get_source_by_name(default_source_name)

            return {
                "name": source.name,
                "description": source.description,
                "muted": bool(source.mute),
                "index": source.index,
            }
        except Exception as e:
            logger.error(f"Failed to get default source: {e}")
            raise

    def set_mute_state(self, source_name: str | None, muted: bool) -> None:
        """Set mute state for a specific source or default source (microphone input).

        Args:
            source_name: Name of source to control, or None for default source
            muted: True to mute, False to unmute
        """
        try:
            # Use specified source, configured source, or get default source
            target_source = source_name or self.config.source_name
            if target_source is None:
                default_info = self.get_default_source()
                target_source = default_info["name"]

            # Get the source and set mute state
            source = self._pulse.get_source_by_name(target_source)
            self._pulse.source_mute(source.index, int(muted))

            logger.debug(f"Set mute state for source '{target_source}': {muted}")
        except Exception as e:
            logger.error(f"Failed to set mute state for source '{source_name}': {e}")
            raise

    def is_muted(self, source_name: str | None) -> bool:
        """Check if a source is currently muted.

        Args:
            source_name: Name of source to check, or None for default source

        Returns:
            True if source is muted, False otherwise
        """
        try:
            # Use specified source, configured source, or get default source
            target_source = source_name or self.config.source_name
            if target_source is None:
                default_info = self.get_default_source()
                target_source = default_info["name"]

            # Get the source and check mute state
            source = self._pulse.get_source_by_name(target_source)
            return bool(source.mute)
        except Exception as e:
            logger.error(f"Failed to get mute state for source '{source_name}': {e}")
            raise

    def list_sources(self) -> list[dict[str, Any]]:
        """List all available audio sources (microphone inputs).

        Returns:
            List of dictionaries containing source information
        """
        try:
            sources = []
            for source in self._pulse.source_list():
                sources.append(
                    {
                        "name": source.name,
                        "description": source.description,
                        "muted": bool(source.mute),
                        "index": source.index,
                    }
                )
            return sources
        except Exception as e:
            logger.error(f"Failed to list sources: {e}")
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
