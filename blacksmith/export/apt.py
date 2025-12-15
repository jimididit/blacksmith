"""Apt list exporter."""

from typing import Optional

from blacksmith.export.base import BaseExporter


class AptExporter(BaseExporter):
    """Export packages to Apt list format."""
    
    def export(self, output_path: Optional[str] = None) -> str:
        """
        Export packages to Apt list format.
        
        Apt uses a simple text format, one package per line.
        """
        packages = self.filter_packages_by_manager("apt")
        
        # Extract package names
        package_names = []
        for pkg in packages:
            pkg_id = self.get_package_id(pkg, "apt")
            if pkg_id:
                package_names.append(pkg_id)
        
        # Create output (one package per line)
        output = "\n".join(package_names)
        if package_names:
            output += "\n"  # Add trailing newline
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)
        
        return output
    
    def get_file_extension(self) -> str:
        """Get file extension for Apt format."""
        return ".txt"

