"""Load pre-made and custom sets."""

from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from blacksmith.config.parser import load_yaml, parse_config
from blacksmith.config.validator import validate_config
from blacksmith.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_sets_directory() -> Path:
    """
    Get the directory containing pre-made sets.
    
    Returns:
        Path to sets directory
    """
    # Get the package directory
    package_dir = Path(__file__).parent.parent
    sets_dir = package_dir / "sets"
    return sets_dir


def load_set(set_name: str) -> Optional[Dict[str, Any]]:
    """
    Load a pre-made set by name.
    
    Args:
        set_name: Name of the set (without .yaml extension)
        
    Returns:
        Parsed config dictionary or None if not found
    """
    sets_dir = get_sets_directory()
    set_file = sets_dir / f"{set_name}.yaml"
    
    if not set_file.exists():
        logger.warning(f"Set file not found: {set_file}")
        return None
    
    try:
        data = load_yaml(set_file)
        parsed = parse_config(data)
        
        # Validate
        is_valid, error = validate_config(parsed)
        if not is_valid:
            logger.error(f"Invalid set configuration: {error}")
            return None
        
        return parsed
    except Exception as e:
        logger.error(f"Failed to load set '{set_name}': {e}")
        return None


def list_available_sets() -> List[str]:
    """
    List all available pre-made sets.
    
    Returns:
        List of set names (without .yaml extension)
    """
    sets_dir = get_sets_directory()
    
    if not sets_dir.exists():
        logger.warning(f"Sets directory not found: {sets_dir}")
        return []
    
    sets = []
    for file in sets_dir.glob("*.yaml"):
        sets.append(file.stem)
    
    return sorted(sets)


def load_custom_config(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Load a custom configuration file.
    
    Args:
        file_path: Path to config file
        
    Returns:
        Parsed config dictionary or None if invalid
    """
    try:
        data = load_yaml(file_path)
        parsed = parse_config(data)
        
        # Validate
        is_valid, error = validate_config(parsed)
        if not is_valid:
            logger.error(f"Invalid configuration: {error}")
            return None
        
        return parsed
    except Exception as e:
        logger.error(f"Failed to load custom config: {e}")
        return None

