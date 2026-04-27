"""Configuration models for MuteMe Button Control."""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class OperationMode(str, Enum):
    """Supported button operating modes."""

    NORMAL = "normal"
    PTT = "ptt"


class DeviceConfig(BaseModel):
    """Device-specific configuration."""

    model_config = ConfigDict(validate_assignment=True)

    vid: int = Field(default=0x20A0, description="USB Vendor ID for MuteMe device")
    pid: int = Field(default=0x42DA, description="USB Product ID for MuteMe device")
    timeout: float = Field(
        default=5.0, ge=0.1, le=60.0, description="Device connection timeout in seconds"
    )
    poll_interval_ms: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Main loop poll interval in milliseconds (default: 10ms)",
    )
    poll_timeout_ms: int = Field(
        default=100,
        ge=10,
        le=5000,
        description="Main loop poll timeout in milliseconds (default: 100ms)",
    )


class AudioConfig(BaseModel):
    """Audio backend configuration."""

    model_config = ConfigDict(validate_assignment=True)

    backend: str = Field(default="pulseaudio", description="Audio backend to use")
    source_name: str | None = Field(
        default=None, description="Specific PulseAudio source name to control (microphone input)"
    )
    poll_interval: float = Field(
        default=0.1, ge=0.01, le=1.0, description="Audio state polling interval in seconds"
    )

    @field_validator("backend")
    @classmethod
    def validate_backend(cls, value: str) -> str:
        """Validate and normalize supported audio backend names."""
        normalized = value.lower()
        if normalized not in {"auto", "pulseaudio", "pipewire", "coreaudio"}:
            raise ValueError(
                "Unsupported audio backend; expected auto, pulseaudio, pipewire, or coreaudio"
            )
        return normalized


class ModeConfig(BaseModel):
    """Operating mode and gesture configuration."""

    model_config = ConfigDict(validate_assignment=True)

    default: OperationMode = Field(
        default=OperationMode.NORMAL,
        description="Default operating mode: normal toggle or ptt hold-to-talk",
    )
    switch_gesture: str = Field(
        default="double_tap_hold",
        description="Gesture used to switch modes; currently double_tap_hold",
    )
    double_tap_timeout_ms: int = Field(
        default=300,
        ge=50,
        le=2000,
        description="Maximum time between taps for mode-switch gesture detection",
    )
    switch_hold_threshold_ms: int = Field(
        default=800,
        ge=100,
        le=5000,
        description="How long the second tap must be held to switch modes",
    )
    debounce_time_ms: int = Field(
        default=10,
        ge=0,
        le=250,
        description="Minimum time between press events to ignore bounce",
    )

    @field_validator("switch_gesture")
    @classmethod
    def validate_switch_gesture(cls, value: str) -> str:
        """Validate the supported mode-switch gesture."""
        if value != "double_tap_hold":
            raise ValueError("Only double_tap_hold is currently supported as switch_gesture")
        return value


class PTTConfig(BaseModel):
    """Push-to-talk configuration."""

    model_config = ConfigDict(validate_assignment=True)

    key: str = Field(default="f19", description="Synthetic key to emit for PTT mode")
    idle_color: str = Field(default="blue", description="LED color for PTT idle state")
    active_color: str = Field(default="yellow", description="LED color for active PTT hold")
    emitter_backend: str = Field(
        default="ydotool",
        description="F19 emitter backend: auto, ydotool, evdev, or Windows sendinput",
    )

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        """Only F19 is supported by the initial PTT emitter."""
        normalized = value.lower()
        if normalized != "f19":
            raise ValueError("Only f19 is currently supported for PTT key emulation")
        return normalized

    @field_validator("emitter_backend")
    @classmethod
    def validate_emitter_backend(cls, value: str) -> str:
        """Validate PTT emitter backend."""
        normalized = value.lower()
        if normalized not in {"auto", "ydotool", "evdev", "sendinput"}:
            raise ValueError(
                "Unsupported PTT emitter backend; expected auto, ydotool, evdev, or sendinput"
            )
        return normalized


class LoggingConfig(BaseModel):
    """Logging configuration."""

    model_config = ConfigDict(validate_assignment=True)

    level: LogLevel = Field(default=LogLevel.INFO, description="Minimum log level")
    format: LogFormat = Field(default=LogFormat.TEXT, description="Log output format")
    file_path: Path | None = Field(
        default=None, description="Log file path (optional, defaults to stdout)"
    )
    max_file_size: int = Field(
        default=10485760, ge=1024, description="Maximum log file size in bytes"
    )
    backup_count: int = Field(
        default=5, ge=1, le=20, description="Number of backup log files to keep"
    )

    @field_validator("level", mode="before")
    @classmethod
    def normalize_level(cls, value: LogLevel | str) -> LogLevel:
        """Normalize log level string to uppercase before enum validation."""
        if isinstance(value, LogLevel):
            return value
        try:
            return LogLevel(value.upper())
        except ValueError as exc:
            raise ValueError(f"Unsupported log level: {value}") from exc

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v) -> Path | None:
        """Validate that the file path directory exists if file_path is provided."""
        if v is not None:
            if not v.parent.exists():
                raise ValueError(f"Log file directory does not exist: {v.parent}")
        return v


class AppConfig(BaseModel):
    """Main application configuration."""

    model_config = ConfigDict(
        extra="forbid",  # Forbid extra fields to catch configuration errors
        validate_assignment=True,
    )

    device: DeviceConfig = Field(default_factory=DeviceConfig, description="Device configuration")
    audio: AudioConfig = Field(default_factory=AudioConfig, description="Audio configuration")
    mode: ModeConfig = Field(default_factory=ModeConfig, description="Operating mode configuration")
    ptt: PTTConfig = Field(default_factory=PTTConfig, description="Push-to-talk configuration")
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    daemon: bool = Field(default=False, description="Run in daemon mode")
    config_file: Path | None = Field(default=None, description="Path to configuration file")

    @classmethod
    def from_toml_file(cls, config_path: Path) -> "AppConfig":
        """Load configuration from a TOML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            import toml

            config_data = toml.load(config_path)
            return cls(**config_data)
        except Exception as e:
            raise ValueError(f"Invalid configuration file {config_path}: {e}") from e

    def to_toml_file(self, config_path: Path) -> None:
        """Save configuration to a TOML file."""
        import toml

        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_data = self.model_dump(mode="json")
        with open(config_path, "w") as f:
            toml.dump(config_data, f)
