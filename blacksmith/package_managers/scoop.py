"""Scoop package manager implementation."""

import subprocess
from typing import List, Dict

from blacksmith.package_managers.base import PackageManager
from blacksmith.utils.logger import setup_logger

logger = setup_logger(__name__)


class ScoopManager(PackageManager):
    """Scoop package manager for Windows."""
    
    def __init__(self):
        super().__init__("scoop")
    
    def is_available(self) -> bool:
        """Check if scoop is available."""
        try:
            result = subprocess.run(
                ["scoop", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def install(self, packages: List[str]) -> bool:
        """Install packages using scoop."""
        if not packages:
            return True
        
        try:
            cmd = ["scoop", "install"] + packages
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                shell=True
            )
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            logger.error(f"Scoop install failed: {e}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Scoop install timed out")
            return False
    
    def is_installed(self, package: str) -> bool:
        """Check if package is installed."""
        try:
            result = subprocess.run(
                ["scoop", "list"],
                capture_output=True,
                text=True,
                timeout=10,
                shell=True
            )
            return result.returncode == 0 and package in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for packages using Scoop."""
        try:
            result = subprocess.run(
                ["scoop", "search", query],
                capture_output=True,
                text=True,
                timeout=30,
                shell=True
            )
            if result.returncode != 0:
                return []
            
            packages = []
            for line in result.stdout.strip().split('\n')[1:limit+1]:  # Skip header
                if line.strip():
                    packages.append({
                        'name': line.strip(),
                        'description': ''
                    })
            return packages
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"Scoop search failed: {e}")
            return []

