"""UI helpers using Rich for beautiful terminal output."""

import sys
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# Custom color scheme
# Primary: #3A254C (dark purple)
# Accent: #44FFD1 (cyan/turquoise)
# Shades: lighter/darker variations of primary

custom_theme = Theme({
    "primary": "#3A254C",
    "primary.light": "#5A3A6C",
    "primary.dark": "#2A1A3C",
    "accent": "#44FFD1",
    "accent.dark": "#33CCAA",
    "success": "#44FFD1",  # Use accent for success
    "error": "#FF6B6B",    # Slight red tint for errors
    "warning": "#FFD93D",  # Yellow for warnings
    "info": "#44FFD1",     # Use accent for info
})

# Configure console with encoding error handling for Windows
# Use ASCII-safe symbols on Windows to avoid encoding issues
if sys.platform == "win32":
    # Windows console may not support Unicode characters
    console = Console(theme=custom_theme, force_terminal=True, legacy_windows=True)
    # ASCII-safe symbols for Windows
    SYMBOL_SUCCESS = "[OK]"
    SYMBOL_ERROR = "[X]"
    SYMBOL_WARNING = "[!]"
    SYMBOL_INFO = "[i]"
else:
    console = Console(theme=custom_theme)
    # Unicode symbols for Unix-like systems
    SYMBOL_SUCCESS = "✓"
    SYMBOL_ERROR = "✗"
    SYMBOL_WARNING = "⚠"
    SYMBOL_INFO = "ℹ"


def print_panel(title: str, content: str, style: str = "primary") -> None:
    """
    Print a formatted panel.
    
    Args:
        title: Panel title
        content: Panel content
        style: Panel style (defaults to primary color)
    """
    # Map style names to hex colors for convenience
    style_map = {
        "primary": "#3A254C",
        "accent": "#44FFD1",
    }
    border_style = style_map.get(style, style)
    console.print(Panel(content, title=title, border_style=border_style))


def print_table(title: str, headers: List[str], rows: List[List[str]], show_header: bool = True) -> None:
    """
    Print a formatted table.
    
    Args:
        title: Table title
        headers: Column headers
        rows: Table rows
        show_header: Whether to show header row
    """
    # Use hex color directly since Rich themes need proper style references
    table = Table(title=title, show_header=show_header, header_style="bold #44FFD1")
    
    for header in headers:
        table.add_column(header, style="#5A3A6C")
    
    for row in rows:
        table.add_row(*row)
    
    console.print(table)


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold #44FFD1]{SYMBOL_SUCCESS}[/bold #44FFD1] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold #FF6B6B]{SYMBOL_ERROR}[/bold #FF6B6B] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold #FFD93D]{SYMBOL_WARNING}[/bold #FFD93D] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[bold #44FFD1]{SYMBOL_INFO}[/bold #44FFD1] {message}")


def create_progress() -> Progress:
    """
    Create a progress bar instance.
    
    Returns:
        Progress instance
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )


def format_os_badge(os_name: str) -> str:
    """
    Format OS name as a badge/emoji.
    
    Args:
        os_name: OS name (windows, linux, macos, darwin)
        
    Returns:
        Emoji or abbreviation for the OS
    """
    os_name_lower = os_name.lower()
    if os_name_lower == "windows":
        return "🪟"
    elif os_name_lower in ["linux"]:
        return "🐧"
    elif os_name_lower in ["macos", "darwin"]:
        return "🍎"
    else:
        return os_name[:3].upper()


def format_os_compatibility(
    target_os_list: Optional[List[str]],
    current_os: str,
    show_checkmark: bool = True
) -> str:
    """
    Format OS compatibility badges with current OS indicator.
    
    Args:
        target_os_list: List of target OS names
        current_os: Current OS name (normalized)
        show_checkmark: Whether to show checkmark for compatible OS
        
    Returns:
        Formatted OS compatibility string with Rich markup
    """
    if not target_os_list:
        return "[dim]?[/dim]"  # Unknown OS compatibility
    
    # Normalize OS names
    target_os_normalized = [os_name.lower() for os_name in target_os_list]
    if "darwin" in target_os_normalized or "macos" in target_os_normalized:
        target_os_normalized = [os_name for os_name in target_os_normalized if os_name not in ["darwin", "macos"]]
        target_os_normalized.append("macos")
    
    # Create badges
    os_badges = [format_os_badge(os_name) for os_name in target_os_normalized]
    os_compat = " ".join(os_badges)
    
    # Check compatibility
    if current_os in target_os_normalized:
        if show_checkmark:
            return f"[bold #44FFD1]{os_compat}[/bold #44FFD1] ✓"
        else:
            return f"[bold #44FFD1]{os_compat}[/bold #44FFD1]"
    else:
        return f"[dim]{os_compat}[/dim]"


def format_manager_preferences(
    preferred_managers: Optional[Dict[str, List[str]]],
    current_os: str,
    max_display: int = 2
) -> str:
    """
    Format manager preferences for display.
    
    Args:
        preferred_managers: Dict of OS to manager list
        current_os: Current OS name (normalized)
        max_display: Maximum number of managers to show before truncating
        
    Returns:
        Formatted manager preferences string
    """
    if not preferred_managers:
        return "—"
    
    if current_os in preferred_managers:
        managers = preferred_managers[current_os]
        if len(managers) <= max_display:
            return ", ".join(managers)
        else:
            return ", ".join(managers[:max_display]) + "..."
    else:
        # Show first OS's managers if current OS not found
        first_os = list(preferred_managers.keys())[0]
        managers = preferred_managers[first_os]
        if len(managers) <= max_display:
            return ", ".join(managers)
        else:
            return ", ".join(managers[:max_display]) + "..."


def format_os_status(
    target_os_list: Optional[List[str]],
    current_os: str
) -> Tuple[str, str]:
    """
    Get OS compatibility status and color.
    
    Args:
        target_os_list: List of target OS names
        current_os: Current OS name (normalized)
        
    Returns:
        Tuple of (status_text, color_hex)
    """
    if not target_os_list:
        return ("Not specified", "#888888")
    
    # Normalize OS names
    target_os_normalized = [os_name.lower() for os_name in target_os_list]
    if "darwin" in target_os_normalized or "macos" in target_os_normalized:
        target_os_normalized = [os_name for os_name in target_os_normalized if os_name not in ["darwin", "macos"]]
        target_os_normalized.append("macos")
    
    if current_os in target_os_normalized:
        return ("✓ Compatible", "#44FFD1")
    else:
        return ("✗ Not compatible", "#FF6B6B")

