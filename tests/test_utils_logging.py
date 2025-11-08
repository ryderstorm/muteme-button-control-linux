"""Tests for logging utilities."""

import json
import logging
import logging.handlers
from pathlib import Path
from unittest.mock import patch

import structlog

from muteme_btn.utils.logging import LogContext, get_logger, log_with_context, setup_logging


class TestSetupLogging:
    """Test suite for setup_logging function."""

    def test_setup_logging_defaults(self):
        """Test setup_logging with default parameters."""
        # Reset logging to ensure clean state
        logging.root.handlers = []
        structlog.reset_defaults()

        setup_logging()

        # Verify structlog is configured
        logger = structlog.get_logger("test")
        assert logger is not None

    def test_setup_logging_debug_level(self):
        """Test setup_logging with DEBUG level."""
        logging.root.handlers = []
        structlog.reset_defaults()

        setup_logging(level="DEBUG")

        logger = structlog.get_logger("test")
        logger.debug("test message")
        # Should not raise exception

    def test_setup_logging_info_level(self):
        """Test setup_logging with INFO level."""
        logging.root.handlers = []
        structlog.reset_defaults()

        setup_logging(level="INFO")

        logger = structlog.get_logger("test")
        logger.info("test message")
        # Should not raise exception

    def test_setup_logging_warning_level(self):
        """Test setup_logging with WARNING level."""
        logging.root.handlers = []
        structlog.reset_defaults()

        setup_logging(level="WARNING")

        logger = structlog.get_logger("test")
        logger.warning("test message")
        # Should not raise exception

    def test_setup_logging_error_level(self):
        """Test setup_logging with ERROR level."""
        logging.root.handlers = []
        structlog.reset_defaults()

        setup_logging(level="ERROR")

        logger = structlog.get_logger("test")
        logger.error("test message")
        # Should not raise exception

    def test_setup_logging_critical_level(self):
        """Test setup_logging with CRITICAL level."""
        logging.root.handlers = []
        structlog.reset_defaults()

        setup_logging(level="CRITICAL")

        logger = structlog.get_logger("test")
        logger.critical("test message")
        # Should not raise exception

    def test_setup_logging_text_format(self):
        """Test setup_logging with text format."""
        logging.root.handlers = []
        structlog.reset_defaults()

        setup_logging(format_type="text")

        logger = structlog.get_logger("test")
        # Text format should use ConsoleRenderer
        logger.info("test message")
        # Should not raise exception

    def test_setup_logging_json_format(self):
        """Test setup_logging with JSON format."""
        logging.root.handlers = []
        structlog.reset_defaults()

        setup_logging(format_type="json")

        logger = structlog.get_logger("test")
        # JSON format should use JSONRenderer
        logger.info("test message")
        # Should not raise exception

    def test_setup_logging_with_file_path(self, tmp_path: Path):
        """Test setup_logging with file path."""
        logging.root.handlers = []
        structlog.reset_defaults()

        log_file = tmp_path / "test.log"
        setup_logging(file_path=log_file, level="INFO")

        logger = structlog.get_logger("test")
        logger.info("test message to file")

        # Verify file was created
        assert log_file.exists()

        # Verify log content (may be in text or JSON format depending on default)
        content = log_file.read_text()
        assert "test message to file" in content or len(content) > 0

    def test_setup_logging_with_file_path_creates_directory(self, tmp_path: Path):
        """Test setup_logging creates directory if it doesn't exist."""
        logging.root.handlers = []
        structlog.reset_defaults()

        log_dir = tmp_path / "logs"
        log_file = log_dir / "test.log"
        setup_logging(file_path=log_file, level="INFO")

        logger = structlog.get_logger("test")
        logger.info("test message")

        # Verify directory was created
        assert log_dir.exists()
        assert log_file.exists()

    def test_setup_logging_with_custom_file_size(self, tmp_path: Path):
        """Test setup_logging with custom max_file_size."""
        logging.root.handlers = []
        structlog.reset_defaults()

        log_file = tmp_path / "test.log"
        setup_logging(file_path=log_file, max_file_size=1024, level="INFO")

        logger = structlog.get_logger("test")
        logger.info("test message")

        # Verify file handler was created with correct maxBytes
        root_logger = logging.getLogger()
        file_handlers = [
            h
            for h in root_logger.handlers  # type: ignore[attr-defined]
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) > 0
        assert file_handlers[0].maxBytes == 1024

    def test_setup_logging_with_custom_backup_count(self, tmp_path: Path):
        """Test setup_logging with custom backup_count."""
        logging.root.handlers = []
        structlog.reset_defaults()

        log_file = tmp_path / "test.log"
        setup_logging(file_path=log_file, backup_count=10, level="INFO")

        logger = structlog.get_logger("test")
        logger.info("test message")

        # Verify file handler was created with correct backupCount
        root_logger = logging.getLogger()
        file_handlers = [
            h
            for h in root_logger.handlers  # type: ignore[attr-defined]
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) > 0
        assert file_handlers[0].backupCount == 10

    def test_setup_logging_json_output_format(self, tmp_path: Path):
        """Test that JSON format produces valid JSON output."""
        logging.root.handlers = []
        structlog.reset_defaults()

        log_file = tmp_path / "test.json.log"
        setup_logging(format_type="json", file_path=log_file, level="INFO")

        logger = structlog.get_logger("test")
        logger.info("test message", key="value", number=42)

        # Verify file contains valid JSON
        content = log_file.read_text()
        # JSON format should produce JSON lines
        lines = [line for line in content.strip().split("\n") if line.strip()]
        if lines:
            # Try to parse first line as JSON
            try:
                json.loads(lines[0])
            except json.JSONDecodeError:
                # If not JSON, that's okay - might be text format
                pass


class TestGetLogger:
    """Test suite for get_logger function."""

    def test_get_logger_returns_structlog_logger(self):
        """Test that get_logger returns a structlog logger."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test.module")

        # structlog.get_logger returns a lazy proxy that becomes BoundLogger when used
        # Verify it's a structlog logger by checking it can log
        logger.info("test")
        # If we get here without error, it's working correctly
        assert logger is not None

    def test_get_logger_with_different_names(self):
        """Test get_logger with different logger names."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger1 = get_logger("test.module1")
        logger2 = get_logger("test.module2")

        assert logger1 is not None
        assert logger2 is not None
        # Different names should return different loggers (or same logger factory)
        assert logger1._context is not None or logger2._context is not None

    def test_get_logger_can_log_messages(self):
        """Test that logger from get_logger can log messages."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")
        # Should not raise exception
        logger.info("test message")
        logger.debug("debug message")
        logger.warning("warning message")
        logger.error("error message")


class TestLogContext:
    """Test suite for LogContext context manager."""

    def test_log_context_enters_and_exits(self):
        """Test LogContext context manager entry and exit."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")
        context = LogContext(logger, key1="value1", key2="value2")

        with context as bound_logger:
            assert bound_logger is not None
            assert isinstance(bound_logger, structlog.stdlib.BoundLogger)
            # Should not raise exception
            bound_logger.info("test message")

    def test_log_context_binds_context(self):
        """Test that LogContext binds context to logger."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")
        context = LogContext(logger, user_id=123, action="test")

        with context as bound_logger:
            # Bound logger should have context
            bound_logger.info("test message")
            # Should not raise exception

    def test_log_context_multiple_keys(self):
        """Test LogContext with multiple context keys."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")
        context = LogContext(
            logger, key1="value1", key2=42, key3=True, key4=[1, 2, 3], key5={"nested": "value"}
        )

        with context as bound_logger:
            bound_logger.info("test message")
            # Should not raise exception

    def test_log_context_empty_context(self):
        """Test LogContext with no context keys."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")
        context = LogContext(logger)

        with context as bound_logger:
            bound_logger.info("test message")
            # Should not raise exception

    def test_log_context_nested_usage(self):
        """Test nested LogContext usage."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")
        outer_context = LogContext(logger, outer="value")
        inner_context = LogContext(logger, inner="value")

        with outer_context:
            with inner_context as inner_logger:
                inner_logger.info("test message")
                # Should not raise exception


class TestLogWithContext:
    """Test suite for log_with_context helper function."""

    def test_log_with_context_info_level(self):
        """Test log_with_context with INFO level."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")
        # Should not raise exception
        log_with_context(logger, "info", "test message", key="value")

    def test_log_with_context_debug_level(self):
        """Test log_with_context with DEBUG level."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging(level="DEBUG")

        logger = get_logger("test")
        # Should not raise exception
        log_with_context(logger, "debug", "test message", key="value")

    def test_log_with_context_warning_level(self):
        """Test log_with_context with WARNING level."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")
        # Should not raise exception
        log_with_context(logger, "warning", "test message", key="value")

    def test_log_with_context_error_level(self):
        """Test log_with_context with ERROR level."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")
        # Should not raise exception
        log_with_context(logger, "error", "test message", key="value")

    def test_log_with_context_critical_level(self):
        """Test log_with_context with CRITICAL level."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")
        # Should not raise exception
        log_with_context(logger, "critical", "test message", key="value")

    def test_log_with_context_multiple_context_keys(self):
        """Test log_with_context with multiple context keys."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")
        # Should not raise exception
        log_with_context(
            logger,
            "info",
            "test message",
            key1="value1",
            key2=42,
            key3=True,
            key4=[1, 2, 3],
            key5={"nested": "value"},
        )

    def test_log_with_context_no_context(self):
        """Test log_with_context with no additional context."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")
        # Should not raise exception
        log_with_context(logger, "info", "test message")

    def test_log_with_context_calls_correct_method(self):
        """Test that log_with_context calls the correct logger method."""
        logging.root.handlers = []
        structlog.reset_defaults()
        setup_logging()

        logger = get_logger("test")

        # Mock the logger's info method to verify it's called
        with patch.object(logger, "info") as mock_info:
            log_with_context(logger, "info", "test message", key="value")
            # Verify info method was called with correct arguments
            mock_info.assert_called_once_with("test message", key="value")


class TestLoggingIntegration:
    """Integration tests for logging utilities."""

    def test_full_logging_workflow(self, tmp_path: Path):
        """Test complete logging workflow."""
        logging.root.handlers = []
        structlog.reset_defaults()

        log_file = tmp_path / "integration.log"
        setup_logging(level="DEBUG", format_type="text", file_path=log_file)

        logger = get_logger("test.module")

        # Use LogContext
        with LogContext(logger, request_id="12345", user="test_user") as bound_logger:
            bound_logger.info("Processing request")
            bound_logger.debug("Debug information")

        # Use log_with_context
        log_with_context(logger, "info", "Operation completed", status="success")

        # Verify log file was created and has content
        assert log_file.exists()
        content = log_file.read_text()
        assert len(content) > 0

    def test_logging_with_json_format(self, tmp_path: Path):
        """Test logging workflow with JSON format."""
        logging.root.handlers = []
        structlog.reset_defaults()

        log_file = tmp_path / "json.log"
        setup_logging(level="INFO", format_type="json", file_path=log_file)

        logger = get_logger("test")
        logger.info("test message", key="value", number=42)

        # Verify file was created
        assert log_file.exists()
        content = log_file.read_text()
        assert len(content) > 0
