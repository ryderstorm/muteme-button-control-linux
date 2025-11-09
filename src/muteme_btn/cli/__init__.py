"""CLI package for MuteMe Button Control."""

# Create app first (before importing commands)
from .app import _setup_main_callback, app

# Import commands to register them (they import app from this package)
from .commands import check_device, run, test_device, version  # noqa: F401

# Set up main callback after commands are registered
_setup_main_callback()

__all__ = ["app"]
