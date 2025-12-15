"""Winget package manager implementation."""

import re
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
            # Winget v1.12.350 and earlier don't support --output json
            # Use text output and parse it
            # Use UTF-8 encoding with error handling to avoid UnicodeDecodeError
            result = subprocess.run(
                ["winget", "search", query],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace invalid characters instead of failing
                timeout=30,
                shell=True
            )
            
            if result.returncode != 0:
                # Check if it's just no results or an actual error
                stderr_text = result.stderr or ""
                stdout_text = result.stdout or ""
                if "No package found" in stderr_text or "No package found" in stdout_text:
                    return []
                logger.warning(f"Winget search failed: {stderr_text}")
                return []
            
            # Check if stdout is None or empty
            if not result.stdout:
                return []
            
            # Parse text output
            # Format is typically:
            # Name                    Id                          Version    Source
            # ----                    --                          -------    ------
            # Package Name            Publisher.PackageName       1.0.0      winget
            packages = []
            lines = result.stdout.strip().split('\n')
            
            # Find the header line (contains "Name" and "Id")
            header_idx = -1
            for i, line in enumerate(lines):
                if 'Name' in line and 'Id' in line:
                    header_idx = i
                    break
            
            if header_idx == -1:
                # No header found, try to parse anyway
                # Look for lines that look like package entries
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('-') and not line.startswith('█'):
                        # Check if it looks like a package line (has at least 2 words)
                        parts = line.split()
                        if len(parts) >= 2:
                            # First part might be name, second might be ID
                            # Try to find Publisher.Package format
                            pkg_id = None
                            for part in parts:
                                if '.' in part and len(part.split('.')) >= 2:
                                    pkg_id = part
                                    break
                            
                            if pkg_id:
                                packages.append({
                                    'name': pkg_id,
                                    'description': ' '.join(parts[1:]) if len(parts) > 1 else ''
                                })
            else:
                # Parse structured output
                # Skip header and separator line (header_idx + 1 is separator, +2 is first data)
                for line in lines[header_idx + 2:]:
                    if not line:  # Check if line is None or empty before strip()
                        continue
                    line = line.strip()
                    if not line or line.startswith('█') or line.startswith('▒') or line.startswith('-'):
                        # Skip progress bars, empty lines, and separators
                        continue
                    
                    # Parse the line - format is space-separated with variable spacing
                    # Name       Id                     Version  Match     Source
                    # cURL       cURL.cURL              8.17.0.4           winget
                    # Split on multiple spaces (2 or more) to get columns
                    parts = re.split(r'\s{2,}', line)
                    
                    if len(parts) >= 2:
                        pkg_name = parts[0].strip()  # First column is name
                        pkg_id = parts[1].strip()    # Second column is ID
                        
                        # Get description (use name if available, or version if present)
                        description = pkg_name
                        if len(parts) >= 3:
                            # Third column is usually version, can use as description
                            version = parts[2].strip()
                            if version and version != 'Unknown':
                                description = f"{pkg_name} ({version})"
                        
                        if pkg_id:
                            packages.append({
                                'name': pkg_id,
                                'description': description
                            })
                            
                            if len(packages) >= limit:
                                break
            
            return packages[:limit]
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"Winget search failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Winget search parsing failed: {e}")
            return []

