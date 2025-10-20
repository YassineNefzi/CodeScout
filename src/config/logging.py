"""Logging configuration for the application."""

import os
import logging
import coloredlogs

from .settings import get_settings
from .singleton import Singleton


class Logger(metaclass=Singleton):
    """Logger class to manage application logging as a Singleton."""

    def __init__(self):
        """Initialize logging configuration once."""
        if not hasattr(self, "_initialized"):
            self.settings = get_settings()
            self._setup_logging()
            self._initialized = True

    def _setup_logging(self):
        """Setup logging configuration."""

        log_file = self.settings.LOG_FILE
        log_level = self.settings.LOG_LEVEL

        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_format = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_format)
            logging.getLogger().addHandler(file_handler)

        coloredlogs.install(level=log_level, logger=logging.getLogger())

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance with colored logs for console."""
        return logging.getLogger(name)