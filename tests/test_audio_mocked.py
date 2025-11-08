"""Mocked audio backend tests for CI and testing environments."""

import pytest
from unittest.mock import Mock
from typing import Dict, List, Any
import copy

from muteme_btn.config import AudioConfig


class MockedPulseAudioBackend:
    """Mock implementation of PulseAudio backend for testing."""
    
    def __init__(self, config: AudioConfig):
        """Initialize mocked backend."""
        self.config = config
        self._mock_sinks = [
            {
                "name": "alsa_output.pci-0000_00_1b.0.analog-stereo",
                "description": "Built-in Audio Analog Stereo",
                "muted": False,
                "index": 0,
            },
            {
                "name": "bluez_sink.00_11_22_33_44_55.a2dp_sink",
                "description": "Bluetooth Headphones",
                "muted": True,
                "index": 1,
            }
        ]
        self._default_sink_index = 0
        self._mute_state = False
        self._connected = True

    def get_default_sink(self) -> Dict[str, Any]:
        """Get mocked default sink."""
        if not self._connected:
            raise Exception("Not connected to PulseAudio")
        return self._mock_sinks[self._default_sink_index]

    def set_mute_state(self, sink_name: str, muted: bool) -> None:
        """Set mocked mute state."""
        if not self._connected:
            raise Exception("Not connected to PulseAudio")
        
        if sink_name is None:
            sink_name = self.get_default_sink()["name"]
        
        for sink in self._mock_sinks:
            if sink["name"] == sink_name:
                sink["muted"] = muted
                if sink["index"] == self._default_sink_index:
                    self._mute_state = muted
                return
        
        raise Exception(f"Sink '{sink_name}' not found")

    def is_muted(self, sink_name: str) -> bool:
        """Check mocked mute state."""
        if not self._connected:
            raise Exception("Not connected to PulseAudio")
        
        if sink_name is None:
            return self._mute_state
        
        for sink in self._mock_sinks:
            if sink["name"] == sink_name:
                return sink["muted"]
        
        raise Exception(f"Sink '{sink_name}' not found")

    def list_sinks(self) -> List[Dict[str, Any]]:
        """List mocked sinks."""
        if not self._connected:
            raise Exception("Not connected to PulseAudio")
        return copy.deepcopy(self._mock_sinks)

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
        return AudioConfig(sink_name=None, poll_interval=0.5)

    @pytest.fixture
    def mocked_backend(self, audio_config):
        """Create mocked audio backend."""
        return MockedPulseAudioBackend(audio_config)

    def test_mocked_backend_initialization(self, mocked_backend, audio_config):
        """Test mocked backend initialization."""
        assert mocked_backend.config == audio_config
        assert mocked_backend._connected is True
        assert len(mocked_backend._mock_sinks) == 2

    def test_mocked_get_default_sink(self, mocked_backend):
        """Test getting default sink from mocked backend."""
        sink = mocked_backend.get_default_sink()
        
        assert sink["name"] == "alsa_output.pci-0000_00_1b.0.analog-stereo"
        assert sink["description"] == "Built-in Audio Analog Stereo"
        assert sink["muted"] is False
        assert sink["index"] == 0

    def test_mocked_set_mute_state_default_sink(self, mocked_backend):
        """Test setting mute state on default sink."""
        mocked_backend.set_mute_state(None, True)
        
        assert mocked_backend.is_muted(None) is True
        assert mocked_backend._mock_sinks[0]["muted"] is True

    def test_mocked_set_mute_state_specific_sink(self, mocked_backend):
        """Test setting mute state on specific sink."""
        mocked_backend.set_mute_state("bluez_sink.00_11_22_33_44_55.a2dp_sink", False)
        
        assert mocked_backend.is_muted("bluez_sink.00_11_22_33_44_55.a2dp_sink") is False
        assert mocked_backend._mock_sinks[1]["muted"] is False

    def test_mocked_set_mute_state_invalid_sink(self, mocked_backend):
        """Test setting mute state on invalid sink raises exception."""
        with pytest.raises(Exception, match="Sink 'invalid_sink' not found"):
            mocked_backend.set_mute_state("invalid_sink", True)

    def test_mocked_is_muted_default_sink(self, mocked_backend):
        """Test checking mute state of default sink."""
        assert mocked_backend.is_muted(None) is False
        
        mocked_backend.set_mute_state(None, True)
        assert mocked_backend.is_muted(None) is True

    def test_mocked_is_muted_specific_sink(self, mocked_backend):
        """Test checking mute state of specific sink."""
        assert mocked_backend.is_muted("bluez_sink.00_11_22_33_44_55.a2dp_sink") is True

    def test_mocked_is_muted_invalid_sink(self, mocked_backend):
        """Test checking mute state of invalid sink raises exception."""
        with pytest.raises(Exception, match="Sink 'invalid_sink' not found"):
            mocked_backend.is_muted("invalid_sink")

    def test_mocked_list_sinks(self, mocked_backend):
        """Test listing all sinks."""
        sinks = mocked_backend.list_sinks()
        
        assert len(sinks) == 2
        assert sinks[0]["name"] == "alsa_output.pci-0000_00_1b.0.analog-stereo"
        assert sinks[1]["name"] == "bluez_sink.00_11_22_33_44_55.a2dp_sink"

    def test_mocked_close_connection(self, mocked_backend):
        """Test closing mocked connection."""
        mocked_backend.close()
        
        assert mocked_backend._connected is False
        
        # Operations should fail after closing
        with pytest.raises(Exception, match="Not connected to PulseAudio"):
            mocked_backend.get_default_sink()

    def test_mocked_context_manager(self, audio_config):
        """Test mocked backend as context manager."""
        with MockedPulseAudioBackend(audio_config) as backend:
            assert backend._connected is True
            sink = backend.get_default_sink()
            assert sink["name"] is not None
        
        # Should be closed after context
        assert backend._connected is False

    def test_mocked_disconnected_operations(self, mocked_backend):
        """Test operations fail when disconnected."""
        mocked_backend.close()
        
        with pytest.raises(Exception, match="Not connected to PulseAudio"):
            mocked_backend.get_default_sink()
        
        with pytest.raises(Exception, match="Not connected to PulseAudio"):
            mocked_backend.set_mute_state(None, True)
        
        with pytest.raises(Exception, match="Not connected to PulseAudio"):
            mocked_backend.is_muted(None)
        
        with pytest.raises(Exception, match="Not connected to PulseAudio"):
            mocked_backend.list_sinks()

    def test_mocked_multiple_mute_operations(self, mocked_backend):
        """Test multiple mute operations work correctly."""
        # Initial state
        assert mocked_backend.is_muted(None) is False
        
        # Mute default sink
        mocked_backend.set_mute_state(None, True)
        assert mocked_backend.is_muted(None) is True
        
        # Mute different sink
        mocked_backend.set_mute_state("bluez_sink.00_11_22_33_44_55.a2dp_sink", False)
        assert mocked_backend.is_muted("bluez_sink.00_11_22_33_44_55.a2dp_sink") is False
        assert mocked_backend.is_muted(None) is True  # Default sink still muted
        
        # Unmute default sink
        mocked_backend.set_mute_state(None, False)
        assert mocked_backend.is_muted(None) is False

    def test_mocked_sink_state_isolation(self, mocked_backend):
        """Test that sink states are properly isolated."""
        # Set different mute states for different sinks
        mocked_backend.set_mute_state("alsa_output.pci-0000_00_1b.0.analog-stereo", True)
        mocked_backend.set_mute_state("bluez_sink.00_11_22_33_44_55.a2dp_sink", False)
        
        # Check states are independent
        assert mocked_backend.is_muted("alsa_output.pci-0000_00_1b.0.analog-stereo") is True
        assert mocked_backend.is_muted("bluez_sink.00_11_22_33_44_55.a2dp_sink") is False

    def test_mocked_list_sinks_returns_copy(self, mocked_backend):
        """Test that list_sinks returns a copy, not reference."""
        sinks1 = mocked_backend.list_sinks()
        sinks2 = mocked_backend.list_sinks()
        
        # Modify one list
        sinks1[0]["muted"] = True
        
        # Other list should be unchanged
        assert sinks2[0]["muted"] is False
        
        # Backend state should be unchanged
        assert mocked_backend._mock_sinks[0]["muted"] is False

    def test_mocked_backend_with_custom_config(self):
        """Test mocked backend with custom configuration."""
        config = AudioConfig(sink_name="custom_sink", poll_interval=0.8)
        backend = MockedPulseAudioBackend(config)
        
        assert backend.config.sink_name == "custom_sink"
        assert backend.config.poll_interval == 0.8
