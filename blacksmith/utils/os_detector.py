"""OS detection utilities."""

import platform
import sys


def detect_os() -> str:
    """
    Detect the current operating system.
    
    Returns:
        'linux' or 'windows'
    """
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    else:
        return "unknown"


def is_linux() -> bool:
    """Check if running on Linux."""
    return detect_os() == "linux"


def is_windows() -> bool:
    """Check if running on Windows."""
    return detect_os() == "windows"

