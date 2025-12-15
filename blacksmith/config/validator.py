"""Configuration validation."""

from typing import Any, Dict, List, Optional, Tuple

from blacksmith.utils.ui import print_error

# Valid OS values
VALID_OS = ["windows", "linux", "darwin", "macos"]

# Valid package manager names
VALID_MANAGERS = [
    "apt", "pacman", "yum", "dnf",
    "winget", "chocolatey", "scoop",
    "snap", "flatpak"
]


def validate_config(config_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate configuration structure.
    
    Args:
        config_data: Configuration dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    if "packages" not in config_data:
        return False, "Missing required field: 'packages'"
    
    if not isinstance(config_data["packages"], list):
        return False, "Field 'packages' must be a list"
    
    # Validate optional target_os field (if present)
    if "target_os" in config_data and config_data["target_os"] is not None:
        target_os = config_data["target_os"]
        if isinstance(target_os, str):
            if target_os.lower() not in VALID_OS:
                return False, f"Invalid target_os: '{target_os}'. Must be one of: {', '.join(VALID_OS)}"
        elif isinstance(target_os, list):
            for os_name in target_os:
                if not isinstance(os_name, str) or os_name.lower() not in VALID_OS:
                    return False, f"Invalid OS in target_os list: '{os_name}'. Must be one of: {', '.join(VALID_OS)}"
        else:
            return False, "Field 'target_os' must be a string or list of strings"
    
    # Validate optional preferred_managers field (if present)
    if "preferred_managers" in config_data and config_data["preferred_managers"] is not None:
        preferred = config_data["preferred_managers"]
        if not isinstance(preferred, dict):
            return False, "Field 'preferred_managers' must be a dictionary"
        
        for os_name, managers in preferred.items():
            if os_name.lower() not in VALID_OS:
                return False, f"Invalid OS in preferred_managers: '{os_name}'"
            if not isinstance(managers, list):
                return False, f"preferred_managers['{os_name}'] must be a list"
            for mgr in managers:
                if not isinstance(mgr, str) or mgr.lower() not in VALID_MANAGERS:
                    return False, f"Invalid manager '{mgr}' in preferred_managers['{os_name}']. Must be one of: {', '.join(VALID_MANAGERS)}"
    
    # Validate optional managers_supported field (if present)
    if "managers_supported" in config_data and config_data["managers_supported"] is not None:
        managers_supported = config_data["managers_supported"]
        if not isinstance(managers_supported, list):
            return False, "Field 'managers_supported' must be a list"
        for mgr in managers_supported:
            if not isinstance(mgr, str) or mgr.lower() not in VALID_MANAGERS:
                return False, f"Invalid manager '{mgr}' in managers_supported. Must be one of: {', '.join(VALID_MANAGERS)}"
    
    # Validate each package entry
    for i, package in enumerate(config_data["packages"]):
        if not isinstance(package, dict):
            return False, f"Package at index {i} must be a dictionary"
        
        if "name" not in package:
            return False, f"Package at index {i} missing required field: 'name'"
        
        if "managers" not in package:
            return False, f"Package '{package.get('name', 'unknown')}' missing required field: 'managers'"
        
        if not isinstance(package["managers"], dict):
            return False, f"Package '{package.get('name', 'unknown')}' field 'managers' must be a dictionary"
        
        # Validate manager names in package managers dict
        for mgr_name, pkg_id in package["managers"].items():
            if mgr_name.lower() not in VALID_MANAGERS:
                return False, f"Package '{package.get('name', 'unknown')}' has invalid manager '{mgr_name}'. Must be one of: {', '.join(VALID_MANAGERS)}"
            if not isinstance(pkg_id, str) or not pkg_id.strip():
                return False, f"Package '{package.get('name', 'unknown')}' has empty or invalid package ID for manager '{mgr_name}'"
    
    return True, None


def validate_and_report(config_data: Dict[str, Any]) -> bool:
    """
    Validate configuration and print error if invalid.
    
    Args:
        config_data: Configuration dictionary
        
    Returns:
        True if valid, False otherwise
    """
    is_valid, error = validate_config(config_data)
    
    if not is_valid and error:
        print_error(f"Config validation failed: {error}")
    
    return is_valid

