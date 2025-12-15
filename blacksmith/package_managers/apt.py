"""APT package manager implementation."""

import subprocess
from typing import List, Dict

from blacksmith.package_managers.base import PackageManager
from blacksmith.utils.logger import setup_logger

logger = setup_logger(__name__)


class AptManager(PackageManager):
    """APT package manager for Debian/Ubuntu."""
    
    def __init__(self):
        super().__init__("apt")
    
    def is_available(self) -> bool:
        """Check if apt is available."""
        try:
            result = subprocess.run(
                ["apt", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def install(self, packages: List[str]) -> bool:
        """Install packages using apt."""
        if not packages:
            return True
        
        try:
            # Update package list first
            # Don't capture output so sudo password prompts are visible
            result = subprocess.run(
                ["sudo", "apt", "update"],
                check=False,
                timeout=300
            )
            if result.returncode != 0:
                logger.error("APT update failed")
                return False
            
            # Install packages
            # Don't capture output so sudo password prompts are visible
            cmd = ["sudo", "apt", "install", "-y"] + packages
            result = subprocess.run(
                cmd,
                timeout=600
            )
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            logger.error(f"APT install failed: {e}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("APT install timed out")
            return False
    
    def is_installed(self, package: str) -> bool:
        """Check if package is installed."""
        try:
            result = subprocess.run(
                ["dpkg", "-l", package],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and package in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def update_package(self, package: str) -> bool:
        """Update a specific package using apt install --only-upgrade."""
        try:
            # Update package list first
            result = subprocess.run(
                ["sudo", "apt", "update"],
                check=False,
                timeout=300
            )
            if result.returncode != 0:
                logger.error("APT update failed")
                return False
            
            # Upgrade the specific package
            cmd = ["sudo", "apt", "install", "--only-upgrade", "-y", package]
            result = subprocess.run(
                cmd,
                timeout=600
            )
            if result.returncode != 0:
                logger.error(f"APT upgrade failed for {package}")
                from blacksmith.utils.ui import print_error
                print_error(f"Failed to update {package}")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.error("APT upgrade timed out")
            from blacksmith.utils.ui import print_error
            print_error("APT upgrade timed out")
            return False
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for packages using apt-cache."""
        try:
            result = subprocess.run(
                ["apt-cache", "search", query],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                return []
            
            packages = []
            for line in result.stdout.strip().split('\n')[:limit]:
                if ' - ' in line:
                    name, desc = line.split(' - ', 1)
                    packages.append({
                        'name': name.strip(),
                        'description': desc.strip()
                    })
                elif line.strip():
                    packages.append({
                        'name': line.strip(),
                        'description': ''
                    })
            
            return packages
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"APT search failed: {e}")
            return []

