"""Base class for package managers."""

from abc import ABC, abstractmethod
from typing import List


class PackageManager(ABC):
    """Abstract base class for package managers."""
    
    def __init__(self, name: str):
        """
        Initialize package manager.
        
        Args:
            name: Name of the package manager
        """
        self.name = name
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this package manager is available on the system.
        
        Returns:
            True if available, False otherwise
        """
        pass
    
    @abstractmethod
    def install(self, packages: List[str]) -> bool:
        """
        Install packages.
        
        Args:
            packages: List of package names to install
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_installed(self, package: str) -> bool:
        """
        Check if a package is installed.
        
        Args:
            package: Package name to check
            
        Returns:
            True if installed, False otherwise
        """
        pass
    
    def update(self) -> bool:
        """
        Update package manager database.
        
        Returns:
            True if successful, False otherwise
        """
        # Default implementation does nothing
        return True
    
    def update_package(self, package: str) -> bool:
        """
        Update a specific package (if supported by the package manager).
        
        Args:
            package: Package name to update
            
        Returns:
            True if successful, False otherwise
        """
        # Default implementation: just reinstall (works for most managers)
        return self.install([package])
    
    def search(self, query: str, limit: int = 10) -> List[dict]:
        """
        Search for packages in this package manager.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of dicts with 'name' and optionally 'description' keys
        """
        # Default implementation returns empty list
        # Subclasses should override this
        return []
    
    def validate_package(self, package_name: str) -> bool:
        """
        Validate if a package name exists in this package manager.
        
        Args:
            package_name: Package name to validate
            
        Returns:
            True if package exists, False otherwise
        """
        # Default implementation: try to search for exact match
        results = self.search(package_name, limit=1)
        return any(pkg.get('name', '') == package_name for pkg in results)

