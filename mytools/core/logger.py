"""Logging utilities for mytools application."""

import logging
import sys
from typing import Optional

from .config import Config


class Logger:
    """Centralized logging management."""

    _logger: Optional[logging.Logger] = None

    @classmethod
    def get_logger(cls, name: str = "mytools") -> logging.Logger:
        """Get or create logger instance."""
        if cls._logger is None:
            cls._logger = cls._setup_logger(name)
        return cls._logger

    @classmethod
    def _setup_logger(cls, name: str) -> logging.Logger:
        """Set up logger with appropriate handlers and formatters."""
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if logger.handlers:
            return logger

        # Console handler for warnings and errors
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler for all logs
        try:
            file_handler = logging.FileHandler(Config.get_error_log_path())
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # If we can't write to the log file, log to console only
            logger.warning(f"Could not create log file: {e}")

        return logger

    @classmethod
    def log_exception(cls, message: str, exc: Exception) -> None:
        """Log an exception with context."""
        logger = cls.get_logger()
        logger.exception(f"{message}: {exc}")

    @classmethod
    def log_error(cls, message: str) -> None:
        """Log an error message."""
        logger = cls.get_logger()
        logger.error(message)

    @classmethod
    def log_warning(cls, message: str) -> None:
        """Log a warning message."""
        logger = cls.get_logger()
        logger.warning(message)

    @classmethod
    def log_info(cls, message: str) -> None:
        """Log an info message."""
        logger = cls.get_logger()
        logger.info(message)

    @classmethod
    def log_debug(cls, message: str) -> None:
        """Log a debug message."""
        logger = cls.get_logger()
        logger.debug(message)
