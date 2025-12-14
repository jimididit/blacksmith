"""YUM/DNF package manager implementation."""

import subprocess
from typing import List, Dict

from blacksmith.package_managers.base import PackageManager
from blacksmith.utils.logger import setup_logger

logger = setup_logger(__name__)


class YumManager(PackageManager):
    """YUM/DNF package manager for RHEL/Fedora."""
    
    def __init__(self):
        super().__init__("yum")
        # Prefer dnf over yum if available
        if self._check_dnf():
            self.command = "dnf"
        elif self._check_yum():
            self.command = "yum"
        else:
            self.command = "yum"  # Default fallback
    
    def _check_dnf(self) -> bool:
        """Check if dnf is available."""
        try:
            result = subprocess.run(
                ["dnf", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def is_available(self) -> bool:
        """Check if yum or dnf is available."""
        return self._check_dnf() or self._check_yum()
    
    def _check_yum(self) -> bool:
        """Check if yum is available."""
        try:
            result = subprocess.run(
                ["yum", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def install(self, packages: List[str]) -> bool:
        """Install packages using yum or dnf."""
        if not packages:
            return True
        
        try:
            # Don't capture output so sudo password prompts are visible
            cmd = ["sudo", self.command, "install", "-y"] + packages
            result = subprocess.run(
                cmd,
                timeout=600
            )
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            logger.error(f"{self.command} install failed: {e}")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"{self.command} install timed out")
            return False
    
    def is_installed(self, package: str) -> bool:
        """Check if package is installed."""
        try:
            result = subprocess.run(
                ["rpm", "-q", package],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for packages using yum or dnf."""
        try:
            result = subprocess.run(
                [self.command, "search", query],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                return []
            
            packages = []
            for line in result.stdout.strip().split('\n')[:limit]:
                if ':' in line and not line.startswith('='):
                    name = line.split(':')[0].strip()
                    desc = ':'.join(line.split(':')[1:]).strip() if ':' in line else ''
                    packages.append({
                        'name': name,
                        'description': desc
                    })
            return packages
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"{self.command} search failed: {e}")
            return []

