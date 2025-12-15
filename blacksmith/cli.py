"""Main CLI interface for Blacksmith."""

import sys
from pathlib import Path
from typing import Optional

import click
import questionary
from rich.console import Console
from rich.table import Table

from blacksmith import __version__
from blacksmith.config.loader import load_custom_config, load_set, list_available_sets
from blacksmith.config.validator import validate_and_report
from blacksmith.package_managers.detector import detect_available_managers, find_manager_for_package
from blacksmith.utils.logger import setup_logger
from blacksmith.utils.os_detector import detect_os
from blacksmith.utils.ui import (
    create_progress,
    print_error,
    print_info,
    print_panel,
    print_success,
    print_table,
    print_warning,
)

# Use the themed console from ui module
from blacksmith.utils.ui import console

# Setup logger
logger = setup_logger(__name__)

logger = setup_logger(__name__)


def show_banner():
    """Display ASCII art banner with version and developer info."""
    import platform
    import sys
    
    # ASCII art for blacksmith (lowercase)
    ascii_art = r"""
  _     _            _                  _ _   _     
 | |__ | | __ _  ___| | _____ _ __ ___ (_) |_| |__  
 | '_ \| |/ _` |/ __| |/ / __| '_ ` _ \| | __| '_ \ 
 | |_) | | (_| | (__|   <\__ \ | | | | | | |_| | | |
 |_.__/|_|\__,_|\___|_|\_\___/_| |_| |_|_|\__|_| |_|
    """
    
    # Get system info
    os_name = platform.system()
    os_version = platform.release()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    # Create banner text with custom colors
    banner_text = f"""[bold #44FFD1]{ascii_art}[/bold #44FFD1]
[bold #44FFD1]Version:[/bold #44FFD1] {__version__}
[bold #44FFD1]Developer:[/bold #44FFD1] jimididit
[bold #44FFD1]OS:[/bold #44FFD1] {os_name} {os_version}
[bold #44FFD1]Python:[/bold #44FFD1] {python_version}

[dim #5A3A6C]Cross-platform development tool installer[/dim #5A3A6C]
    """
    
    console.print(banner_text)
    console.print()


def show_welcome():
    """Show welcome message."""
    show_banner()
    
    welcome_text = """
Blacksmith helps you quickly set up your development environment
by installing tools and applications using your system's package managers.

Select a pre-made set or use your own configuration file.
    """
    print_panel("Welcome", welcome_text.strip(), style="accent")


def show_sets_menu():
    """Show interactive menu to select a set."""
    sets = list_available_sets()
    
    if not sets:
        print_error("No pre-made sets found.")
        return None
    
    # Load set info for display
    set_info = []
    for set_name in sets:
        config = load_set(set_name)
        if config:
            description = config.get("description", "No description")
            package_count = len(config.get("packages", []))
            set_info.append({
                "name": set_name,
                "description": description,
                "count": package_count
            })
    
    # Create choices for questionary
    choices = [
        questionary.Choice(
            title=f"{info['name']:20} - {info['description']} ({info['count']} packages)",
            value=info['name']
        )
        for info in set_info
    ]
    
    # Add exit option at the end
    choices.append(
        questionary.Choice(
            title="Exit",
            value="__exit__"
        )
    )
    
    selected = questionary.select(
        "Select a set to install:",
        choices=choices
    ).ask()
    
    if selected == "__exit__":
        print_info("Goodbye!")
        return None
    
    return selected


def show_installation_summary(
    config: dict,
    available_managers: list,
    preferences: Optional[object] = None
):
    """Show what will be installed before confirmation."""
    from blacksmith.package_managers.detector import find_manager_for_package
    
    packages = config.get("packages", [])
    managers_supported = config.get("managers_supported")
    
    rows = []
    for pkg in packages:
        pkg_name = pkg.get("name", "Unknown")
        manager_info = find_manager_for_package(
            pkg,
            available_managers,
            preferred_order=preferences,
            managers_supported=managers_supported
        )
        if manager_info:
            mgr, pkg_id = manager_info
            # Show if this was chosen from multiple options
            pkg_managers = pkg.get("managers", {})
            if len(pkg_managers) > 1:
                # Highlight the selected manager
                manager_display = f"[bold #44FFD1]{mgr.name}[/bold #44FFD1]: {pkg_id}"
                manager_display += f" [dim](selected from {len(pkg_managers)} options)[/dim]"
                rows.append([pkg_name, manager_display])
            else:
                rows.append([pkg_name, f"[bold #44FFD1]{mgr.name}[/bold #44FFD1]: {pkg_id}"])
        else:
            rows.append([pkg_name, "[bold red]❌ No compatible manager found[/bold red]"])
    
    # Use Rich table for better formatting
    table = Table(title=f"Installation Summary - {config.get('name', 'Unknown Set')}", show_header=True, header_style="bold #44FFD1")
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Manager", style="white")
    
    for row in rows:
        table.add_row(row[0], row[1])
    
    console.print()
    console.print(table)
    
    if not rows:
        print_warning("No packages to install.")
        return False
    
    # Provide options: proceed, cancel, or go back
    choice = questionary.select(
        "What would you like to do?",
        choices=[
            questionary.Choice("Proceed with installation", "proceed"),
            questionary.Choice("Cancel", "cancel"),
            questionary.Choice("Go back to menu", "back")
        ],
        default="proceed"
    ).ask()
    
    if choice == "proceed":
        return True
    elif choice == "back":
        return "back"
    else:
        return False


def install_packages(
    config: dict,
    skip_installed: bool = False,
    show_summary: bool = True,
    prefer_manager: Optional[str] = None,
    force: bool = False
):
    """Install packages from configuration.
    
    Args:
        config: Configuration dict with packages to install
        skip_installed: If True, skip already installed packages without prompting
        show_summary: If True, show installation summary and prompt for confirmation
        prefer_manager: Optional manager name to prefer (overrides config preferences)
        force: If True, allow installation even if OS doesn't match target_os
    """
    from blacksmith.config.preferences import PreferredManagerOrder
    from blacksmith.utils.os_detector import detect_os
    
    # Detect current OS
    current_os = detect_os().lower()
    # Normalize macOS
    if current_os == "darwin":
        current_os = "macos"
    
    # Check OS compatibility
    target_os_list = config.get("target_os")
    
    if target_os_list:
        # Normalize OS names for comparison
        target_os_normalized = [os_name.lower() for os_name in target_os_list]
        # Handle macOS aliases
        if "darwin" in target_os_normalized or "macos" in target_os_normalized:
            target_os_normalized = [os_name for os_name in target_os_normalized if os_name not in ["darwin", "macos"]]
            target_os_normalized.append("macos")
        
        if current_os not in target_os_normalized:
            if not force:
                print_warning(f"This set targets: {', '.join(target_os_list)}")
                print_warning(f"Your current OS is: {current_os.capitalize()}")
                print_error("OS mismatch. Use --force to install anyway.")
                return False
            else:
                print_warning(f"Installing set for {', '.join(target_os_list)} on {current_os.capitalize()} (--force enabled)")
    
    available_managers = detect_available_managers()
    
    if not available_managers:
        print_error("No package managers detected on this system.")
        return False
    
    # Build preference system
    preferred_managers_config = config.get("preferred_managers")
    managers_supported = config.get("managers_supported")
    
    # Override with --prefer flag if provided
    if prefer_manager:
        custom_prefs = {current_os: [prefer_manager.lower()]}
        preferences = PreferredManagerOrder(custom_preferences=custom_prefs)
        print_info(f"Using preferred manager: {prefer_manager} (--prefer flag)")
    elif preferred_managers_config:
        preferences = PreferredManagerOrder(custom_preferences=preferred_managers_config)
        print_info("Using manager preferences from set configuration")
    else:
        preferences = PreferredManagerOrder()
        print_info("Using default manager preferences")
    
    # Filter available managers by managers_supported if specified
    if managers_supported:
        managers_supported_lower = [m.lower() for m in managers_supported]
        available_managers = [
            mgr for mgr in available_managers
            if mgr.name.lower() in managers_supported_lower
        ]
        if available_managers:
            print_info(f"Filtered to supported managers: {', '.join([m.name for m in available_managers])}")
    
    # Show detected managers
    manager_names = [mgr.name for mgr in available_managers]
    print_info(f"Detected package managers: {', '.join(manager_names)}")
    
    # Show summary and get confirmation (if requested)
    if show_summary:
        confirmation = show_installation_summary(config, available_managers, preferences)
        if confirmation == "back":
            return "back"
        elif not confirmation:
            print_info("Installation cancelled.")
            return False
    
    # Check if any managers require sudo
    requires_sudo = any(
        mgr.name in ['apt', 'pacman', 'yum', 'snap', 'flatpak']
        for mgr in available_managers
    )
    
    if requires_sudo:
        print_warning("Some package managers require sudo privileges.")
        print_info("You may be prompted for your password during installation.")
        console.print()
    
    packages = config.get("packages", [])
    
    # Check each package and determine action
    packages_to_install = []  # (pkg_name, pkg_id, mgr, action) where action is 'install', 'reinstall', 'update'
    packages_to_skip = []
    not_found = []
    
    console.print()
    print_info("Checking installed packages...")
    
    for pkg in packages:
        pkg_name = pkg.get("name", "Unknown")
        # Use preferred manager order when finding manager
        manager_info = find_manager_for_package(
            pkg,
            available_managers,
            preferred_order=preferences,
            managers_supported=managers_supported
        )
        
        if not manager_info:
            not_found.append(pkg_name)
            # Show why it wasn't found
            pkg_managers = pkg.get("managers", {})
            available_manager_names = [m.name.lower() for m in available_managers]
            pkg_manager_names = [m.lower() for m in pkg_managers.keys()]
            
            if pkg_manager_names:
                missing = [m for m in pkg_manager_names if m not in available_manager_names]
                if missing:
                    print_warning(f"{pkg_name}: Required managers not available: {', '.join(missing)}")
            continue
        
        mgr, pkg_id = manager_info
        # Log which manager was chosen and why
        pkg_managers = pkg.get("managers", {})
        all_pkg_managers = list(pkg_managers.keys())
        if len(all_pkg_managers) > 1:
            print_info(f"{pkg_name}: Using {mgr.name} (preferred from available: {', '.join(all_pkg_managers)})")
        
        # Always check if installed
        if mgr.is_installed(pkg_id):
            # Package is installed - prompt user
            if skip_installed:
                # Old behavior: just skip
                packages_to_skip.append(pkg_name)
                print_info(f"⏭  Skipping {pkg_name} (already installed)")
            else:
                # New behavior: prompt user
                choices = [
                    questionary.Choice("Skip (keep current version)", "skip"),
                    questionary.Choice("Reinstall", "reinstall"),
                    questionary.Choice("Update (if available)", "update")
                ]
                
                action = questionary.select(
                    f"{pkg_name} is already installed. What would you like to do?",
                    choices=choices,
                    default="skip"
                ).ask()
                
                if action == "skip":
                    packages_to_skip.append(pkg_name)
                    print_info(f"⏭  Skipping {pkg_name}")
                elif action == "reinstall":
                    packages_to_install.append((pkg_name, pkg_id, mgr, "reinstall"))
                elif action == "update":
                    packages_to_install.append((pkg_name, pkg_id, mgr, "update"))
        else:
            # Package not installed - install it
            packages_to_install.append((pkg_name, pkg_id, mgr, "install"))
    
    # Group packages by manager and action
    manager_packages = {}  # {manager_name: [(pkg_name, pkg_id, mgr, action), ...]}
    
    for pkg_name, pkg_id, mgr, action in packages_to_install:
        if mgr.name not in manager_packages:
            manager_packages[mgr.name] = []
        manager_packages[mgr.name].append((pkg_name, pkg_id, mgr, action))
    
    # Install/update packages by manager
    success_count = 0
    fail_count = 0
    updated_count = 0
    reinstalled_count = 0
    
    if packages_to_install:
        console.print()
        with create_progress() as progress:
            for manager_name, pkg_list in manager_packages.items():
                # Get the manager instance (all entries for same manager have same instance)
                mgr = pkg_list[0][2]  # Get manager from first package
                
                # Process packages by action type
                install_list = [(name, pkg_id) for name, pkg_id, _, action in pkg_list if action in ["install", "reinstall"]]
                update_list = [(name, pkg_id) for name, pkg_id, _, action in pkg_list if action == "update"]
                
                # Handle updates
                if update_list:
                    task = progress.add_task(f"Updating via {manager_name}...", total=len(update_list))
                    for pkg_name, pkg_id in update_list:
                        if mgr.update_package(pkg_id):
                            progress.update(task, advance=1)
                            updated_count += 1
                            print_success(f"Updated {pkg_name}")
                        else:
                            progress.update(task, advance=1)
                            fail_count += 1
                            print_error(f"Failed to update {pkg_name}")
                
                # Handle installs/reinstalls
                if install_list:
                    task = progress.add_task(f"Installing via {manager_name}...", total=len(install_list))
                    pkg_ids = [pkg_id for _, pkg_id in install_list]
                    
                    if mgr.install(pkg_ids):
                        progress.update(task, completed=len(pkg_ids))
                        for pkg_name, pkg_id in install_list:
                            # Check if it was a reinstall by looking at original action
                            was_reinstall = any(name == pkg_name and action == "reinstall" 
                                              for name, _, _, action in pkg_list)
                            if was_reinstall:
                                reinstalled_count += 1
                                print_success(f"Reinstalled {pkg_name}")
                            else:
                                success_count += 1
                                print_success(f"Installed {pkg_name}")
                    else:
                        progress.update(task, completed=len(pkg_ids))
                        fail_count += len(pkg_ids)
                        for pkg_name, _ in install_list:
                            print_error(f"Failed to install {pkg_name}")
    
    # Summary
    console.print()
    if packages_to_skip:
        print_info(f"Skipped {len(packages_to_skip)} already installed package(s)")
    if updated_count > 0:
        print_success(f"Updated {updated_count} package(s)")
    if reinstalled_count > 0:
        print_success(f"Reinstalled {reinstalled_count} package(s)")
    if not_found:
        print_warning(f"Could not find manager for {len(not_found)} package(s)")
    if success_count > 0:
        print_success(f"Successfully installed {success_count} package(s)")
    if fail_count > 0:
        print_error(f"Failed to install/update {fail_count} package(s)")
    
    return fail_count == 0


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="Blacksmith")
@click.pass_context
def cli(ctx):
    """Blacksmith - Cross-platform development tool installer."""
    # If no subcommand, show interactive menu
    if ctx.invoked_subcommand is None:
        while True:
            show_welcome()
            selected = show_sets_menu()
            
            if not selected:
                # User chose to exit
                break
            
            config = load_set(selected)
            if not config:
                print_error(f"Failed to load set: {selected}")
                break
            
            # Show summary and get confirmation
            from blacksmith.config.preferences import PreferredManagerOrder
            preferences = PreferredManagerOrder(custom_preferences=config.get("preferred_managers"))
            confirmation = show_installation_summary(config, detect_available_managers(), preferences)
            
            if confirmation == "back":
                # User wants to go back to menu, continue loop
                continue
            elif confirmation:
                # User confirmed, proceed with installation (skip summary since we already showed it)
                result = install_packages(config, show_summary=False, prefer_manager=None, force=False)
                
                # Handle back option from install_packages
                if result == "back":
                    continue
                
                # After installation, ask if user wants to continue
                continue_choice = questionary.select(
                    "What would you like to do?",
                    choices=[
                        questionary.Choice("Install another set", "continue"),
                        questionary.Choice("Exit", "exit")
                    ],
                    default="exit"
                ).ask()
                
                if continue_choice == "exit":
                    print_info("Goodbye!")
                    break
            else:
                # User cancelled
                cancel_choice = questionary.select(
                    "What would you like to do?",
                    choices=[
                        questionary.Choice("Go back to menu", "back"),
                        questionary.Choice("Exit", "exit")
                    ],
                    default="back"
                ).ask()
                
                if cancel_choice == "exit":
                    print_info("Goodbye!")
                    break
                # Otherwise continue loop to show menu again
    else:
        # Show banner for subcommands (but not for built-in click commands)
        show_banner()


@cli.command()
def list():
    """List available pre-made sets."""
    from blacksmith.utils.os_detector import detect_os
    
    sets = list_available_sets()
    
    if not sets:
        print_error("No pre-made sets found.")
        return
    
    current_os = detect_os().lower()
    if current_os == "darwin":
        current_os = "macos"
    
    rows = []
    for set_name in sets:
        config = load_set(set_name)
        if config:
            description = config.get("description", "No description")
            package_count = len(config.get("packages", []))
            
            # OS compatibility badge (using helper)
            from blacksmith.utils.ui import format_os_compatibility, format_manager_preferences
            target_os_list = config.get("target_os")
            os_compat = format_os_compatibility(target_os_list, current_os)
            
            # Manager preferences info (using helper)
            preferred_managers = config.get("preferred_managers")
            managers_supported = config.get("managers_supported")
            if preferred_managers:
                mgr_info = format_manager_preferences(preferred_managers, current_os)
            elif managers_supported:
                mgr_info = f"{len(managers_supported)} manager(s)"
            else:
                mgr_info = "—"
            
            rows.append([set_name, description, str(package_count), os_compat, mgr_info])
    
    print_table(
        "Available Sets",
        ["Name", "Description", "Packages", "OS", "Managers"],
        rows
    )
    
    console.print()
    print_info("Legend: 🪟 Windows | 🐧 Linux | 🍎 macOS | ✓ Compatible with your OS")


@cli.command()
@click.argument("set_name", required=False)
@click.option("--file", "-f", "config_file", help="Path to custom config file")
@click.option("--skip-installed", "-s", is_flag=True, help="Skip already installed packages")
@click.option("--prefer", "-p", "prefer_manager", help="Prefer specific package manager (overrides config)")
@click.option("--force", is_flag=True, help="Force installation even if OS doesn't match target_os")
def install(
    set_name: Optional[str],
    config_file: Optional[str],
    skip_installed: bool,
    prefer_manager: Optional[str],
    force: bool
):
    """Install tools from a pre-made set or custom config file."""
    config = None
    
    if config_file:
        # Load custom config
        config = load_custom_config(config_file)
        if not config:
            print_error(f"Failed to load config file: {config_file}")
            sys.exit(1)
    elif set_name:
        # Load pre-made set
        config = load_set(set_name)
        if not config:
            print_error(f"Set '{set_name}' not found.")
            print_info("Use 'blacksmith list' to see available sets.")
            sys.exit(1)
    else:
        # Interactive mode
        show_welcome()
        selected = show_sets_menu()
        if not selected:
            return
        config = load_set(selected)
        if not config:
            print_error(f"Failed to load set: {selected}")
            sys.exit(1)
    
    # Install packages
    success = install_packages(
        config,
        skip_installed=skip_installed,
        prefer_manager=prefer_manager,
        force=force
    )
    sys.exit(0 if success else 1)


@cli.command()
@click.argument("set_name", required=False)
@click.option("--file", "-f", "config_file", type=click.Path(exists=True), help="Path to custom config file")
@click.option("--format", "-F", "export_format", 
              type=click.Choice(["winget", "choco", "chocolatey", "apt", "pacman", "scoop"], case_sensitive=False),
              help="Export format: winget, choco/chocolatey, apt, pacman, or scoop")
@click.option("--output", "-o", "output_file", help="Output file path")
def export(set_name: Optional[str], config_file: Optional[str], export_format: Optional[str], output_file: Optional[str]):
    """Export a set to native package manager format."""
    from blacksmith.config.loader import load_set, load_custom_config
    from blacksmith.export import (
        WingetExporter, ChocolateyExporter, AptExporter,
        PacmanExporter, ScoopExporter
    )
    
    # Load config
    config = None
    if config_file:
        config = load_custom_config(config_file)
        if not config:
            print_error(f"Failed to load config file: {config_file}")
            sys.exit(1)
    elif set_name:
        config = load_set(set_name)
        if not config:
            print_error(f"Set '{set_name}' not found.")
            print_info("Use 'blacksmith list' to see available sets.")
            sys.exit(1)
    else:
        # Interactive mode
        show_welcome()
        selected = show_sets_menu()
        if not selected:
            return
        config = load_set(selected)
        if not config:
            print_error(f"Failed to load set: {selected}")
            sys.exit(1)
    
    # Get format (interactive if not provided)
    if not export_format:
        export_format = questionary.select(
            "Select export format:",
            choices=[
                questionary.Choice("Winget (JSON)", "winget"),
                questionary.Choice("Chocolatey (packages.config)", "chocolatey"),
                questionary.Choice("Apt (text list)", "apt"),
                questionary.Choice("Pacman (text list)", "pacman"),
                questionary.Choice("Scoop (JSON)", "scoop"),
            ],
            default="winget"
        ).ask()
        
        if not export_format:
            print_info("Export cancelled.")
            return
    
    # Normalize format name
    export_format = export_format.lower()
    if export_format == "choco":
        export_format = "chocolatey"
    
    # Select exporter
    exporter = None
    if export_format == "winget":
        exporter = WingetExporter(config)
    elif export_format == "chocolatey":
        exporter = ChocolateyExporter(config)
    elif export_format == "apt":
        exporter = AptExporter(config)
    elif export_format == "pacman":
        exporter = PacmanExporter(config)
    elif export_format == "scoop":
        exporter = ScoopExporter(config)
    else:
        print_error(f"Unsupported export format: {export_format}")
        sys.exit(1)
    
    # Generate output filename if not provided
    if not output_file:
        set_name_safe = config.get("name", "set").lower().replace(" ", "_")
        output_file = f"{set_name_safe}{exporter.get_file_extension()}"
    
    # Export
    try:
        output = exporter.export(output_file)
        package_count = len(exporter.filter_packages_by_manager(export_format))
        print_success(f"Exported {package_count} package(s) to {output_file}")
        print_info(f"Format: {export_format}")
    except Exception as e:
        print_error(f"Export failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument("set_name", required=False)
@click.option("--file", "-f", "config_file", type=click.Path(exists=True), help="Path to custom config file")
def info(set_name: Optional[str], config_file: Optional[str]):
    """Show detailed information about a set."""
    from blacksmith.config.loader import load_set, load_custom_config
    from blacksmith.utils.os_detector import detect_os
    
    # Load config
    config = None
    if config_file:
        config = load_custom_config(config_file)
        if not config:
            print_error(f"Failed to load config file: {config_file}")
            sys.exit(1)
    elif set_name:
        config = load_set(set_name)
        if not config:
            print_error(f"Set '{set_name}' not found.")
            print_info("Use 'blacksmith list' to see available sets.")
            sys.exit(1)
    else:
        # Interactive mode
        show_welcome()
        selected = show_sets_menu()
        if not selected:
            return
        config = load_set(selected)
        if not config:
            print_error(f"Failed to load set: {selected}")
            sys.exit(1)
    
    # Display set information
    console.print()
    print_panel(
        f"Set Information: {config.get('name', 'Unknown')}",
        config.get('description', 'No description')
    )
    
    # OS compatibility
    current_os = detect_os().lower()
    if current_os == "darwin":
        current_os = "macos"
    
    # OS compatibility (using helper)
    from blacksmith.utils.ui import format_os_status
    target_os_list = config.get("target_os")
    if target_os_list:
        os_status, os_color = format_os_status(target_os_list, current_os)
        console.print(f"\n[bold]Target OS:[/bold] {', '.join(target_os_list)}")
        console.print(f"[bold]Your OS:[/bold] {current_os.capitalize()}")
        console.print(f"[bold {os_color}]{os_status}[/bold {os_color}]")
    else:
        console.print(f"\n[bold]Target OS:[/bold] [dim]Not specified (assumes current OS)[/dim]")
    
    # Manager preferences
    preferred_managers = config.get("preferred_managers")
    if preferred_managers:
        console.print(f"\n[bold]Preferred Managers:[/bold]")
        for os_name, managers in preferred_managers.items():
            console.print(f"  {os_name.capitalize()}: {', '.join(managers)}")
    else:
        console.print(f"\n[bold]Preferred Managers:[/bold] [dim]Using defaults[/dim]")
    
    # Managers supported
    managers_supported = config.get("managers_supported")
    if managers_supported:
        console.print(f"\n[bold]Supported Managers:[/bold] {', '.join(managers_supported)}")
    
    # Package count
    packages = config.get("packages", [])
    console.print(f"\n[bold]Packages:[/bold] {len(packages)}")
    
    # Show sample packages
    if packages:
        console.print(f"\n[bold]Sample Packages:[/bold]")
        try:
            for pkg in packages[:5]:
                pkg_name = pkg.get("name", "Unknown")
                managers_dict = pkg.get("managers", {})
                if managers_dict:
                    # Get manager names and ensure they're strings
                    manager_names = [str(m) for m in managers_dict.keys()]
                    # Limit to first 3 managers for display
                    manager_display = manager_names[:3]
                    manager_str = ', '.join(manager_display)
                    if len(manager_names) > 3:
                        manager_str += '...'
                    # Use console.print - ensure we're not accidentally invoking CLI
                    console.print(f"  • {pkg_name} [dim]({manager_str})[/dim]")
                else:
                    console.print(f"  • {pkg_name} [dim](no managers)[/dim]")
            if len(packages) > 5:
                console.print(f"  ... and {len(packages) - 5} more")
        except Exception as e:
            # If there's an error, just skip the sample packages display
            print_warning(f"Could not display sample packages: {e}")
    
    # Explicit return to prevent any issues
    return


@cli.command()
@click.argument("config_path", type=click.Path(exists=True))
def validate(config_path: str):
    """Validate a configuration file."""
    from blacksmith.config.parser import load_yaml
    
    try:
        data = load_yaml(config_path)
        if validate_and_report(data):
            print_success(f"Configuration file is valid: {config_path}")
            print_info(f"Name: {data.get('name', 'Unnamed')}")
            print_info(f"Packages: {len(data.get('packages', []))}")
        else:
            sys.exit(1)
    except Exception as e:
        print_error(f"Failed to validate config: {e}")
        sys.exit(1)


@cli.command()
@click.argument("query", required=False)
@click.option("--manager", "-m", help="Filter by specific package manager")
@click.option("--limit", "-l", default=10, help="Maximum number of results")
def search(query: Optional[str], manager: Optional[str], limit: int):
    """Search for packages across available package managers."""
    available_managers = detect_available_managers()
    
    if not available_managers:
        print_error("No package managers detected on this system.")
        return
    
    if not query:
        query = questionary.text("Search for package:").ask()
        if not query:
            print_info("Search cancelled.")
            return
    
    # Filter by manager if specified
    if manager:
        # Normalize manager name (handle aliases)
        manager_lower = manager.lower()
        manager_aliases = {
            'choco': 'chocolatey',
            'chocolatey': 'chocolatey',
            'winget': 'winget',
            'scoop': 'scoop',
            'apt': 'apt',
            'pacman': 'pacman',
            'yum': 'yum',
            'dnf': 'yum',  # DNF is handled by YumManager
            'snap': 'snap',
            'flatpak': 'flatpak'
        }
        
        # Get the canonical name
        canonical_name = manager_aliases.get(manager_lower, manager_lower)
        
        available_managers = [
            mgr for mgr in available_managers 
            if mgr.name.lower() == canonical_name
        ]
        if not available_managers:
            # Check if it's an OS-specific manager
            linux_managers = ['apt', 'pacman', 'yum', 'dnf', 'snap', 'flatpak']
            windows_managers = ['winget', 'chocolatey', 'choco', 'scoop']
            current_os = detect_os().lower()
            
            if canonical_name in linux_managers and current_os != 'linux':
                print_error(f"Package manager '{manager}' is only available on Linux.")
                print_info(f"You are currently on {current_os.capitalize()}.")
            elif canonical_name in windows_managers and current_os != 'windows':
                print_error(f"Package manager '{manager}' is only available on Windows.")
                print_info(f"You are currently on {current_os.capitalize()}.")
            else:
                print_error(f"Package manager '{manager}' not found.")
            
            print_info(f"Available managers on your system: {', '.join([m.name for m in detect_available_managers()])}")
            return
    
    print_info(f"Searching for '{query}'...")
    console.print()
    
    all_results = []
    for mgr in available_managers:
        results = mgr.search(query, limit=limit)
        if results:
            all_results.append((mgr.name, results))
    
    if not all_results:
        print_warning(f"No packages found for '{query}'")
        return
    
    # Display results
    for mgr_name, results in all_results:
        print_panel(
            f"Results from {mgr_name}",
            "\n".join([
                f"  • {pkg['name']}" + (f" - {pkg.get('description', '')[:60]}" if pkg.get('description') else "")
                for pkg in results
            ]),
            style="accent"
        )
        console.print()


@cli.command()
@click.option("--advanced", is_flag=True, help="Advanced mode: single-manager sets only")
def create(advanced: bool):
    """Interactively create a new tool set."""
    print_panel("Create New Set", "This will guide you through creating a custom tool set.")
    
    name = questionary.text("Set name:").ask()
    if not name:
        print_error("Set name is required.")
        return
    
    description = questionary.text("Description (optional):").ask() or ""
    
    # OS Selection
    console.print()
    if advanced:
        print_info("Advanced mode: Creating single-manager set")
        # In advanced mode, ask for single OS and single manager
        os_choices = [
            questionary.Choice("🪟 Windows", "windows"),
            questionary.Choice("🐧 Linux", "linux"),
        ]
        target_os_selection = questionary.select(
            "Target OS:",
            choices=os_choices
        ).ask()
        
        if target_os_selection is None:
            print_info("Creation cancelled.")
            return
        
        target_os_list = [target_os_selection]
        
        # Get managers for selected OS
        if target_os_selection == "windows":
            os_managers = ["winget", "chocolatey", "scoop"]
        else:
            os_managers = ["apt", "pacman", "yum", "snap", "flatpak"]
        
        selected_manager = questionary.select(
            "Select package manager:",
            choices=[questionary.Choice(mgr, mgr) for mgr in os_managers]
        ).ask()
        
        if selected_manager is None:
            print_info("Creation cancelled.")
            return
        
        selected_managers = {target_os_selection: [selected_manager]}
        managers_supported = [selected_manager]
        preferred_managers = {target_os_selection: [selected_manager]}
    else:
        # Normal mode: cross-platform with multiple managers
        print_info("Select target operating system(s) for this set:")
        os_choices = [
            questionary.Choice("🪟 Windows only", "windows"),
            questionary.Choice("🐧 Linux only", "linux"),
            questionary.Choice("🪟🐧 Windows and Linux (cross-platform)", "both"),
        ]
        
        target_os_selection = questionary.select(
            "Target OS:",
            choices=os_choices,
            default="both"
        ).ask()
        
        if target_os_selection is None:
            print_info("Creation cancelled.")
            return
        
        # Determine target OS list
        if target_os_selection == "both":
            target_os_list = ["windows", "linux"]
        else:
            target_os_list = [target_os_selection]
        
        # Manager Selection per OS
        from blacksmith.config.preferences import PreferredManagerOrder
        preferences = PreferredManagerOrder()
        selected_managers = {}
        managers_supported = []
        
        console.print()
        print_info("Select package managers to target for each OS:")
        
        for os_name in target_os_list:
            default_managers = preferences.get_preferred_order(os_name)
            
            # Get available managers for this OS
            os_managers = []
            if os_name == "windows":
                os_managers = ["winget", "chocolatey", "scoop"]
            elif os_name == "linux":
                os_managers = ["apt", "pacman", "yum", "snap", "flatpak"]
            
            if not os_managers:
                continue
            
            # Filter default_managers to only include those in os_managers
            # and ensure they match exactly (case-sensitive)
            # Create a set of lowercase os_managers for quick lookup
            os_managers_lower = {m.lower(): m for m in os_managers}
            valid_defaults = []
            for mgr in default_managers:
                mgr_lower = mgr.lower()
                if mgr_lower in os_managers_lower:
                    # Use the exact case from os_managers
                    valid_defaults.append(os_managers_lower[mgr_lower])
            
            # Create choices for checkbox
            manager_choices = [
                questionary.Choice(mgr, mgr)
                for mgr in os_managers
            ]
            
            # questionary.checkbox doesn't properly handle default parameter
            # Workaround: Don't pass default parameter, let user select manually
            # The user can still select the preferred managers if they want
            selected = questionary.checkbox(
                f"Select managers for {os_name.capitalize()}:",
                choices=manager_choices
            ).ask()
            
            if selected is None:
                print_info("Creation cancelled.")
                return
            
            selected_managers[os_name] = selected
            # Add to managers_supported list (avoid duplicates)
            for mgr in selected:
                if mgr not in managers_supported:
                    managers_supported.append(mgr)
        
        if not managers_supported:
            print_error("No package managers selected. Cannot create set.")
            return
        
        # Build preferred_managers dict
        preferred_managers = {}
        for os_name, managers in selected_managers.items():
            if managers:
                preferred_managers[os_name] = managers
    
    print_info("Add packages to your set. You can search for packages or enter them manually.")
    print_info("Press Enter with empty input to finish adding packages.")
    
    packages = []
    # Filter available managers to only those selected
    all_available_managers = detect_available_managers()
    available_managers = [
        mgr for mgr in all_available_managers
        if mgr.name.lower() in [m.lower() for m in managers_supported]
    ]
    
    if not available_managers:
        print_warning("None of the selected managers are available on this system.")
        print_info("You can still create the set, but packages will need to be entered manually.")
        # Keep available_managers as empty list - user can still enter packages manually
    
    while True:
        console.print()
        # Ask what the user wants to do
        action = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("🔍 Search for a package", "search"),
                questionary.Choice("✏️  Enter package manually", "manual"),
                questionary.Choice("✅ Finish and save set", "finish"),
                questionary.Choice("❌ Cancel and exit (don't save)", "cancel")
            ],
            default="search"
        ).ask()
        
        if action is None or action == "cancel":
            print_info("Creation cancelled. No changes saved.")
            return
        elif action == "finish":
            break
        elif action == "search":
            # Search for packages
            query = questionary.text("Search for package:").ask()
            if not query or query is None:
                continue
            
            print_info(f"Searching for '{query}'...")
            
            # Search across selected managers only
            all_results = {}
            searched_managers = []
            
            if available_managers:
                print_info(f"Searching in: {', '.join([m.name for m in available_managers])}")
                for mgr in available_managers:
                    searched_managers.append(mgr.name)
                    try:
                        results = mgr.search(query, limit=10)
                        if results:
                            all_results[mgr.name] = results
                            print_info(f"Found {len(results)} result(s) in {mgr.name}")
                        else:
                            # Manager searched but returned no results
                            print_info(f"No results found in {mgr.name}")
                            logger.debug(f"{mgr.name} search returned no results for '{query}'")
                    except Exception as e:
                        print_warning(f"Search failed for {mgr.name}: {e}")
                        logger.warning(f"Search failed for {mgr.name}: {e}")
                        # Continue with other managers even if one fails
            else:
                # No managers available, but user can still enter manually
                print_warning("No package managers available for searching on this system.")
                print_info("You can still add packages manually.")
                continue
            
            if not all_results:
                if searched_managers:
                    print_warning(f"No packages found for '{query}' in {', '.join(searched_managers)}")
                else:
                    print_warning(f"No packages found for '{query}'")
                continue
            
            # Build unified list of all results with manager labels
            unified_results = []
            for mgr_name, results in all_results.items():
                for pkg in results[:10]:  # Limit to top 10 per manager
                    pkg_id = pkg.get('name', '')
                    pkg_desc = pkg.get('description', '')[:50] or 'No description'
                    # Format: "[manager] PackageID - Description"
                    display_text = f"[{mgr_name}] {pkg_id}"
                    if pkg_desc and pkg_desc != 'No description':
                        display_text += f" - {pkg_desc}"
                    unified_results.append({
                        'manager': mgr_name,
                        'package_id': pkg_id,
                        'description': pkg_desc,
                        'display': display_text
                    })
            
            if not unified_results:
                print_warning(f"No packages found for '{query}'")
                continue
            
            # Show unified results table
            console.print()
            print_table(
                f"Search Results for '{query}'",
                ["Manager", "Package", "Description"],
                [
                    [result['manager'], result['package_id'], result['description']]
                    for result in unified_results
                ]
            )
            
            # Let user select multiple packages from all managers at once
            console.print()
            print_info("Select which packages to add (you can select multiple):")
            
            # Create checkbox choices for all results
            # Use string format "manager:package_id" for values to avoid tuple issues
            checkbox_choices = [
                questionary.Choice(
                    result['display'],
                    f"{result['manager']}:{result['package_id']}"  # Format: "manager:package_id"
                )
                for result in unified_results
            ]
            
            selected = questionary.checkbox(
                "Select packages to add:",
                choices=checkbox_choices
            ).ask()
            
            if selected is None:
                # User cancelled
                continue
            
            if not selected:
                print_info("No packages selected.")
                continue
            
            # Parse selected values (format: "manager:package_id")
            selected_packages = []
            for value in selected:
                if ':' in value:
                    mgr_name, pkg_id = value.split(':', 1)
                    selected_packages.append((mgr_name, pkg_id))
                else:
                    # Fallback if format is unexpected
                    print_warning(f"Unexpected format for selection: {value}")
            
            if not selected_packages:
                print_info("No valid packages selected.")
                continue
            
            # Show confirmation with what will be added
            console.print()
            print_info("You selected:")
            for mgr_name, pkg_id in selected_packages:
                console.print(f"  • {mgr_name}: {pkg_id}")
            
            confirm = questionary.confirm(
                "Add these packages to your set?",
                default=True
            ).ask()
            
            if not confirm:
                print_info("Packages not added.")
                continue
            
            if selected_packages:
                # Group by package name (same package from different managers)
                pkg_groups = {}
                for mgr_name, pkg_id in selected_packages:
                    # Extract base name - handle various formats:
                    # - "postman|11.46.6" -> "postman" (Chocolatey format)
                    # - "Git.Git" -> "git" (Winget format)
                    # - "git" -> "git" (simple format)
                    base_name = pkg_id
                    
                    # Remove version info (Chocolatey uses |, others might use @ or -)
                    if '|' in base_name:
                        base_name = base_name.split('|')[0]
                    elif '@' in base_name:
                        base_name = base_name.split('@')[0]
                    
                    # Extract from Publisher.Package format (Winget)
                    if '.' in base_name:
                        base_name = base_name.split('.')[-1]
                    
                    # Extract from repo/package format (some managers)
                    if '/' in base_name:
                        base_name = base_name.split('/')[-1]
                    
                    # Clean up: lowercase and remove any remaining special chars
                    base_name = base_name.lower().strip()
                    
                    # Use original query as fallback if extraction fails
                    if not base_name or len(base_name) < 2:
                        base_name = query.lower()
                    
                    if base_name not in pkg_groups:
                        pkg_groups[base_name] = {"name": base_name, "managers": {}}
                    pkg_groups[base_name]["managers"][mgr_name] = pkg_id
                
                # Ask user to confirm package name
                for base_name, pkg_data in pkg_groups.items():
                    suggested_name = questionary.text(
                        f"Package display name (default: {base_name}):",
                        default=base_name
                    ).ask() or base_name
                    
                    packages.append({
                        "name": suggested_name,
                        "managers": pkg_data["managers"]
                    })
                    print_success(f"Added {suggested_name} with {len(pkg_data['managers'])} manager(s)")
            else:
                print_info("No packages selected")
        
        elif action == "manual":
            # Manual entry - show all selected managers, not just available ones
            pkg_name = questionary.text("Package display name:").ask()
            if not pkg_name:
                continue
            
            managers = {}
            # Show all selected managers, even if not available on current system
            for mgr_name in managers_supported:
                pkg_id = questionary.text(
                    f"  {mgr_name} package name (or Enter to skip):"
                ).ask()
                if pkg_id and pkg_id.strip():
                    # If manager is available, try to validate
                    mgr_instance = next(
                        (m for m in all_available_managers if m.name.lower() == mgr_name.lower()),
                        None
                    )
                    if mgr_instance and hasattr(mgr_instance, 'validate_package'):
                        if not mgr_instance.validate_package(pkg_id):
                            print_warning(f"Package '{pkg_id}' not found in {mgr_name}. Adding anyway...")
                    managers[mgr_name] = pkg_id
            
            if managers:
                packages.append({
                    "name": pkg_name,
                    "managers": managers
                })
                print_success(f"Added {pkg_name}")
            else:
                print_warning(f"Skipped {pkg_name} (no managers specified)")
    
    if not packages:
        print_error("No packages added. Set creation cancelled.")
        return
    
    # Show summary
    console.print()
    print_info(f"Set will contain {len(packages)} package(s):")
    for pkg in packages:
        manager_count = len(pkg.get("managers", {}))
        print_info(f"  - {pkg['name']} ({manager_count} manager(s))")
    
    # Create config dict with metadata
    config = {
        "name": name,
        "description": description,
        "packages": packages,
        "target_os": target_os_list,
    }
    
    # Add preferred_managers if specified
    if preferred_managers:
        config["preferred_managers"] = preferred_managers
    
    # Add managers_supported if specified
    if managers_supported:
        config["managers_supported"] = managers_supported
    
    # Save to file
    output_file = questionary.text(
        "Output file path:",
        default=f"{name.lower().replace(' ', '_')}.yaml"
    ).ask()
    
    if output_file:
        import yaml
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print_success(f"Set saved to {output_file}")
    else:
        print_error("No output file specified.")


@cli.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def uninstall(yes: bool):
    """Uninstall Blacksmith from your system."""
    import subprocess
    import shutil
    import sys
    import os
    import tempfile
    import time
    
    def create_cleanup_script(target_file: str) -> str:
        """
        Create a temporary script that will delete the target file and itself.
        Returns the path to the created script.
        """
        if os.name == 'nt':  # Windows
            # Create a PowerShell script
            script_content = f"""
# Wait for the process to fully exit
Start-Sleep -Seconds 2

# Try to delete the target file
$target = '{target_file}'
if (Test-Path $target) {{
    try {{
        Remove-Item $target -Force -ErrorAction Stop
        Write-Host "Deleted: $target"
    }} catch {{
        Write-Host "Could not delete: $target"
        Write-Host "Error: $_"
    }}
}}

# Delete this script itself
$scriptPath = $MyInvocation.MyCommand.Path
Start-Sleep -Seconds 1
if (Test-Path $scriptPath) {{
    Remove-Item $scriptPath -Force -ErrorAction SilentlyContinue
}}
"""
            # Create temp PowerShell script
            fd, script_path = tempfile.mkstemp(suffix='.ps1', prefix='blacksmith_cleanup_', text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(script_content)
            return script_path
        else:  # Linux/Mac
            # Create a bash script
            script_content = f"""#!/bin/bash
# Wait for the process to fully exit
sleep 2

# Try to delete the target file
if [ -f '{target_file}' ]; then
    rm -f '{target_file}' && echo "Deleted: {target_file}" || echo "Could not delete: {target_file}"
fi

# Delete this script itself
SCRIPT_PATH="$0"
sleep 1
rm -f "$SCRIPT_PATH"
"""
            # Create temp bash script
            fd, script_path = tempfile.mkstemp(suffix='.sh', prefix='blacksmith_cleanup_', text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(script_content)
            # Make it executable
            os.chmod(script_path, 0o755)
            return script_path
    
    
    print_panel("Uninstall Blacksmith", "This will remove Blacksmith from your system.")
    
    # Check if blacksmith command exists
    blacksmith_path = shutil.which("blacksmith")
    if not blacksmith_path:
        print_warning("Blacksmith does not appear to be installed.")
        return
    
    print_info(f"Found Blacksmith at: {blacksmith_path}")
    
    # Confirm uninstallation
    if not yes:
        confirmed = questionary.confirm(
            "Are you sure you want to uninstall Blacksmith?",
            default=False
        ).ask()
        if not confirmed:
            print_info("Uninstallation cancelled.")
            return
    
    # Try different uninstall methods
    print_info("Attempting to uninstall Blacksmith...")
    
    # Detect which Python executable is running Blacksmith
    python_exe = sys.executable
    
    # List of methods to try (in order of likelihood)
    # Try both package names in case user installed from PyPI (jdi-blacksmith) or from source (blacksmith)
    uninstall_methods = [
        # Method 1: Use the same Python that's running Blacksmith (PyPI package name)
        ([python_exe, "-m", "pip", "uninstall", "-y", "jdi-blacksmith"], "python -m pip"),
        # Method 2: With --user flag (PyPI package name)
        ([python_exe, "-m", "pip", "uninstall", "-y", "--user", "jdi-blacksmith"], "python -m pip --user"),
        # Method 3: Try pip directly (PyPI package name)
        (["pip", "uninstall", "-y", "jdi-blacksmith"], "pip"),
        # Method 4: pip with --user (PyPI package name)
        (["pip", "uninstall", "-y", "--user", "jdi-blacksmith"], "pip --user"),
        # Method 5: Fallback to old package name (for source installs)
        ([python_exe, "-m", "pip", "uninstall", "-y", "blacksmith"], "python -m pip (fallback)"),
        # Method 6: pip3 (PyPI package name)
        (["pip3", "uninstall", "-y", "jdi-blacksmith"], "pip3"),
        # Method 7: Windows Python launcher (PyPI package name)
        (["py", "-m", "pip", "uninstall", "-y", "jdi-blacksmith"], "py -m pip"),
        # Method 8: python3 -m pip (PyPI package name)
        (["python3", "-m", "pip", "uninstall", "-y", "jdi-blacksmith"], "python3 -m pip"),
        # Method 9: python -m pip (PyPI package name)
        (["python", "-m", "pip", "uninstall", "-y", "jdi-blacksmith"], "python -m pip"),
    ]
    
    for cmd, method_name in uninstall_methods:
        try:
            # On Windows, use shell=True for better command resolution
            shell = os.name == 'nt'
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                shell=shell
            )
            
            if result.returncode == 0:
                print_success(f"Blacksmith uninstalled successfully using {method_name}.")
                # Try to remove the executable if it still exists
                # Note: This may fail if Blacksmith is currently running (which it is, since we're in it)
                if os.path.exists(blacksmith_path):
                    try:
                        # Check if we're running from this executable
                        current_exe = sys.executable
                        if os.path.exists(current_exe) and os.path.samefile(current_exe, blacksmith_path):
                            print_warning("Cannot remove executable while Blacksmith is running.")
                            print_info("Creating cleanup script to delete it after this process exits...")
                            
                            try:
                                cleanup_script = create_cleanup_script(blacksmith_path)
                                
                                # Launch the cleanup script in a separate process
                                if os.name == 'nt':  # Windows
                                    # Use PowerShell to run the script in background
                                    subprocess.Popen(
                                        ['powershell', '-ExecutionPolicy', 'Bypass', '-File', cleanup_script],
                                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL
                                    )
                                else:  # Linux/Mac
                                    # Run bash script in background
                                    subprocess.Popen(
                                        ['bash', cleanup_script],
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL
                                    )
                                
                                print_success("Cleanup script created. The executable will be deleted automatically.")
                                print_info("You can close this terminal now.")
                            except Exception as e:
                                logger.debug(f"Failed to create cleanup script: {e}")
                                print_warning("Could not create automatic cleanup script.")
                                print_info("Please manually delete the executable after closing this terminal:")
                                print_info(f"  {blacksmith_path}")
                        else:
                            os.remove(blacksmith_path)
                            print_success(f"Removed executable: {blacksmith_path}")
                    except PermissionError as e:
                        print_warning("Cannot remove executable - it's currently in use.")
                        print_info("This is normal when uninstalling from within Blacksmith.")
                        print_info("Creating cleanup script to delete it after this process exits...")
                        
                        try:
                            cleanup_script = create_cleanup_script(blacksmith_path)
                            
                            # Launch the cleanup script in a separate process
                            if os.name == 'nt':  # Windows
                                # Use PowerShell to run the script in background
                                subprocess.Popen(
                                    ['powershell', '-ExecutionPolicy', 'Bypass', '-File', cleanup_script],
                                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL
                                )
                            else:  # Linux/Mac
                                # Run bash script in background
                                subprocess.Popen(
                                    ['bash', cleanup_script],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL
                                )
                            
                            print_success("Cleanup script created. The executable will be deleted automatically.")
                            print_info("You can close this terminal now.")
                        except Exception as e:
                            logger.debug(f"Failed to create cleanup script: {e}")
                            print_warning("Could not create automatic cleanup script.")
                            print_info("Please manually delete the executable after closing this terminal:")
                            print_info(f"  {blacksmith_path}")
                    except Exception as e:
                        print_warning(f"Could not remove executable: {e}")
                        print_info(f"You may need to manually delete: {blacksmith_path}")
                else:
                    print_success("Executable already removed.")
                return
            else:
                # Log the error for debugging (but don't show to user unless all fail)
                logger.debug(f"Uninstall method {method_name} failed: {result.stderr}")
        except FileNotFoundError:
            # Command not found, try next method
            continue
        except subprocess.TimeoutExpired:
            print_warning(f"Uninstall method {method_name} timed out.")
            continue
        except Exception as e:
            logger.debug(f"Uninstall method {method_name} raised exception: {e}")
            continue
    
    # If all methods failed, show detailed error
    print_error("Could not automatically uninstall Blacksmith.")
    print_info("You may need to manually remove it:")
    print_info(f"  - Remove the command: {blacksmith_path}")
    print_info(f"  - Run: {python_exe} -m pip uninstall jdi-blacksmith")
    print_info("  - Or: pip uninstall jdi-blacksmith")
    print_info("  - Or: pip uninstall --user jdi-blacksmith")
    print_info("  - If installed from source: pip uninstall blacksmith")
    
    # Try to show what went wrong with the last method
    if blacksmith_path:
        print_info("\nTroubleshooting:")
        print_info(f"  - Python executable: {python_exe}")
        print_info(f"  - Blacksmith path: {blacksmith_path}")
        print_info("  - Try running the pip command manually to see the error")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()

