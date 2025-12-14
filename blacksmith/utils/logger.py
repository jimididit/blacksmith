"""Logging utilities."""

import logging
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with Rich formatting.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Add Rich handler
    console = Console()
    handler = RichHandler(console=console, rich_tracebacks=True)
    handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    logger.addHandler(handler)
    
    return logger

