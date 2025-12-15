"""Winget JSON exporter."""

import json
from typing import Dict, List, Optional

from blacksmith.export.base import BaseExporter


class WingetExporter(BaseExporter):
    """Export packages to Winget JSON format."""
    
    def export(self, output_path: Optional[str] = None) -> str:
        """
        Export packages to Winget JSON format.
        
        Winget export format is a JSON array of package identifiers.
        """
        packages = self.filter_packages_by_manager("winget")
        
        # Extract package IDs
        package_ids = []
        for pkg in packages:
            pkg_id = self.get_package_id(pkg, "winget")
            if pkg_id:
                package_ids.append(pkg_id)
        
        # Create JSON structure
        output = json.dumps(package_ids, indent=2, ensure_ascii=False)
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)
        
        return output
    
    def get_file_extension(self) -> str:
        """Get file extension for Winget format."""
        return ".json"

