"""Mocked audio backend tests for CI and testing environments."""

import copy
from typing import Any

import pytest

from muteme_btn.config import AudioConfig


class MockedPulseAudioBackend:
    """Mock implementation of PulseAudio backend for testing."""

    def __init__(self, config: AudioConfig):
        """Initialize mocked backend."""
        self.config = config
        self._mock_sources = [
            {
                "name": "alsa_input.pci-0000_00_1b.0.analog-stereo",
                "description": "Built-in Audio Analog Stereo",
                "muted": False,
                "index": 0,
            },
            {
                "name": "bluez_source.00_11_22_33_44_55.a2dp_source",
                "description": "Bluetooth Microphone",
                "muted": True,
                "index": 1,
            },
        ]
        self._default_source_index = 0
        self._mute_state = False
        self._connected = True

    def get_default_source(self) -> dict[str, Any]:
        """Get mocked default source."""
        if not self._connected:
            raise Exception("Not connected to PulseAudio")
        return self._mock_sources[self._default_source_index]

    def set_mute_state(self, source_name: str, muted: bool) -> None:
        """Set mocked mute state."""
        if not self._connected:
            raise Exception("Not connected to PulseAudio")

        if source_name is None:
            source_name = self.get_default_source()["name"]

        for source in self._mock_sources:
            if source["name"] == source_name:
                source["muted"] = muted
                if source["index"] == self._default_source_index:
                    self._mute_state = muted
                return

        raise Exception(f"Source '{source_name}' not found")

    def is_muted(self, source_name: str) -> bool:
        """Check mocked mute state."""
        if not self._connected:
            raise Exception("Not connected to PulseAudio")

        if source_name is None:
            return self._mute_state

        for source in self._mock_sources:
            if source["name"] == source_name:
                return bool(source["muted"])

        raise Exception(f"Source '{source_name}' not found")

    def list_sources(self) -> list[dict[str, Any]]:
        """List mocked sources."""
        if not self._connected:
            raise Exception("Not connected to PulseAudio")
        return copy.deepcopy(self._mock_sources)

    def close(self) -> None:
        """Mock close connection."""
        self._connected = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class TestMockedAudioBackend:
    """Test suite for mocked audio backend functionality."""

    @pytest.fixture
    def audio_config(self):
        """Create test audio configuration."""
        return AudioConfig(source_name=None, poll_interval=0.5)

    @pytest.fixture
    def mocked_backend(self, audio_config):
        """Create mocked audio backend."""
        return MockedPulseAudioBackend(audio_config)

    def test_mocked_backend_initialization(self, mocked_backend, audio_config):
        """Test mocked backend initialization."""
        assert mocked_backend.config == audio_config
        assert mocked_backend._connected is True
        assert len(mocked_backend._mock_sources) == 2

    def test_mocked_get_default_source(self, mocked_backend):
        """Test getting default source from mocked backend."""
        source = mocked_backend.get_default_source()

        assert source["name"] == "alsa_input.pci-0000_00_1b.0.analog-stereo"
        assert source["description"] == "Built-in Audio Analog Stereo"
        assert source["muted"] is False
        assert source["index"] == 0

    def test_mocked_set_mute_state_default_source(self, mocked_backend):
        """Test setting mute state on default source."""
        mocked_backend.set_mute_state(None, True)

        assert mocked_backend.is_muted(None) is True
        assert mocked_backend._mock_sources[0]["muted"] is True

    def test_mocked_set_mute_state_specific_source(self, mocked_backend):
        """Test setting mute state on specific source."""
        mocked_backend.set_mute_state("bluez_source.00_11_22_33_44_55.a2dp_source", False)

        assert mocked_backend.is_muted("bluez_source.00_11_22_33_44_55.a2dp_source") is False
        assert mocked_backend._mock_sources[1]["muted"] is False

    def test_mocked_set_mute_state_invalid_source(self, mocked_backend):
        """Test setting mute state on invalid source raises exception."""
        with pytest.raises(Exception, match="Source 'invalid_source' not found"):
            mocked_backend.set_mute_state("invalid_source", True)

    def test_mocked_is_muted_default_source(self, mocked_backend):
        """Test checking mute state of default source."""
        assert mocked_backend.is_muted(None) is False

        mocked_backend.set_mute_state(None, True)
        assert mocked_backend.is_muted(None) is True

    def test_mocked_is_muted_specific_source(self, mocked_backend):
        """Test checking mute state of specific source."""
        assert mocked_backend.is_muted("bluez_source.00_11_22_33_44_55.a2dp_source") is True

    def test_mocked_is_muted_invalid_source(self, mocked_backend):
        """Test checking mute state of invalid source raises exception."""
        with pytest.raises(Exception, match="Source 'invalid_source' not found"):
            mocked_backend.is_muted("invalid_source")

    def test_mocked_list_sources(self, mocked_backend):
        """Test listing all sources."""
        sources = mocked_backend.list_sources()

        assert len(sources) == 2
        assert sources[0]["name"] == "alsa_input.pci-0000_00_1b.0.analog-stereo"
        assert sources[1]["name"] == "bluez_source.00_11_22_33_44_55.a2dp_source"

    def test_mocked_close_connection(self, mocked_backend):
        """Test closing mocked connection."""
        mocked_backend.close()

        assert mocked_backend._connected is False

        # Operations should fail after closing
        with pytest.raises(Exception, match="Not connected to PulseAudio"):
            mocked_backend.get_default_source()

    def test_mocked_context_manager(self, audio_config):
        """Test mocked backend as context manager."""
        with MockedPulseAudioBackend(audio_config) as backend:
            assert backend._connected is True
            source = backend.get_default_source()
            assert source["name"] is not None

        # Should be closed after context
        assert backend._connected is False

    def test_mocked_disconnected_operations(self, mocked_backend):
        """Test operations fail when disconnected."""
        mocked_backend.close()

        with pytest.raises(Exception, match="Not connected to PulseAudio"):
            mocked_backend.get_default_source()

        with pytest.raises(Exception, match="Not connected to PulseAudio"):
            mocked_backend.set_mute_state(None, True)

        with pytest.raises(Exception, match="Not connected to PulseAudio"):
            mocked_backend.is_muted(None)

        with pytest.raises(Exception, match="Not connected to PulseAudio"):
            mocked_backend.list_sources()

    def test_mocked_multiple_mute_operations(self, mocked_backend):
        """Test multiple mute operations work correctly."""
        # Initial state
        assert mocked_backend.is_muted(None) is False

        # Mute default source
        mocked_backend.set_mute_state(None, True)
        assert mocked_backend.is_muted(None) is True

        # Mute different source
        mocked_backend.set_mute_state("bluez_source.00_11_22_33_44_55.a2dp_source", False)
        assert mocked_backend.is_muted("bluez_source.00_11_22_33_44_55.a2dp_source") is False
        assert mocked_backend.is_muted(None) is True  # Default source still muted

        # Unmute default source
        mocked_backend.set_mute_state(None, False)
        assert mocked_backend.is_muted(None) is False

    def test_mocked_source_state_isolation(self, mocked_backend):
        """Test that source states are properly isolated."""
        # Set different mute states for different sources
        mocked_backend.set_mute_state("alsa_input.pci-0000_00_1b.0.analog-stereo", True)
        mocked_backend.set_mute_state("bluez_source.00_11_22_33_44_55.a2dp_source", False)

        # Check states are independent
        assert mocked_backend.is_muted("alsa_input.pci-0000_00_1b.0.analog-stereo") is True
        assert mocked_backend.is_muted("bluez_source.00_11_22_33_44_55.a2dp_source") is False

    def test_mocked_list_sources_returns_copy(self, mocked_backend):
        """Test that list_sources returns a copy, not reference."""
        sources1 = mocked_backend.list_sources()
        sources2 = mocked_backend.list_sources()

        # Modify one list
        sources1[0]["muted"] = True

        # Other list should be unchanged
        assert sources2[0]["muted"] is False

        # Backend state should be unchanged
        assert mocked_backend._mock_sources[0]["muted"] is False

    def test_mocked_backend_with_custom_config(self):
        """Test mocked backend with custom configuration."""
        config = AudioConfig(source_name="custom_source", poll_interval=0.8)
        backend = MockedPulseAudioBackend(config)

        assert backend.config.source_name == "custom_source"
        assert backend.config.poll_interval == 0.8
