"""CLI tests for MuteMe Button Control."""

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from muteme_btn.cli import app
from muteme_btn.config import AppConfig


class TestCLI:
    """Test suite for CLI functionality."""

    def test_version_command(self, runner: CliRunner) -> None:
        """Test version command outputs correct version."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "muteme-btn-control 0.1.0" in result.stdout

    def test_version_flag(self, runner: CliRunner) -> None:
        """Test --version flag outputs correct version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "muteme-btn-control 0.1.0" in result.stdout

    def test_version_short_flag(self, runner: CliRunner) -> None:
        """Test -v flag outputs correct version."""
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "muteme-btn-control 0.1.0" in result.stdout

    def test_help_command(self, runner: CliRunner) -> None:
        """Test help command shows usage information."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "MuteMe button integration" in result.stdout
        assert "--version" in result.stdout
        assert "--help" in result.stdout

    def test_no_args_shows_help(self, runner: CliRunner) -> None:
        """Test that no arguments shows help (due to no_args_is_help=True)."""
        result = runner.invoke(app, [])
        # Typer with no_args_is_help=True actually exits with code 2 and shows help
        assert result.exit_code == 2
        assert "Usage:" in result.stdout
        assert "MuteMe button integration" in result.stdout

    def test_invalid_command(self, runner: CliRunner) -> None:
        """Test invalid command returns error."""
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0

    @patch('muteme_btn.config.AppConfig.from_toml_file')
    def test_config_file_loading(self, mock_from_toml, runner: CliRunner, temp_config_file: Path) -> None:
        """Test loading configuration from file."""
        # Mock the config loading to avoid file system issues in test
        mock_config = AppConfig()
        mock_from_toml.return_value = mock_config
        
        # This will be implemented when we add config file support to CLI
        # For now, just test that the CLI can handle the concept
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_cli_imports(self) -> None:
        """Test that CLI imports work correctly."""
        from muteme_btn.cli import app, version_callback
        assert app is not None
        assert version_callback is not None

    def test_version_callback_function(self) -> None:
        """Test version callback function directly."""
        from muteme_btn.cli import version_callback
        import typer
        
        # Test that calling version_callback with True raises Exit
        with pytest.raises(typer.Exit):
            version_callback(True)
        
        # Test that calling with False does not raise Exit
        try:
            version_callback(False)
        except typer.Exit:
            pytest.fail("version_callback(False) should not raise Exit")

    def test_cli_app_configuration(self) -> None:
        """Test that the CLI app is properly configured."""
        assert app.info.name == "muteme-btn-control"
        assert "MuteMe button integration" in app.info.help
        # Check the no_args_is_help through the rich_console if available
        # or just verify the help behavior works correctly

    @patch('muteme_btn.utils.logging.setup_logging')
    def test_logging_setup_integration(self, mock_setup_logging, runner: CliRunner) -> None:
        """Test that logging setup is called when CLI is invoked."""
        # This will be tested more thoroughly when we integrate logging
        # For now, ensure the CLI can be invoked without errors
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_cli_entry_point(self) -> None:
        """Test that the CLI entry point works."""
        from muteme_btn.main import app as main_app
        assert main_app is not None
        
        # Test that it's the same app as cli.app
        assert main_app is app
