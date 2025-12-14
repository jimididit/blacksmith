"""Winget package manager implementation."""

import subprocess
import json
from typing import List, Dict

from blacksmith.package_managers.base import PackageManager
from blacksmith.utils.logger import setup_logger

logger = setup_logger(__name__)


class WingetManager(PackageManager):
    """Winget package manager for Windows."""
    
    def __init__(self):
        super().__init__("winget")
    
    def is_available(self) -> bool:
        """Check if winget is available."""
        try:
            result = subprocess.run(
                ["winget", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def install(self, packages: List[str]) -> bool:
        """Install packages using winget."""
        if not packages:
            return True
        
        try:
            success = True
            for package in packages:
                cmd = ["winget", "install", "--accept-package-agreements", "--accept-source-agreements", package]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    shell=True
                )
                if result.returncode != 0:
                    logger.error(f"Winget install failed for {package}: {result.stderr}")
                    success = False
            return success
        except subprocess.TimeoutExpired:
            logger.error("Winget install timed out")
            return False
    
    def is_installed(self, package: str) -> bool:
        """Check if package is installed."""
        try:
            # Winget package IDs are in format Publisher.Package
            # We need to check if any installed package matches
            result = subprocess.run(
                ["winget", "list", package],
                capture_output=True,
                text=True,
                timeout=10,
                shell=True
            )
            return result.returncode == 0 and package in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for packages using winget."""
        try:
            result = subprocess.run(
                ["winget", "search", query, "--exact", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                shell=True
            )
            if result.returncode != 0:
                # Try without --exact for broader search
                result = subprocess.run(
                    ["winget", "search", query, "--output", "json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=True
                )
            
            if result.returncode != 0:
                return []
            
            try:
                data = json.loads(result.stdout)
                packages = []
                for pkg in data.get('Sources', [{}])[0].get('Packages', [])[:limit]:
                    packages.append({
                        'name': pkg.get('PackageIdentifier', ''),
                        'description': pkg.get('Description', '')
                    })
                return packages
            except (json.JSONDecodeError, KeyError, IndexError):
                # Fallback to text parsing
                packages = []
                for line in result.stdout.strip().split('\n')[2:limit+2]:  # Skip header
                    parts = line.split()
                    if parts:
                        packages.append({
                            'name': parts[0] if parts else '',
                            'description': ' '.join(parts[1:]) if len(parts) > 1 else ''
                        })
                return packages
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"Winget search failed: {e}")
            return []

