"""MuteMe Button Control - A Linux CLI tool for MuteMe button integration."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Read version from installed package metadata (single source of truth: pyproject.toml)
    __version__ = version("muteme-btn-control")
except PackageNotFoundError:
    # Fallback for development when package isn't installed
    # Read directly from pyproject.toml
    from pathlib import Path
    from tomllib import load as load_toml

    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        with pyproject_path.open("rb") as f:
            pyproject = load_toml(f)
            __version__ = pyproject["project"]["version"]
    else:
        __version__ = "0.0.0-dev"
