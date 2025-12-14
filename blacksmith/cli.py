"""Main CLI interface for Blacksmith."""

import sys
from pathlib import Path
from typing import Optional

import click
import questionary
from rich.console import Console

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

logger = setup_logger(__name__)


def show_banner():
    """Display ASCII art banner with version and developer info."""
    import platform
    import sys
    
    # ASCII art for blacksmith (lowercase)
    ascii_art = """
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


def show_installation_summary(config: dict, available_managers: list):
    """Show what will be installed before confirmation."""
    packages = config.get("packages", [])
    
    rows = []
    for pkg in packages:
        pkg_name = pkg.get("name", "Unknown")
        manager_info = find_manager_for_package(pkg, available_managers)
        if manager_info:
            mgr, pkg_id = manager_info
            rows.append([pkg_name, f"{mgr.name}: {pkg_id}"])
        else:
            rows.append([pkg_name, "❌ No compatible manager found"])
    
    print_table(
        f"Installation Summary - {config.get('name', 'Unknown Set')}",
        ["Package", "Manager"],
        rows
    )
    
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


def install_packages(config: dict, skip_installed: bool = False):
    """Install packages from configuration."""
    available_managers = detect_available_managers()
    
    if not available_managers:
        print_error("No package managers detected on this system.")
        return False
    
    # Show detected managers
    manager_names = [mgr.name for mgr in available_managers]
    print_info(f"Detected package managers: {', '.join(manager_names)}")
    
    # Show summary and get confirmation
    confirmation = show_installation_summary(config, available_managers)
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
    
    # Group packages by manager
    manager_packages = {}
    skipped = []
    not_found = []
    
    for pkg in packages:
        pkg_name = pkg.get("name", "Unknown")
        manager_info = find_manager_for_package(pkg, available_managers)
        
        if not manager_info:
            not_found.append(pkg_name)
            continue
        
        mgr, pkg_id = manager_info
        
        # Check if already installed
        if skip_installed and mgr.is_installed(pkg_id):
            skipped.append(pkg_name)
            print_info(f"⏭  Skipping {pkg_name} (already installed)")
            continue
        
        if mgr.name not in manager_packages:
            manager_packages[mgr.name] = []
        manager_packages[mgr.name].append((pkg_name, pkg_id, mgr))
    
    # Install packages by manager
    success_count = 0
    fail_count = 0
    
    with create_progress() as progress:
        for manager_name, pkg_list in manager_packages.items():
            # Get the manager instance (they're all the same for a given name)
            mgr = pkg_list[0][2]
            pkg_ids = [pkg_id for _, pkg_id, _ in pkg_list]
            
            task = progress.add_task(f"Installing via {manager_name}...", total=len(pkg_ids))
            
            if mgr.install(pkg_ids):
                progress.update(task, completed=len(pkg_ids))
                success_count += len(pkg_ids)
                for pkg_name, _, _ in pkg_list:
                    print_success(f"Installed {pkg_name}")
            else:
                progress.update(task, completed=len(pkg_ids))
                fail_count += len(pkg_ids)
                for pkg_name, _, _ in pkg_list:
                    print_error(f"Failed to install {pkg_name}")
    
    # Summary
    console.print()
    if skipped:
        print_info(f"Skipped {len(skipped)} already installed package(s)")
    if not_found:
        print_warning(f"Could not find manager for {len(not_found)} package(s)")
    if success_count > 0:
        print_success(f"Successfully installed {success_count} package(s)")
    if fail_count > 0:
        print_error(f"Failed to install {fail_count} package(s)")
    
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
            confirmation = show_installation_summary(config, detect_available_managers())
            
            if confirmation == "back":
                # User wants to go back to menu, continue loop
                continue
            elif confirmation:
                # User confirmed, proceed with installation
                result = install_packages(config)
                
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
    sets = list_available_sets()
    
    if not sets:
        print_error("No pre-made sets found.")
        return
    
    rows = []
    for set_name in sets:
        config = load_set(set_name)
        if config:
            description = config.get("description", "No description")
            package_count = len(config.get("packages", []))
            rows.append([set_name, description, str(package_count)])
    
    print_table(
        "Available Sets",
        ["Name", "Description", "Packages"],
        rows
    )


@cli.command()
@click.argument("set_name", required=False)
@click.option("--file", "-f", "config_file", help="Path to custom config file")
@click.option("--skip-installed", "-s", is_flag=True, help="Skip already installed packages")
def install(set_name: Optional[str], config_file: Optional[str], skip_installed: bool):
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
    success = install_packages(config, skip_installed=skip_installed)
    sys.exit(0 if success else 1)


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
        available_managers = [mgr for mgr in available_managers if mgr.name == manager]
        if not available_managers:
            print_error(f"Package manager '{manager}' not found.")
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
def create():
    """Interactively create a new tool set."""
    print_panel("Create New Set", "This will guide you through creating a custom tool set.")
    
    name = questionary.text("Set name:").ask()
    if not name:
        print_error("Set name is required.")
        return
    
    description = questionary.text("Description (optional):").ask() or ""
    
    print_info("Add packages to your set. You can search for packages or enter them manually.")
    print_info("Press Enter with empty package name to finish.")
    
    packages = []
    available_managers = detect_available_managers()
    
    while True:
        pkg_name = questionary.text("Package name (or Enter to finish):").ask()
        if not pkg_name:
            break
        
        # Offer to search
        search_choice = questionary.select(
            f"Search for '{pkg_name}' in package managers?",
            choices=[
                questionary.Choice("Yes, search for package", "search"),
                questionary.Choice("No, enter manually", "manual")
            ]
        ).ask()
        
        managers = {}
        
        if search_choice == "search":
            # Search across all managers
            for mgr in available_managers:
                results = mgr.search(pkg_name, limit=5)
                if results:
                    choices = [
                        questionary.Choice(f"{pkg['name']} - {pkg.get('description', '')[:50]}", pkg['name'])
                        for pkg in results
                    ]
                    choices.append(questionary.Choice("Skip this manager", None))
                    
                    selected = questionary.select(
                        f"Select package from {mgr.name}:",
                        choices=choices
                    ).ask()
                    
                    if selected:
                        managers[mgr.name] = selected
                        print_success(f"Found {selected} in {mgr.name}")
                else:
                    # No results, ask manually
                    pkg_id = questionary.text(
                        f"  {mgr.name} package name (or Enter to skip):"
                    ).ask()
                    if pkg_id:
                        managers[mgr.name] = pkg_id
        else:
            # Manual entry
            for mgr in available_managers:
                pkg_id = questionary.text(
                    f"  {mgr.name} package name (or Enter to skip):"
                ).ask()
                if pkg_id:
                    # Validate package if possible
                    if hasattr(mgr, 'validate_package'):
                        if not mgr.validate_package(pkg_id):
                            print_warning(f"Package '{pkg_id}' not found in {mgr.name}. Adding anyway...")
                    managers[mgr.name] = pkg_id
        
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
    
    # Create config dict
    config = {
        "name": name,
        "description": description,
        "packages": packages
    }
    
    # Save to file
    output_file = questionary.text(
        "Output file path:",
        default=f"{name.lower().replace(' ', '_')}.yaml"
    ).ask()
    
    if output_file:
        import yaml
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
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
    uninstall_methods = [
        # Method 1: Use the same Python that's running Blacksmith
        ([python_exe, "-m", "pip", "uninstall", "-y", "blacksmith"], "python -m pip"),
        # Method 2: With --user flag
        ([python_exe, "-m", "pip", "uninstall", "-y", "--user", "blacksmith"], "python -m pip --user"),
        # Method 3: Try pip directly
        (["pip", "uninstall", "-y", "blacksmith"], "pip"),
        # Method 4: pip with --user
        (["pip", "uninstall", "-y", "--user", "blacksmith"], "pip --user"),
        # Method 5: pip3
        (["pip3", "uninstall", "-y", "blacksmith"], "pip3"),
        # Method 6: Windows Python launcher
        (["py", "-m", "pip", "uninstall", "-y", "blacksmith"], "py -m pip"),
        # Method 7: python3 -m pip
        (["python3", "-m", "pip", "uninstall", "-y", "blacksmith"], "python3 -m pip"),
        # Method 8: python -m pip (if python_exe is different)
        (["python", "-m", "pip", "uninstall", "-y", "blacksmith"], "python -m pip"),
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
                # Also try to remove the executable if it still exists
                if os.path.exists(blacksmith_path):
                    try:
                        os.remove(blacksmith_path)
                        print_success(f"Removed executable: {blacksmith_path}")
                    except Exception as e:
                        print_warning(f"Could not remove executable: {e}")
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
    print_info(f"  - Run: {python_exe} -m pip uninstall blacksmith")
    print_info("  - Or: pip uninstall blacksmith")
    print_info("  - Or: pip uninstall --user blacksmith")
    
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

