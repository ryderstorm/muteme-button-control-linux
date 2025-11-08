"""Configuration models for MuteMe Button Control."""

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class LogLevel(str, Enum):
    """Available log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Available log formats."""
    TEXT = "text"
    JSON = "json"


class DeviceConfig(BaseModel):
    """Device-specific configuration."""
    model_config = ConfigDict(validate_assignment=True)
    
    vid: int = Field(default=0x20a0, description="USB Vendor ID for MuteMe device")
    pid: int = Field(default=0x42da, description="USB Product ID for MuteMe device")
    timeout: float = Field(default=5.0, ge=0.1, le=60.0, description="Device connection timeout in seconds")


class AudioConfig(BaseModel):
    """Audio backend configuration."""
    model_config = ConfigDict(validate_assignment=True)
    
    backend: str = Field(default="pulseaudio", description="Audio backend to use")
    sink_name: Optional[str] = Field(default=None, description="Specific PulseAudio sink name to control")
    poll_interval: float = Field(default=0.1, ge=0.01, le=1.0, description="Audio state polling interval in seconds")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    model_config = ConfigDict(validate_assignment=True)
    
    level: LogLevel = Field(default=LogLevel.INFO, description="Minimum log level")
    format: LogFormat = Field(default=LogFormat.TEXT, description="Log output format")
    file_path: Optional[Path] = Field(default=None, description="Log file path (optional, defaults to stdout)")
    max_file_size: int = Field(default=10485760, ge=1024, description="Maximum log file size in bytes")
    backup_count: int = Field(default=5, ge=1, le=20, description="Number of backup log files to keep")

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v) -> Optional[Path]:
        """Validate that the file path directory exists if file_path is provided."""
        if v is not None:
            if not v.parent.exists():
                raise ValueError(f"Log file directory does not exist: {v.parent}")
        return v


class AppConfig(BaseModel):
    """Main application configuration."""
    model_config = ConfigDict(
        extra="forbid",  # Forbid extra fields to catch configuration errors
        validate_assignment=True
    )
    
    device: DeviceConfig = Field(default_factory=DeviceConfig, description="Device configuration")
    audio: AudioConfig = Field(default_factory=AudioConfig, description="Audio configuration")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")
    daemon: bool = Field(default=False, description="Run in daemon mode")
    config_file: Optional[Path] = Field(default=None, description="Path to configuration file")

    @classmethod
    def from_toml_file(cls, config_path: Path) -> "AppConfig":
        """Load configuration from a TOML file.
        
        Args:
            config_path: Path to the TOML configuration file
            
        Returns:
            AppConfig instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            import toml
            config_data = toml.load(config_path)
            return cls(**config_data)
        except Exception as e:
            raise ValueError(f"Invalid configuration file {config_path}: {e}")

    def to_toml_file(self, config_path: Path) -> None:
        """Save configuration to a TOML file.
        
        Args:
            config_path: Path where to save the TOML configuration file
        """
        import toml
        
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get the model dump with enum values as strings
        config_data = self.model_dump(mode='json')
        
        with open(config_path, 'w') as f:
            toml.dump(config_data, f)
