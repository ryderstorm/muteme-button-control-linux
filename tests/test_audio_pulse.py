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

    def test_get_default_sink_success(self, backend):
        """Test getting default sink information."""
        # Mock sink object
        mock_sink = Mock()
        mock_sink.name = "alsa_output.pci-0000_00_1b.0.analog-stereo"
        mock_sink.description = "Built-in Audio Analog Stereo"
        mock_sink.mute = 0
        mock_sink.index = 0

        backend._pulse.get_sink_by_name.return_value = mock_sink

        result = backend.get_default_sink()

        assert result["name"] == mock_sink.name
        assert result["description"] == mock_sink.description
        assert result["muted"] is False
        assert result["index"] == 0

    def test_get_default_sink_not_found(self, backend):
        """Test handling when default sink is not found."""
        backend._pulse.get_sink_by_name.side_effect = Exception("Sink not found")

        with pytest.raises(Exception, match="Sink not found"):
            backend.get_default_sink()

    def test_set_mute_state_mute(self, backend):
        """Test muting a sink."""
        mock_sink = Mock()
        mock_sink.index = 0
        backend._pulse.get_sink_by_name.return_value = mock_sink

        backend.set_mute_state("test_sink", True)

        backend._pulse.get_sink_by_name.assert_called_once_with("test_sink")
        backend._pulse.sink_mute.assert_called_once_with(mock_sink.index, True)

    def test_set_mute_state_unmute(self, backend):
        """Test unmuting a sink."""
        mock_sink = Mock()
        mock_sink.index = 1
        backend._pulse.get_sink_by_name.return_value = mock_sink

        backend.set_mute_state("test_sink", False)

        backend._pulse.get_sink_by_name.assert_called_once_with("test_sink")
        backend._pulse.sink_mute.assert_called_once_with(mock_sink.index, False)

    def test_set_mute_state_default_sink(self, backend):
        """Test muting/unmuting default sink when no sink specified."""
        mock_sink = Mock()
        mock_sink.name = "default_sink"
        mock_sink.index = 2
        backend._pulse.get_sink_by_name.return_value = mock_sink

        # Mock the default sink lookup
        with patch.object(backend, "get_default_sink", return_value={"name": "default_sink"}):
            backend.set_mute_state(None, True)

        backend._pulse.sink_mute.assert_called_once_with(2, True)

    def test_is_muted_true(self, backend):
        """Test checking if sink is muted (returns True)."""
        mock_sink = Mock()
        mock_sink.mute = 1  # pulsectl uses 1 for muted
        backend._pulse.get_sink_by_name.return_value = mock_sink

        result = backend.is_muted("test_sink")

        assert result is True

    def test_is_muted_false(self, backend):
        """Test checking if sink is muted (returns False)."""
        mock_sink = Mock()
        mock_sink.mute = 0  # pulsectl uses 0 for unmuted
        backend._pulse.get_sink_by_name.return_value = mock_sink

        result = backend.is_muted("test_sink")

        assert result is False

    def test_is_muted_default_sink(self, backend):
        """Test checking mute status of default sink."""
        mock_sink = Mock()
        mock_sink.mute = 1
        backend._pulse.get_sink_by_name.return_value = mock_sink

        with patch.object(backend, "get_default_sink", return_value={"name": "default_sink"}):
            result = backend.is_muted(None)

        assert result is True

    def test_list_sinks(self, backend):
        """Test listing all available sinks."""
        mock_sink1 = Mock()
        mock_sink1.name = "sink1"
        mock_sink1.description = "Test Sink 1"
        mock_sink1.mute = 0
        mock_sink1.index = 0

        mock_sink2 = Mock()
        mock_sink2.name = "sink2"
        mock_sink2.description = "Test Sink 2"
        mock_sink2.mute = 1
        mock_sink2.index = 1

        backend._pulse.sink_list.return_value = [mock_sink1, mock_sink2]

        result = backend.list_sinks()

        assert len(result) == 2
        assert result[0]["name"] == "sink1"
        assert result[0]["muted"] is False
        assert result[1]["name"] == "sink2"
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

    def test_specific_sink_config(self):
        """Test backend with specific sink configuration."""
        config = AudioConfig(sink_name="specific_sink")

        with patch("muteme_btn.audio.pulse.pulsectl.Pulse"):
            backend = PulseAudioBackend(config)
            assert backend.config.sink_name == "specific_sink"
