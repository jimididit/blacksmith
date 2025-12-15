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
        
        from blacksmith.utils.ui import print_error, print_warning, print_info
        
        try:
            success = True
            for package in packages:
                # First verify package exists
                verify_cmd = ["winget", "search", "--exact", "--id", package]
                verify_result = subprocess.run(
                    verify_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )
                
                if verify_result.returncode != 0 or package not in verify_result.stdout:
                    print_error(f"Package {package} not found in winget repository")
                    print_warning(f"  Try searching: winget search {package.split('.')[0] if '.' in package else package}")
                    success = False
                    continue
                
                # Try installation without --silent first (more reliable)
                # Some packages don't support --silent
                cmd = ["winget", "install", "--accept-package-agreements", "--accept-source-agreements", package]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    shell=True
                )
                
                if result.returncode != 0:
                    # Extract error message from output
                    error_msg = result.stderr.strip() or result.stdout.strip()
                    logger.error(f"Winget install failed for {package}: {error_msg}")
                    
                    # Show user-friendly error
                    if "No package found" in error_msg or "No applicable package" in error_msg:
                        print_error(f"Package {package} not found in winget repository")
                        print_warning(f"  Try: winget search {package.split('.')[0] if '.' in package else package}")
                    elif "requires administrator" in error_msg.lower() or "elevated" in error_msg.lower() or "administrator" in error_msg.lower():
                        print_error(f"Administrator privileges required for {package}")
                        print_warning("  Please run Blacksmith as Administrator")
                    elif "hash" in error_msg.lower() or "security" in error_msg.lower():
                        print_error(f"Security/hash verification failed for {package}")
                        print_warning("  You may need to update winget or allow hash override")
                    elif error_msg:
                        # Show first few lines of error
                        error_lines = [line.strip() for line in error_msg.split('\n') if line.strip()][:3]
                        if error_lines:
                            error_preview = ' | '.join(error_lines)
                            print_error(f"Failed to install {package}: {error_preview[:200]}")
                        else:
                            print_error(f"Failed to install {package} (check winget output above)")
                    else:
                        print_error(f"Failed to install {package} (exit code: {result.returncode})")
                    success = False
                else:
                    print_info(f"Successfully installed {package}")
            return success
        except subprocess.TimeoutExpired:
            logger.error("Winget install timed out")
            print_error("Winget install timed out")
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
    
    def update_package(self, package: str) -> bool:
        """Update a specific package using winget upgrade."""
        try:
            cmd = ["winget", "upgrade", "--accept-package-agreements", "--accept-source-agreements", package]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                shell=True
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"Winget upgrade failed for {package}: {error_msg}")
                from blacksmith.utils.ui import print_error
                if "No applicable update" in error_msg or "already installed" in error_msg.lower():
                    print_error(f"{package} is already up to date")
                else:
                    print_error(f"Failed to update {package}: {error_msg[:150]}")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.error("Winget upgrade timed out")
            from blacksmith.utils.ui import print_error
            print_error("Winget upgrade timed out")
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

