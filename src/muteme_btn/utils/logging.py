"""Structured logging configuration for MuteMe Button Control."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

import structlog


def setup_logging(
    level: str = "INFO",
    format_type: str = "text",
    file_path: Path | None = None,
    max_file_size: int = 10485760,
    backup_count: int = 5,
) -> None:
    """Configure structured logging with the specified parameters.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Output format - 'text' or 'json'
        file_path: Optional log file path. If None, logs to stdout.
        max_file_size: Maximum log file size in bytes (for file logging)
        backup_count: Number of backup files to keep (for file logging)
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout if file_path is None else None,
        level=getattr(logging, level.upper()),
    )

    # Configure file handler if file_path is provided
    if file_path:
        # Ensure log directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, level.upper()))

        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

    # Configure structlog processors based on format type
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if format_type == "json":
        processors.extend(
            [
                structlog.processors.dict_tracebacks,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ]
        )
    else:  # text format
        processors.extend(
            [
                structlog.processors.UnicodeDecoder(),
                structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty()),
            ]
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger instance
    """
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding structured log context."""

    def __init__(self, logger: structlog.stdlib.BoundLogger, **context: Any):
        """Initialize log context.

        Args:
            logger: Logger instance to bind context to
            **context: Key-value pairs to add to log context
        """
        self.logger = logger
        self.context = context
        self.bound_logger = None

    def __enter__(self) -> structlog.stdlib.BoundLogger:
        """Enter context and return bound logger."""
        self.bound_logger = self.logger.bind(**self.context)
        return self.bound_logger

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context (no cleanup needed)."""
        pass


# Convenience function for common logging patterns
def log_with_context(
    logger: structlog.stdlib.BoundLogger,
    level: str,
    message: str,
    **context: Any,
) -> None:
    """Log a message with additional context.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional structured context
    """
    log_method = getattr(logger, level.lower())
    log_method(message, **context)
