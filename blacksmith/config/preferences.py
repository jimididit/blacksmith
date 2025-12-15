"""Manager preference system for cross-platform support."""

from typing import Dict, List, Optional, Tuple

from blacksmith.package_managers.base import PackageManager
from blacksmith.utils.os_detector import detect_os


class PreferredManagerOrder:
    """Manages OS-specific package manager preferences."""
    
    # Default preferences for each OS
    DEFAULT_PREFERENCES: Dict[str, List[str]] = {
        "windows": ["winget", "chocolatey", "scoop"],
        "linux": ["apt", "pacman", "yum", "flatpak", "snap"],
        "darwin": ["brew", "snap", "flatpak"],  # macOS (for future support)
        "macos": ["brew", "snap", "flatpak"],  # Alias for darwin
    }
    
    def __init__(self, custom_preferences: Optional[Dict[str, List[str]]] = None):
        """
        Initialize preference system.
        
        Args:
            custom_preferences: Optional custom preferences to override defaults.
                               Format: {"windows": ["winget", "chocolatey"], ...}
        """
        self.preferences = self.DEFAULT_PREFERENCES.copy()
        if custom_preferences:
            # Normalize OS names to lowercase
            for os_name, managers in custom_preferences.items():
                self.preferences[os_name.lower()] = [
                    mgr.lower() for mgr in managers
                ]
    
    def get_preferred_order(self, os_name: Optional[str] = None) -> List[str]:
        """
        Get preferred manager order for an OS.
        
        Args:
            os_name: OS name (windows, linux, darwin). If None, detects current OS.
            
        Returns:
            List of manager names in preferred order
        """
        if os_name is None:
            os_name = detect_os().lower()
        else:
            os_name = os_name.lower()
        
        # Handle macOS aliases
        if os_name == "darwin":
            os_name = "macos"
        
        return self.preferences.get(os_name, [])
    
    def get_managers_in_order(
        self,
        available_managers: List[PackageManager],
        os_name: Optional[str] = None,
        managers_supported: Optional[List[str]] = None
    ) -> List[PackageManager]:
        """
        Get available managers sorted by preference order.
        
        Args:
            available_managers: List of available PackageManager instances
            os_name: OS name (optional, auto-detects if None)
            managers_supported: Optional list of manager names to filter by
            
        Returns:
            List of PackageManager instances in preferred order
        """
        preferred_order = self.get_preferred_order(os_name)
        
        # Create a map of manager names to instances
        manager_map = {mgr.name.lower(): mgr for mgr in available_managers}
        
        # Filter by managers_supported if provided
        if managers_supported:
            managers_supported_lower = [m.lower() for m in managers_supported]
            manager_map = {
                name: mgr for name, mgr in manager_map.items()
                if name in managers_supported_lower
            }
            # Also filter preferred_order to only include supported managers
            preferred_order = [m for m in preferred_order if m.lower() in managers_supported_lower]
        
        # Sort available managers by preference order
        ordered = []
        seen = set()
        
        # First, add managers in preferred order
        for mgr_name in preferred_order:
            mgr_name_lower = mgr_name.lower()
            if mgr_name_lower in manager_map:
                ordered.append(manager_map[mgr_name_lower])
                seen.add(mgr_name_lower)
        
        # Then, add any remaining managers not in preferred order
        for mgr_name, mgr in manager_map.items():
            if mgr_name not in seen:
                ordered.append(mgr)
        
        return ordered
    
    def find_best_manager(
        self,
        package_managers: Dict[str, str],
        available_managers: List[PackageManager],
        os_name: Optional[str] = None,
        managers_supported: Optional[List[str]] = None
    ) -> Optional[Tuple[PackageManager, str]]:
        """
        Find the best available manager for a package based on preferences.
        
        Args:
            package_managers: Dict mapping manager names to package IDs
            available_managers: List of available PackageManager instances
            os_name: OS name (optional, auto-detects if None)
            managers_supported: Optional list of manager names to filter by
            
        Returns:
            Tuple of (PackageManager, package_id) or None if not found
        """
        ordered_managers = self.get_managers_in_order(
            available_managers,
            os_name=os_name,
            managers_supported=managers_supported
        )
        
        # Create a map of manager names to package IDs (normalized to lowercase)
        package_managers_lower = {
            mgr_name.lower(): pkg_id
            for mgr_name, pkg_id in package_managers.items()
        }
        
        # Try each manager in preferred order
        for mgr in ordered_managers:
            mgr_name_lower = mgr.name.lower()
            if mgr_name_lower in package_managers_lower:
                pkg_id = package_managers_lower[mgr_name_lower]
                # Skip empty package IDs
                if pkg_id and pkg_id.strip():
                    return (mgr, pkg_id)
        
        return None

