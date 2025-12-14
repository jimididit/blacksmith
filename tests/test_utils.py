"""Tests for utility functions."""

import pytest
import platform

from blacksmith.utils.os_detector import detect_os, is_linux, is_windows


def test_detect_os():
    """Test OS detection."""
    os_name = detect_os()
    assert os_name in ['Linux', 'Windows', 'Darwin', 'Unknown']


def test_is_linux():
    """Test Linux detection."""
    result = is_linux()
    assert isinstance(result, bool)
    if platform.system() == 'Linux':
        assert result is True


def test_is_windows():
    """Test Windows detection."""
    result = is_windows()
    assert isinstance(result, bool)
    if platform.system() == 'Windows':
        assert result is True

