"""YAML configuration parser."""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from blacksmith.utils.logger import setup_logger

logger = setup_logger(__name__)


def load_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load and parse a YAML file.
    
    Args:
        file_path: Path to YAML file
        
    Returns:
        Parsed YAML data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data is None:
                return {}
            return data
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML file: {e}")
        raise


def parse_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and validate basic structure of config data.
    
    Args:
        config_data: Raw config dictionary
        
    Returns:
        Parsed config dictionary with defaults applied
    """
    # Normalize target_os to lowercase list
    target_os = config_data.get("target_os")
    if target_os is None:
        # Default: current OS (will be set at runtime if needed)
        target_os_list = None
    elif isinstance(target_os, str):
        target_os_list = [target_os.lower()]
    else:
        target_os_list = [os_name.lower() for os_name in target_os]
    
    # Normalize preferred_managers keys to lowercase
    preferred_managers = config_data.get("preferred_managers")
    if preferred_managers:
        preferred_managers = {
            os_name.lower(): [mgr.lower() for mgr in managers]
            for os_name, managers in preferred_managers.items()
        }
    
    # Normalize managers_supported to lowercase list
    managers_supported = config_data.get("managers_supported")
    if managers_supported:
        managers_supported = [mgr.lower() for mgr in managers_supported]
    
    parsed = {
        "name": config_data.get("name", "Unnamed Set"),
        "description": config_data.get("description", ""),
        "packages": config_data.get("packages", []),
        "target_os": target_os_list,
        "preferred_managers": preferred_managers,
        "managers_supported": managers_supported,
    }
    
    return parsed

