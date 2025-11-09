"""Tests for PulseAudio backend implementation."""

from unittest.mock import Mock, patch

import pytest

from muteme_btn.audio.pulse import PulseAudioBackend
from muteme_btn.config import AudioConfig


class TestPulseAudioBackend:
    """Test suite for PulseAudio backend."""

    @pytest.fixture
    def audio_config(self):
        """Create a test audio configuration."""
        return AudioConfig()

    @pytest.fixture
    def backend(self, audio_config):
        """Create a PulseAudio backend instance with mocked pulsectl."""
        with patch("muteme_btn.audio.pulse.pulsectl.Pulse") as mock_pulse:
            mock_instance = Mock()
            mock_pulse.return_value = mock_instance
            backend = PulseAudioBackend(audio_config)
            backend._pulse = mock_instance
            return backend

    def test_backend_initialization(self, audio_config):
        """Test backend initializes with correct configuration."""
        with patch("muteme_btn.audio.pulse.pulsectl.Pulse") as mock_pulse:
            backend = PulseAudioBackend(audio_config)
            mock_pulse.assert_called_once_with("muteme-btn-control")
            assert backend.config == audio_config

    def test_get_default_source_success(self, backend):
        """Test getting default source information."""
        # Mock source object
        mock_source = Mock()
        mock_source.name = "alsa_input.pci-0000_00_1b.0.analog-stereo"
        mock_source.description = "Built-in Audio Analog Stereo"
        mock_source.mute = 0
        mock_source.index = 0

        backend._pulse.get_source_by_name.return_value = mock_source

        result = backend.get_default_source()

        assert result["name"] == mock_source.name
        assert result["description"] == mock_source.description
        assert result["muted"] is False
        assert result["index"] == 0

    def test_get_default_source_not_found(self, backend):
        """Test handling when default source is not found."""
        backend._pulse.get_source_by_name.side_effect = Exception("Source not found")

        with pytest.raises(Exception, match="Source not found"):
            backend.get_default_source()

    def test_set_mute_state_mute(self, backend):
        """Test muting a source."""
        mock_source = Mock()
        mock_source.index = 0
        backend._pulse.get_source_by_name.return_value = mock_source

        backend.set_mute_state("test_source", True)

        backend._pulse.get_source_by_name.assert_called_once_with("test_source")
        backend._pulse.source_mute.assert_called_once_with(mock_source.index, True)

    def test_set_mute_state_unmute(self, backend):
        """Test unmuting a source."""
        mock_source = Mock()
        mock_source.index = 1
        backend._pulse.get_source_by_name.return_value = mock_source

        backend.set_mute_state("test_source", False)

        backend._pulse.get_source_by_name.assert_called_once_with("test_source")
        backend._pulse.source_mute.assert_called_once_with(mock_source.index, False)

    def test_set_mute_state_default_source(self, backend):
        """Test muting/unmuting default source when no source specified."""
        mock_source = Mock()
        mock_source.name = "default_source"
        mock_source.index = 2
        backend._pulse.get_source_by_name.return_value = mock_source

        # Mock the default source lookup
        with patch.object(backend, "get_default_source", return_value={"name": "default_source"}):
            backend.set_mute_state(None, True)

        backend._pulse.source_mute.assert_called_once_with(2, True)

    def test_is_muted_true(self, backend):
        """Test checking if source is muted (returns True)."""
        mock_source = Mock()
        mock_source.mute = 1  # pulsectl uses 1 for muted
        backend._pulse.get_source_by_name.return_value = mock_source

        result = backend.is_muted("test_source")

        assert result is True

    def test_is_muted_false(self, backend):
        """Test checking if source is muted (returns False)."""
        mock_source = Mock()
        mock_source.mute = 0  # pulsectl uses 0 for unmuted
        backend._pulse.get_source_by_name.return_value = mock_source

        result = backend.is_muted("test_source")

        assert result is False

    def test_is_muted_default_source(self, backend):
        """Test checking mute status of default source."""
        mock_source = Mock()
        mock_source.mute = 1
        backend._pulse.get_source_by_name.return_value = mock_source

        with patch.object(backend, "get_default_source", return_value={"name": "default_source"}):
            result = backend.is_muted(None)

        assert result is True

    def test_list_sources(self, backend):
        """Test listing all available sources."""
        mock_source1 = Mock()
        mock_source1.name = "source1"
        mock_source1.description = "Test Source 1"
        mock_source1.mute = 0
        mock_source1.index = 0

        mock_source2 = Mock()
        mock_source2.name = "source2"
        mock_source2.description = "Test Source 2"
        mock_source2.mute = 1
        mock_source2.index = 1

        backend._pulse.source_list.return_value = [mock_source1, mock_source2]

        result = backend.list_sources()

        assert len(result) == 2
        assert result[0]["name"] == "source1"
        assert result[0]["muted"] is False
        assert result[1]["name"] == "source2"
        assert result[1]["muted"] is True

    def test_context_manager(self, audio_config):
        """Test backend works as context manager."""
        with patch("muteme_btn.audio.pulse.pulsectl.Pulse") as mock_pulse:
            mock_instance = Mock()
            mock_pulse.return_value = mock_instance

            with PulseAudioBackend(audio_config) as backend:
                assert backend._pulse == mock_instance

            mock_instance.close.assert_called_once()

    def test_connection_error_handling(self, audio_config):
        """Test handling of PulseAudio connection errors."""
        with patch(
            "muteme_btn.audio.pulse.pulsectl.Pulse", side_effect=Exception("Connection failed")
        ):
            with pytest.raises(Exception, match="Connection failed"):
                PulseAudioBackend(audio_config)

    def test_specific_source_config(self):
        """Test backend with specific source configuration."""
        config = AudioConfig(source_name="specific_source")

        with patch("muteme_btn.audio.pulse.pulsectl.Pulse"):
            backend = PulseAudioBackend(config)
            assert backend.config.source_name == "specific_source"
