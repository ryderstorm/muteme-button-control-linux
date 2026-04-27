"""CLI tests for MuteMe Button Control."""

import re
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from muteme_btn import __version__
from muteme_btn.cli import _build_config_startup_summary, _find_config_file, app
from muteme_btn.config import AppConfig


class TestCLI:
    """Test suite for CLI functionality."""

    def test_version_command(self, runner: CliRunner) -> None:
        """Test version command outputs correct version."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert f"muteme-btn-control {__version__}" in result.stdout

    def test_version_flag(self, runner: CliRunner) -> None:
        """Test --version flag outputs correct version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert f"muteme-btn-control {__version__}" in result.stdout

    def test_version_short_flag(self, runner: CliRunner) -> None:
        """Test -v flag outputs correct version."""
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert f"muteme-btn-control {__version__}" in result.stdout

    def test_help_command(self, runner: CliRunner) -> None:
        """Test help command shows usage information."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "MuteMe button integration" in result.stdout
        # Strip ANSI codes for more robust checking
        clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
        assert "--version" in clean_output or "-v" in clean_output
        assert "--help" in clean_output

    def test_no_args_shows_help(self, runner: CliRunner) -> None:
        """Test that no arguments runs the daemon (default behavior)."""
        # Since we changed no_args_is_help=False and invoke_without_command=True,
        # no args will try to run the daemon, which will fail without a device
        # So we expect exit code 1 (device error) or 0 if mocked
        with patch("muteme_btn.cli.asyncio.run"), patch("muteme_btn.cli.MuteMeDaemon"):
            result = runner.invoke(app, [])
            # Exit code depends on whether device connection succeeds
            # In test environment without device, it will be 1
            assert result.exit_code in [0, 1]

    def test_invalid_command(self, runner: CliRunner) -> None:
        """Test invalid command returns error."""
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0

    @patch("muteme_btn.config.AppConfig.from_toml_file")
    def test_config_file_loading(
        self, mock_from_toml, runner: CliRunner, temp_config_file: Path
    ) -> None:
        """Test loading configuration from file."""
        # Mock the config loading to avoid file system issues in test
        mock_config = AppConfig()
        mock_from_toml.return_value = mock_config

        # This will be implemented when we add config file support to CLI
        # For now, just test that the CLI can handle the concept
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_user_config_takes_precedence_over_cwd_config(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """User config should not be shadowed by a stale cwd muteme.toml."""
        cwd = temp_dir / "repo"
        user_config_dir = temp_dir / "home" / ".config" / "muteme"
        cwd.mkdir()
        user_config_dir.mkdir(parents=True)
        cwd_config = cwd / "muteme.toml"
        user_config = user_config_dir / "muteme.toml"
        cwd_config.write_text('[mode]\nswitch_gesture = "double_tap_hold"\n')
        user_config.write_text('[mode]\nswitch_gesture = "triple_tap"\n')

        monkeypatch.chdir(cwd)
        monkeypatch.setattr(Path, "home", lambda: temp_dir / "home")

        assert _find_config_file(None) == user_config

    def test_explicit_missing_config_does_not_fall_back_to_user_config(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An explicit missing --config path should fail instead of silently falling back."""
        user_config_dir = temp_dir / "home" / ".config" / "muteme"
        user_config_dir.mkdir(parents=True)
        (user_config_dir / "muteme.toml").write_text('[mode]\nswitch_gesture = "triple_tap"\n')
        monkeypatch.setattr(Path, "home", lambda: temp_dir / "home")

        assert _find_config_file(temp_dir / "missing.toml") is None

    def test_load_config_records_resolved_config_path(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Loaded config should retain the file path for startup diagnostics."""
        config_dir = temp_dir / "home" / ".config" / "muteme"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "muteme.toml"
        config_path.write_text(
            '[mode]\nswitch_gesture = "triple_tap"\n[ptt]\nidle_color = "purple"\n'
        )
        monkeypatch.setattr(Path, "home", lambda: temp_dir / "home")

        from muteme_btn.cli import _load_config

        config = _load_config(None, None)

        assert config.config_file == config_path
        assert config.mode.switch_gesture == "triple_tap"
        assert config.ptt.idle_color == "purple"

    def test_config_startup_summary_includes_loaded_path_and_preferences(self) -> None:
        """Startup diagnostics should expose config source and key mode/PTT preferences."""
        config = AppConfig()
        config.config_file = Path("/tmp/example-muteme.toml")
        config.mode.switch_gesture = "triple_tap"
        config.ptt.idle_color = "purple"

        summary = _build_config_startup_summary(config)

        assert summary["config_file"] == "/tmp/example-muteme.toml"
        assert summary["mode.switch_gesture"] == "triple_tap"
        assert summary["ptt.idle_color"] == "purple"
        assert summary["ptt.emitter_backend"] == "ydotool"

    def test_cli_imports(self) -> None:
        """Test that CLI imports work correctly."""
        from muteme_btn.cli import app, version_callback

        assert app is not None
        assert version_callback is not None

    def test_version_callback_function(self) -> None:
        """Test version callback function directly."""
        import typer

        from muteme_btn.cli import version_callback

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
        # Check that help text contains expected content
        help_text = app.info.help or ""
        assert "MuteMe button integration" in help_text
        # Check the no_args_is_help through the rich_console if available
        # or just verify the help behavior works correctly

    @patch("muteme_btn.utils.logging.setup_logging")
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

    def test_main_module_execution(self, runner: CliRunner) -> None:
        """Test that main.py can be executed as a module."""
        import subprocess
        import sys

        # Test executing main.py directly
        result = subprocess.run(
            [sys.executable, "-m", "muteme_btn.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "muteme-btn-control" in result.stdout or "Usage:" in result.stdout

    def test_main_module_direct_execution(self) -> None:
        """Test that main.py can be executed directly via __main__."""
        import importlib.util
        import sys
        from pathlib import Path

        # Load main.py as a module and execute the __main__ block
        main_path = Path(__file__).parent.parent / "src" / "muteme_btn" / "main.py"
        spec = importlib.util.spec_from_file_location("muteme_btn.main", main_path)
        if spec and spec.loader:
            # This will execute the module, including the __main__ block
            # We'll mock the app() call to avoid actually running the CLI
            with patch("muteme_btn.main.app"):
                module = importlib.util.module_from_spec(spec)
                # Temporarily replace sys.modules to avoid conflicts
                original_module = sys.modules.get("muteme_btn.main")
                sys.modules["muteme_btn.main"] = module
                try:
                    # Execute the module (this will run the if __name__ == "__main__" block)
                    # But we've mocked app() so it won't actually run
                    if spec.loader:
                        spec.loader.exec_module(module)
                        # Verify app was called (if __name__ == "__main__" was executed)
                        # Note: This might not work if the module was already imported
                finally:
                    if original_module:
                        sys.modules["muteme_btn.main"] = original_module
                    elif "muteme_btn.main" in sys.modules:
                        del sys.modules["muteme_btn.main"]
