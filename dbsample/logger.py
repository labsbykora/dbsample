"""Logging configuration and utilities."""

import logging
import sys
from typing import Optional
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration."""
    ERROR = logging.ERROR
    WARN = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG


class Logger:
    """Configured logger for dbsample utility."""
    
    _instance: Optional['Logger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._logger = logging.getLogger("dbsample")
            self._logger.setLevel(logging.INFO)
            self._handler: Optional[logging.StreamHandler] = None
            self._file_handler: Optional[logging.FileHandler] = None
    
    def configure(
        self,
        level: LogLevel = LogLevel.INFO,
        log_file: Optional[str] = None,
    ):
        """Configure logger.
        
        Args:
            level: Logging level
            log_file: Optional file path for log output
        """
        self._logger.setLevel(level.value)
        
        # Remove existing handlers
        if self._handler:
            self._logger.removeHandler(self._handler)
        if self._file_handler:
            self._logger.removeHandler(self._file_handler)
        
        # Console handler (stderr)
        self._handler = logging.StreamHandler(sys.stderr)
        self._handler.setLevel(level.value)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self._handler.setFormatter(formatter)
        self._logger.addHandler(self._handler)
        
        # File handler (if specified)
        if log_file:
            self._file_handler = logging.FileHandler(log_file)
            self._file_handler.setLevel(level.value)
            self._file_handler.setFormatter(formatter)
            self._logger.addHandler(self._file_handler)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message."""
        self._logger.error(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        self._logger.warning(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message."""
        self._logger.info(message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message."""
        self._logger.debug(message, *args, **kwargs)
    
    @property
    def logger(self) -> logging.Logger:
        """Get underlying logger instance."""
        return self._logger


def get_logger() -> Logger:
    """Get logger instance."""
    return Logger()

