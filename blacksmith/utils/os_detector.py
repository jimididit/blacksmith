"""OS detection utilities."""

import platform
import sys


def detect_os() -> str:
    """
    Detect the current operating system.
    
    Returns:
        'Linux', 'Windows', 'Darwin', or 'Unknown'
    """
    system = platform.system()
    if system == "Linux":
        return "Linux"
    elif system == "Windows":
        return "Windows"
    elif system == "Darwin":
        return "Darwin"
    else:
        return "Unknown"


def is_linux() -> bool:
    """Check if running on Linux."""
    return detect_os() == "Linux"


def is_windows() -> bool:
    """Check if running on Windows."""
    return detect_os() == "Windows"

