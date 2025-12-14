"""Configuration validation."""

from typing import Any, Dict, List, Optional, Tuple

from blacksmith.utils.ui import print_error


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

