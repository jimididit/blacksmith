"""Base exporter class for package manager formats."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseExporter(ABC):
    """Abstract base class for package manager exporters."""
    
    def __init__(self, config: Dict):
        """
        Initialize exporter with configuration.
        
        Args:
            config: Configuration dictionary from YAML file
        """
        self.config = config
        self.packages = config.get("packages", [])
    
    @abstractmethod
    def export(self, output_path: Optional[str] = None) -> str:
        """
        Export packages to native format.
        
        Args:
            output_path: Optional file path to write output to
            
        Returns:
            Exported content as string
        """
        pass
    
    @abstractmethod
    def get_file_extension(self) -> str:
        """
        Get recommended file extension for this format.
        
        Returns:
            File extension (e.g., ".json", ".xml", ".txt")
        """
        pass
    
    def get_package_id(self, package: Dict, manager_name: str) -> Optional[str]:
        """
        Get package ID for a specific manager from package config.
        
        Args:
            package: Package configuration dict
            manager_name: Name of the package manager
            
        Returns:
            Package ID or None if not found
        """
        managers = package.get("managers", {})
        return managers.get(manager_name) or managers.get(manager_name.lower())
    
    def filter_packages_by_manager(self, manager_name: str) -> List[Dict]:
        """
        Filter packages that have entries for a specific manager.
        
        Args:
            manager_name: Name of the package manager
            
        Returns:
            List of packages that have this manager
        """
        filtered = []
        for pkg in self.packages:
            pkg_id = self.get_package_id(pkg, manager_name)
            if pkg_id and pkg_id.strip():
                filtered.append(pkg)
        return filtered

