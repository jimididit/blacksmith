"""Chocolatey packages.config exporter."""

import xml.etree.ElementTree as ET
from typing import Dict, Optional

from blacksmith.export.base import BaseExporter


class ChocolateyExporter(BaseExporter):
    """Export packages to Chocolatey packages.config XML format."""
    
    def export(self, output_path: Optional[str] = None) -> str:
        """
        Export packages to Chocolatey packages.config format.
        
        Chocolatey uses XML format:
        <?xml version="1.0" encoding="utf-8"?>
        <packages>
          <package id="package-name" version="1.0.0" />
        </packages>
        """
        packages = self.filter_packages_by_manager("chocolatey")
        
        # Create XML root
        root = ET.Element("packages")
        
        for pkg in packages:
            pkg_id = self.get_package_id(pkg, "chocolatey")
            if pkg_id:
                # Extract version if present (format: package|version)
                package_name = pkg_id
                version = None
                
                if '|' in pkg_id:
                    parts = pkg_id.split('|', 1)
                    package_name = parts[0]
                    if len(parts) > 1:
                        version = parts[1]
                
                # Create package element
                package_elem = ET.SubElement(root, "package")
                package_elem.set("id", package_name)
                if version:
                    package_elem.set("version", version)
        
        # Convert to string
        # ET.indent is Python 3.9+, so we'll format manually for 3.8 compatibility
        try:
            ET.indent(root, space="  ")
        except AttributeError:
            # Python 3.8 doesn't have ET.indent, format manually
            pass
        output = '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode")
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)
        
        return output
    
    def get_file_extension(self) -> str:
        """Get file extension for Chocolatey format."""
        return ".config"

