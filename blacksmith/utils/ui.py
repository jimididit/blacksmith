"""UI helpers using Rich for beautiful terminal output."""

import sys
from typing import Any, Dict, List, Optional

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

