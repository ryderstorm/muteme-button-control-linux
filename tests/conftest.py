"""Pytest fixtures and configuration for muteme-btn-control tests."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from muteme_btn.config import AppConfig


@pytest.fixture
def runner() -> CliRunner:
    """Create a Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_config_file(temp_dir: Path) -> Path:
    """Create a temporary configuration file."""
    config_path = temp_dir / "test_config.toml"

    # Create a basic valid config
    config = AppConfig()
    config.to_toml_file(config_path)

    return config_path


@pytest.fixture
def mock_hid_device():
    """Create a mock HID device for testing."""
    mock_device = MagicMock()
    mock_device.vendor_id = 0x20A0
    mock_device.product_id = 0x42DA
    mock_device.path = b"/dev/hidraw0"
    mock_device.serial_number = "MTM123456"
    mock_device.manufacturer_string = "MuteMe"
    mock_device.product_string = "MuteMe Button"
    return mock_device


@pytest.fixture
def mock_pulseaudio():
    """Create a mock PulseAudio controller for testing."""
    mock_pulse = MagicMock()
    mock_pulse.get_source_list.return_value = [
        MagicMock(name="alsa_input.pci-0000_00_1b.0.analog-stereo", index=0),
        MagicMock(name="alsa_input.usb-MuteMe_Button-00.analog-stereo", index=1),
    ]
    mock_pulse.source_output_list.return_value = []
    mock_pulse.source_mute.return_value = False
    return mock_pulse
