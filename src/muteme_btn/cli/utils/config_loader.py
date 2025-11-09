"""Configuration loading utilities for CLI commands."""

import sys
from pathlib import Path

import typer

from ...config import AppConfig, LogLevel


def find_config_file(config_path: Path | None) -> Path | None:
    """Find configuration file in standard locations.

    Args:
        config_path: Explicit config path from CLI (takes precedence)

    Returns:
        Path to config file if found, None otherwise
    """
    if config_path and config_path.exists():
        return config_path

    # Standard locations (in order of precedence)
    standard_locations = [
        Path("muteme.toml"),  # Current directory
        Path.home() / ".config" / "muteme" / "muteme.toml",
        Path("/etc/muteme/muteme.toml"),
    ]

    for location in standard_locations:
        if location.exists():
            return location

    return None


def load_config(config_path: Path | None, log_level: str | None) -> AppConfig:
    """Load application configuration.

    Args:
        config_path: Optional explicit config file path
        log_level: Optional log level override from CLI

    Returns:
        Loaded AppConfig instance
    """
    found_config = find_config_file(config_path)

    # Fail fast if explicit config path was provided but doesn't exist
    if config_path and found_config is None:
        typer.echo(f"❌ Configuration file not found: {config_path}", err=True)
        sys.exit(1)

    if found_config:
        try:
            config = AppConfig.from_toml_file(found_config)
            # Override log level if provided via CLI
            if log_level:
                config.logging.level = LogLevel(log_level.upper())
            return config
        except Exception as e:
            typer.echo(f"❌ Failed to load configuration from {found_config}: {e}", err=True)
            sys.exit(1)
    else:
        # Use defaults
        config = AppConfig()
        if log_level:
            config.logging.level = LogLevel(log_level.upper())
        return config
