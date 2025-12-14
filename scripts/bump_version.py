#!/usr/bin/env python3
"""
Helper script to bump the version number in both pyproject.toml and blacksmith/__init__.py

Usage:
    python scripts/bump_version.py 0.1.1
    python scripts/bump_version.py --patch    # 0.1.0 -> 0.1.1
    python scripts/bump_version.py --minor    # 0.1.0 -> 0.2.0
    python scripts/bump_version.py --major    # 0.1.0 -> 1.0.0
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"
INIT_PY = PROJECT_ROOT / "blacksmith" / "__init__.py"


def get_current_version():
    """Get current version from pyproject.toml."""
    content = PYPROJECT_TOML.read_text()
    match = re.search(r'version = "([^"]+)"', content)
    if match:
        return match.group(1)
    raise ValueError("Could not find version in pyproject.toml")


def bump_version(current_version, bump_type=None):
    """Bump version based on type or return provided version."""
    if bump_type is None:
        # Assume version was provided directly
        return current_version
    
    parts = list(map(int, current_version.split('.')))
    
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {current_version}")
    
    if bump_type == 'patch':
        parts[2] += 1
    elif bump_type == 'minor':
        parts[1] += 1
        parts[2] = 0
    elif bump_type == 'major':
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")
    
    return '.'.join(map(str, parts))


def update_version(new_version):
    """Update version in both files."""
    # Update pyproject.toml
    content = PYPROJECT_TOML.read_text()
    content = re.sub(r'version = "[^"]+"', f'version = "{new_version}"', content)
    PYPROJECT_TOML.write_text(content)
    print(f"✓ Updated {PYPROJECT_TOML}")
    
    # Update __init__.py
    content = INIT_PY.read_text()
    content = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{new_version}"', content)
    INIT_PY.write_text(content)
    print(f"✓ Updated {INIT_PY}")
    
    print(f"\n✓ Version bumped to {new_version}")
    print("\nNext steps:")
    print(f"  1. git add pyproject.toml blacksmith/__init__.py")
    print(f"  2. git commit -m 'Bump version to {new_version}'")
    print(f"  3. git tag -a v{new_version} -m 'Release version {new_version}'")
    print(f"  4. git push origin main --tags")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/bump_version.py <version>")
        print("  python scripts/bump_version.py --patch")
        print("  python scripts/bump_version.py --minor")
        print("  python scripts/bump_version.py --major")
        sys.exit(1)
    
    current_version = get_current_version()
    print(f"Current version: {current_version}")
    
    arg = sys.argv[1]
    
    if arg.startswith('--'):
        bump_type = arg[2:]  # Remove '--'
        new_version = bump_version(current_version, bump_type)
    else:
        # Assume it's a version string
        new_version = arg
    
    # Validate version format
    if not re.match(r'^\d+\.\d+\.\d+', new_version):
        print(f"Error: Invalid version format: {new_version}")
        print("Version must be in format: MAJOR.MINOR.PATCH (e.g., 0.1.1)")
        sys.exit(1)
    
    update_version(new_version)


if __name__ == '__main__':
    main()

