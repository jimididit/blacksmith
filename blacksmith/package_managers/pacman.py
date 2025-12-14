"""Pacman package manager implementation."""

import subprocess
from typing import List, Dict

from blacksmith.package_managers.base import PackageManager
from blacksmith.utils.logger import setup_logger

logger = setup_logger(__name__)


class PacmanManager(PackageManager):
    """Pacman package manager for Arch Linux."""
    
    def __init__(self):
        super().__init__("pacman")
    
    def is_available(self) -> bool:
        """Check if pacman is available."""
        try:
            result = subprocess.run(
                ["pacman", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def install(self, packages: List[str]) -> bool:
        """Install packages using pacman."""
        if not packages:
            return True
        
        try:
            # Don't capture output so sudo password prompts are visible
            cmd = ["sudo", "pacman", "-S", "--noconfirm"] + packages
            result = subprocess.run(
                cmd,
                timeout=600
            )
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            logger.error(f"Pacman install failed: {e}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Pacman install timed out")
            return False
    
    def is_installed(self, package: str) -> bool:
        """Check if package is installed."""
        try:
            result = subprocess.run(
                ["pacman", "-Q", package],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for packages using pacman."""
        try:
            result = subprocess.run(
                ["pacman", "-Ss", query],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                return []
            
            packages = []
            lines = result.stdout.strip().split('\n')
            for i in range(0, min(len(lines), limit * 2), 2):
                if i < len(lines):
                    name_line = lines[i]
                    desc_line = lines[i + 1] if i + 1 < len(lines) else ''
                    
                    # Format: "repo/name version"
                    if '/' in name_line:
                        name = name_line.split()[0].split('/')[1]
                        desc = desc_line.strip() if desc_line.startswith('    ') else ''
                        packages.append({
                            'name': name,
                            'description': desc
                        })
            
            return packages[:limit]
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"Pacman search failed: {e}")
            return []

