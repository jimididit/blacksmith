"""YUM/DNF package manager implementation."""

import subprocess
from typing import List, Dict

from blacksmith.package_managers.base import PackageManager
from blacksmith.utils.logger import setup_logger
from blacksmith.utils.package_ref import parse_package_ref

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
        
        # Parse package references and build install args
        install_args = []
        for pkg in packages:
            name, version = parse_package_ref(pkg)
            if version:
                install_args.append(f"{name}-{version}")
            else:
                install_args.append(name)
        
        try:
            # Don't capture output so sudo password prompts are visible
            cmd = ["sudo", self.command, "install", "-y"] + install_args
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
            # Strip pin if present
            name, _ = parse_package_ref(package)
            result = subprocess.run(
                ["rpm", "-q", name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def supports_version_pins(self) -> bool:
        """True if this manager can honor name|version install pins."""
        return True
    
    def get_installed_version(self, package: str) -> str:
        """Return installed version string, or None if missing/unknown."""
        try:
            result = subprocess.run(
                ["rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", package],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
    
    def update_package(self, package: str) -> bool:
        """Update a specific package using yum/dnf upgrade."""
        try:
            # Use 'upgrade' for dnf, 'update' for yum
            upgrade_cmd = "upgrade" if self.command == "dnf" else "update"
            cmd = ["sudo", self.command, upgrade_cmd, "-y", package]
            result = subprocess.run(
                cmd,
                timeout=600
            )
            if result.returncode != 0:
                logger.error(f"{self.command} upgrade failed for {package}")
                from blacksmith.utils.ui import print_error
                print_error(f"Failed to update {package}")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"{self.command} upgrade timed out")
            from blacksmith.utils.ui import print_error
            print_error(f"{self.command} upgrade timed out")
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

