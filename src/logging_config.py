"""Logging configuration for SalaryValidator."""

import logging
import sys
from typing import Optional

from src.config import get_settings


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """
    Configure and return the application logger.

    Args:
        level: Override log level (default: from settings)

    Returns:
        Configured logger instance
    """
    settings = get_settings()
    log_level = level or settings.log_level

    # Create logger
    logger = logging.getLogger("salary_validator")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger for a specific module.

    Args:
        name: Module name for the logger

    Returns:
        Child logger instance
    """
    return logging.getLogger(f"salary_validator.{name}")


# Initialize main logger on import
logger = setup_logging()
