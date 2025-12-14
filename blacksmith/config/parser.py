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
        Parsed config dictionary
    """
    parsed = {
        "name": config_data.get("name", "Unnamed Set"),
        "description": config_data.get("description", ""),
        "packages": config_data.get("packages", []),
    }
    
    return parsed

