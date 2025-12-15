"""Scoop JSON exporter."""

import json
from typing import Dict, List, Optional

from blacksmith.export.base import BaseExporter


class ScoopExporter(BaseExporter):
    """Export packages to Scoop JSON format."""
    
    def export(self, output_path: Optional[str] = None) -> str:
        """
        Export packages to Scoop JSON format.
        
        Scoop uses a JSON array format for bucket exports.
        """
        packages = self.filter_packages_by_manager("scoop")
        
        # Extract package names
        package_names = []
        for pkg in packages:
            pkg_id = self.get_package_id(pkg, "scoop")
            if pkg_id:
                package_names.append(pkg_id)
        
        # Create JSON structure (simple array of package names)
        output = json.dumps(package_names, indent=2, ensure_ascii=False)
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)
        
        return output
    
    def get_file_extension(self) -> str:
        """Get file extension for Scoop format."""
        return ".json"

