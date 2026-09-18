"""Homebrew package manager implementation (macOS)."""

import subprocess
from typing import Dict, List

from blacksmith.package_managers.base import PackageManager
from blacksmith.utils.logger import setup_logger
from blacksmith.utils.package_ref import parse_package_ref

logger = setup_logger(__name__)


class BrewManager(PackageManager):
    """Homebrew package manager for macOS (formulas and casks)."""

    def __init__(self):
        super().__init__("brew")

    def is_available(self) -> bool:
        """Check if brew is available."""
        try:
            result = subprocess.run(
                ["brew", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def install(self, packages: List[str]) -> bool:
        """Install packages using brew (formula or cask resolved by Homebrew)."""
        if not packages:
            return True

        # Parse package references and build install args
        install_args = []
        for pkg in packages:
            name, version = parse_package_ref(pkg)
            if version:
                install_args.append(f"{name}@{version}")
            else:
                install_args.append(name)

        try:
            cmd = ["brew", "install"] + install_args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0:
                logger.error(f"Brew install failed: {result.stderr}")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.error("Brew install timed out")
            return False

    def is_installed(self, package: str) -> bool:
        """Check if a formula or cask is installed."""
        try:
            # Strip pin if present
            name, _ = parse_package_ref(package)
            result = subprocess.run(
                ["brew", "list", "--versions", name],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0 and name in result.stdout:
                return True
            # Casks may need an explicit list
            result = subprocess.run(
                ["brew", "list", "--cask", "--versions", name],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.returncode == 0 and name in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def supports_version_pins(self) -> bool:
        """True if this manager can honor name|version install pins."""
        return True
    
    def get_installed_version(self, package: str) -> str:
        """Return installed version string, or None if missing/unknown."""
        try:
            # Try formula first
            result = subprocess.run(
                ["brew", "list", "--versions", package],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                # Parse line "name ver [ver...]" -> first version token after name
                for line in result.stdout.strip().split('\n'):
                    if line.strip() and package in line:
                        parts = line.split()
                        if len(parts) >= 2 and parts[0] == package:
                            return parts[1]  # First version after name
            
            # Try cask if formula failed
            result = subprocess.run(
                ["brew", "list", "--cask", "--versions", package],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                # Parse line "name ver [ver...]" -> first version token after name
                for line in result.stdout.strip().split('\n'):
                    if line.strip() and package in line:
                        parts = line.split()
                        if len(parts) >= 2 and parts[0] == package:
                            return parts[1]  # First version after name
            
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def update(self) -> bool:
        """Update Homebrew formulae/cask metadata."""
        try:
            result = subprocess.run(
                ["brew", "update"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def update_package(self, package: str) -> bool:
        """Upgrade a specific formula or cask."""
        try:
            cmd = ["brew", "upgrade", package]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"Brew upgrade failed for {package}: {error_msg}")
                from blacksmith.utils.ui import print_error
                lowered = error_msg.lower()
                if "already installed" in lowered or "up-to-date" in lowered or "up to date" in lowered:
                    print_error(f"{package} is already up to date")
                else:
                    print_error(f"Failed to upgrade {package}: {error_msg[:150]}")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.error("Brew upgrade timed out")
            from blacksmith.utils.ui import print_error
            print_error("Brew upgrade timed out")
            return False

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search Homebrew formulae and casks."""
        try:
            result = subprocess.run(
                ["brew", "search", query],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return []

            packages: List[Dict] = []
            for line in result.stdout.splitlines():
                name = line.strip()
                if not name or name.startswith("==>"):
                    continue
                packages.append({"name": name, "description": ""})
                if len(packages) >= limit:
                    break
            return packages
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"Brew search failed: {e}")
            return []
