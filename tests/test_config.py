"""Configuration tests for MuteMe Button Control."""

from pathlib import Path

import pytest
import toml

from muteme_btn.config import (
    AppConfig,
    DeviceConfig,
    AudioConfig,
    LoggingConfig,
    LogLevel,
    LogFormat,
)


class TestDeviceConfig:
    """Test suite for DeviceConfig."""

    def test_default_device_config(self) -> None:
        """Test default device configuration values."""
        config = DeviceConfig()
        assert config.vid == 0x20a0
        assert config.pid == 0x42da
        assert config.timeout == 5.0

    def test_custom_device_config(self) -> None:
        """Test custom device configuration values."""
        config = DeviceConfig(vid=0x1234, pid=0x5678, timeout=10.0)
        assert config.vid == 0x1234
        assert config.pid == 0x5678
        assert config.timeout == 10.0

    def test_device_config_validation(self) -> None:
        """Test device configuration validation."""
        # Test timeout validation
        with pytest.raises(ValueError):
            DeviceConfig(timeout=0.05)  # Too small
        
        with pytest.raises(ValueError):
            DeviceConfig(timeout=61.0)  # Too large
        
        # Valid timeout should work
        config = DeviceConfig(timeout=1.0)
        assert config.timeout == 1.0


class TestAudioConfig:
    """Test suite for AudioConfig."""

    def test_default_audio_config(self) -> None:
        """Test default audio configuration values."""
        config = AudioConfig()
        assert config.backend == "pulseaudio"
        assert config.sink_name is None
        assert config.poll_interval == 0.1

    def test_custom_audio_config(self) -> None:
        """Test custom audio configuration values."""
        config = AudioConfig(
            backend="pipewire",
            sink_name="custom_sink",
            poll_interval=0.5
        )
        assert config.backend == "pipewire"
        assert config.sink_name == "custom_sink"
        assert config.poll_interval == 0.5

    def test_audio_config_validation(self) -> None:
        """Test audio configuration validation."""
        # Test poll_interval validation
        with pytest.raises(ValueError):
            AudioConfig(poll_interval=0.005)  # Too small
        
        with pytest.raises(ValueError):
            AudioConfig(poll_interval=1.5)  # Too large
        
        # Valid poll_interval should work
        config = AudioConfig(poll_interval=0.2)
        assert config.poll_interval == 0.2


class TestLoggingConfig:
    """Test suite for LoggingConfig."""

    def test_default_logging_config(self) -> None:
        """Test default logging configuration values."""
        config = LoggingConfig()
        assert config.level == LogLevel.INFO
        assert config.format == LogFormat.TEXT
        assert config.file_path is None
        assert config.max_file_size == 10485760
        assert config.backup_count == 5

    def test_custom_logging_config(self, temp_dir: Path) -> None:
        """Test custom logging configuration values."""
        log_file = temp_dir / "test.log"
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            format=LogFormat.JSON,
            file_path=log_file,
            max_file_size=2097152,
            backup_count=10
        )
        assert config.level == LogLevel.DEBUG
        assert config.format == LogFormat.JSON
        assert config.file_path == log_file
        assert config.max_file_size == 2097152
        assert config.backup_count == 10

    def test_logging_config_validation(self, temp_dir: Path) -> None:
        """Test logging configuration validation."""
        # Test file_path validation - non-existent directory
        non_existent_path = Path("/non/existent/directory/test.log")
        with pytest.raises(ValueError, match="Log file directory does not exist"):
            LoggingConfig(file_path=non_existent_path)
        
        # Test max_file_size validation
        with pytest.raises(ValueError):
            LoggingConfig(max_file_size=512)  # Too small
        
        with pytest.raises(ValueError):
            LoggingConfig(backup_count=0)  # Too small
        
        with pytest.raises(ValueError):
            LoggingConfig(backup_count=25)  # Too large
        
        # Valid values should work
        log_file = temp_dir / "test.log"
        config = LoggingConfig(
            file_path=log_file,
            max_file_size=2048,
            backup_count=15
        )
        assert config.file_path == log_file
        assert config.max_file_size == 2048
        assert config.backup_count == 15


class TestAppConfig:
    """Test suite for AppConfig."""

    def test_default_app_config(self) -> None:
        """Test default application configuration values."""
        config = AppConfig()
        assert isinstance(config.device, DeviceConfig)
        assert isinstance(config.audio, AudioConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert config.daemon is False
        assert config.config_file is None

    def test_custom_app_config(self, temp_dir: Path) -> None:
        """Test custom application configuration values."""
        config_file = temp_dir / "config.toml"
        config = AppConfig(
            daemon=True,
            config_file=config_file,
            device=DeviceConfig(vid=0x1234),
            audio=AudioConfig(backend="pipewire"),
            logging=LoggingConfig(level=LogLevel.DEBUG)
        )
        assert config.daemon is True
        assert config.config_file == config_file
        assert config.device.vid == 0x1234
        assert config.audio.backend == "pipewire"
        assert config.logging.level == LogLevel.DEBUG

    def test_app_config_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden in AppConfig."""
        with pytest.raises(ValueError):
            AppConfig(invalid_field="should_fail")

    def test_from_toml_file_success(self, temp_dir: Path) -> None:
        """Test successful loading from TOML file."""
        config_path = temp_dir / "test_config.toml"
        
        # Create a test TOML file
        test_config = {
            "daemon": True,
            "device": {
                "vid": 0x1234,
                "pid": 0x5678,
                "timeout": 10.0
            },
            "audio": {
                "backend": "pipewire",
                "sink_name": "test_sink",
                "poll_interval": 0.5
            },
            "logging": {
                "level": "DEBUG",
                "format": "json",
                "max_file_size": 2097152,
                "backup_count": 10
            }
        }
        
        with open(config_path, 'w') as f:
            toml.dump(test_config, f)
        
        # Load the configuration
        config = AppConfig.from_toml_file(config_path)
        
        assert config.daemon is True
        assert config.device.vid == 0x1234
        assert config.device.pid == 0x5678
        assert config.device.timeout == 10.0
        assert config.audio.backend == "pipewire"
        assert config.audio.sink_name == "test_sink"
        assert config.audio.poll_interval == 0.5
        assert config.logging.level == LogLevel.DEBUG
        assert config.logging.format == LogFormat.JSON
        assert config.logging.max_file_size == 2097152
        assert config.logging.backup_count == 10

    def test_from_toml_file_not_found(self) -> None:
        """Test loading from non-existent TOML file."""
        non_existent_path = Path("/non/existent/config.toml")
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            AppConfig.from_toml_file(non_existent_path)

    def test_from_toml_file_invalid_toml(self, temp_dir: Path) -> None:
        """Test loading from invalid TOML file."""
        config_path = temp_dir / "invalid_config.toml"
        
        # Write invalid TOML
        with open(config_path, 'w') as f:
            f.write("invalid toml content [[[")
        
        with pytest.raises(ValueError, match="Invalid configuration file"):
            AppConfig.from_toml_file(config_path)

    def test_from_toml_file_invalid_config_data(self, temp_dir: Path) -> None:
        """Test loading TOML file with invalid configuration data."""
        config_path = temp_dir / "invalid_data_config.toml"
        
        # Create TOML with invalid data (violates validation rules)
        test_config = {
            "device": {
                "timeout": 0.05  # Too small, should fail validation
            }
        }
        
        with open(config_path, 'w') as f:
            toml.dump(test_config, f)
        
        with pytest.raises(ValueError, match="Invalid configuration file"):
            AppConfig.from_toml_file(config_path)

    def test_to_toml_file(self, temp_dir: Path) -> None:
        """Test saving configuration to TOML file."""
        config_path = temp_dir / "output_config.toml"
        
        # Create a config
        original_config = AppConfig(
            daemon=True,
            device=DeviceConfig(vid=0x1234),
            audio=AudioConfig(backend="pipewire"),
            logging=LoggingConfig(level=LogLevel.DEBUG)
        )
        
        # Save it
        original_config.to_toml_file(config_path)
        
        # Verify file exists and has content
        assert config_path.exists()
        
        # Load and verify
        loaded_config = AppConfig.from_toml_file(config_path)
        assert loaded_config.daemon is True
        assert loaded_config.device.vid == 0x1234
        assert loaded_config.audio.backend == "pipewire"
        assert loaded_config.logging.level == LogLevel.DEBUG

    def test_to_toml_file_creates_directory(self, temp_dir: Path) -> None:
        """Test that to_toml_file creates parent directories."""
        config_path = temp_dir / "nested" / "dir" / "config.toml"
        
        # Ensure directory doesn't exist
        assert not config_path.parent.exists()
        
        # Save config
        config = AppConfig()
        config.to_toml_file(config_path)
        
        # Verify directory was created and file exists
        assert config_path.exists()
        assert config_path.parent.exists()


class TestConfigEnums:
    """Test suite for configuration enums."""

    def test_log_level_values(self) -> None:
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"

    def test_log_format_values(self) -> None:
        """Test LogFormat enum values."""
        assert LogFormat.TEXT == "text"
        assert LogFormat.JSON == "json"

    def test_enum_serialization(self) -> None:
        """Test that enums serialize correctly."""
        config = LoggingConfig(level=LogLevel.DEBUG, format=LogFormat.JSON)
        data = config.model_dump()
        
        assert data["level"] == "DEBUG"
        assert data["format"] == "json"
