"""Pacman list exporter."""

from typing import Optional

from blacksmith.export.base import BaseExporter


class PacmanExporter(BaseExporter):
    """Export packages to Pacman list format."""
    
    def export(self, output_path: Optional[str] = None) -> str:
        """
        Export packages to Pacman list format.
        
        Pacman uses a simple text format, one package per line.
        """
        packages = self.filter_packages_by_manager("pacman")
        
        # Extract package names
        package_names = []
        for pkg in packages:
            pkg_id = self.get_package_id(pkg, "pacman")
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
        """Get file extension for Pacman format."""
        return ".txt"

