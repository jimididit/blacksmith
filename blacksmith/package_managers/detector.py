"""Package manager detection."""

import shutil
import subprocess
from typing import List, Optional

from blacksmith.package_managers.base import PackageManager
from blacksmith.package_managers.apt import AptManager
from blacksmith.package_managers.pacman import PacmanManager
from blacksmith.package_managers.yum import YumManager
from blacksmith.package_managers.winget import WingetManager
from blacksmith.package_managers.chocolatey import ChocolateyManager
from blacksmith.package_managers.scoop import ScoopManager
from blacksmith.package_managers.snap import SnapManager
from blacksmith.package_managers.flatpak import FlatpakManager
from blacksmith.utils.os_detector import is_linux, is_windows
from blacksmith.utils.logger import setup_logger

logger = setup_logger(__name__)


def check_command(command: str) -> bool:
    """
    Check if a command is available.
    
    Args:
        command: Command name
        
    Returns:
        True if command exists, False otherwise
    """
    return shutil.which(command) is not None


def detect_available_managers() -> List[PackageManager]:
    """
    Detect all available package managers on the system.
    
    Returns:
        List of available PackageManager instances
    """
    available = []
    
    if is_linux():
        # Linux package managers
        if check_command("apt"):
            available.append(AptManager())
        if check_command("pacman"):
            available.append(PacmanManager())
        if check_command("yum") or check_command("dnf"):
            available.append(YumManager())
        if check_command("snap"):
            available.append(SnapManager())
        if check_command("flatpak"):
            available.append(FlatpakManager())
    elif is_windows():
        # Windows package managers
        if check_command("winget"):
            available.append(WingetManager())
        if check_command("choco"):
            available.append(ChocolateyManager())
        if check_command("scoop"):
            available.append(ScoopManager())
    
    return available


def find_manager_for_package(package_config: dict, available_managers: List[PackageManager]) -> Optional[tuple[PackageManager, str]]:
    """
    Find the best package manager and package name for a given package config.
    
    Args:
        package_config: Package configuration with managers dict
        available_managers: List of available package managers
        
    Returns:
        Tuple of (PackageManager, package_name) or None if not found
    """
    managers_dict = package_config.get("managers", {})
    available_names = {mgr.name: mgr for mgr in available_managers}
    
    # Try each manager in order of preference
    for manager_name, package_name in managers_dict.items():
        if manager_name in available_names:
            return (available_names[manager_name], package_name)
    
    return None

