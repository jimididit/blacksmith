"""Main CLI interface for Blacksmith."""

import sys
from pathlib import Path
from typing import Any, List, Optional

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
    
    # Properly detect Windows version (Windows 11 has build >= 22000)
    if os_name == "Windows":
        try:
            # platform.version() returns something like "10.0.22000.1234"
            # Windows 11 has build number >= 22000
            version_info = platform.version().split('.')
            if len(version_info) >= 3:
                build_number = int(version_info[2])
                if build_number >= 22000:
                    os_version = "11"
                else:
                    os_version = "10"
            else:
                os_version = platform.release()
        except (ValueError, IndexError):
            # Fallback to release() if parsing fails
            os_version = platform.release()
    else:
        os_version = platform.release()
    
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    # Create banner text with custom colors
    banner_text = f"""[bold #44FFD1]{ascii_art}[/bold #44FFD1]
[bold #44FFD1]Version:[/bold #44FFD1] {__version__}
[bold #44FFD1]Developer:[/bold #44FFD1] jimididit
[bold #44FFD1]OS:[/bold #44FFD1] {os_name} {os_version}
[bold #44FFD1]Python:[/bold #44FFD1] {python_version}

[dim #5A3A6C]Cross-platform tool installer for development, cybersecurity, and more[/dim #5A3A6C]
    """
    
    console.print(banner_text)
    console.print()


def show_welcome():
    """Show welcome message."""
    show_banner()
    
    welcome_text = """
Blacksmith helps you quickly set up your environment
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
    available_managers: List[Any],
    preferences: Optional[object] = None,
    assume_yes: bool = False,
    dry_run: bool = False,
    config_source: Optional[str] = None,
):
    """Show what will be installed before confirmation."""
    from blacksmith.package_managers.detector import find_manager_for_package

    if config_source:
        print_warning(
            "Installing from a custom config file. Treat third-party YAML as untrusted "
            "until you have reviewed every package ID below."
        )
        print_info(f"Config source: {config_source}")
        console.print()
    
    packages = config.get("packages", [])
    managers_supported = config.get("managers_supported")
    
    rows = []
    plan_lines = []
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
            pkg_managers = pkg.get("managers", {})
            if len(pkg_managers) > 1:
                manager_display = f"[bold #44FFD1]{mgr.name}[/bold #44FFD1]: {pkg_id}"
                manager_display += f" [dim](selected from {len(pkg_managers)} options)[/dim]"
            else:
                manager_display = f"[bold #44FFD1]{mgr.name}[/bold #44FFD1]: {pkg_id}"

            if dry_run:
                try:
                    already = mgr.is_installed(pkg_id)
                except Exception:
                    already = False
                action = "skip (already installed)" if already else "install"
                rows.append([pkg_name, manager_display, action])
                plan_lines.append(f"{action}: {pkg_name} via {mgr.name} ({pkg_id})")
            else:
                rows.append([pkg_name, manager_display])
        else:
            if dry_run:
                rows.append([pkg_name, "[bold red]No compatible manager[/bold red]", "unavailable"])
                plan_lines.append(f"unavailable: {pkg_name} (no compatible manager)")
            else:
                rows.append([pkg_name, "[bold red]❌ No compatible manager found[/bold red]"])
    
    title_suffix = " (dry-run)" if dry_run else ""
    table = Table(
        title=f"Installation Summary - {config.get('name', 'Unknown Set')}{title_suffix}",
        show_header=True,
        header_style="bold #44FFD1",
    )
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Manager", style="white")
    if dry_run:
        table.add_column("Action", style="yellow")
    
    for row in rows:
        table.add_row(*row)
    
    console.print()
    console.print(table)

    if dry_run and plan_lines:
        console.print()
        print_info("Dry-run plan (package, manager, id, action):")
        for line in plan_lines:
            print_info(f"  {line}")
    
    if not rows:
        print_warning("No packages to install.")
        return False

    if dry_run:
        print_info("Dry-run only. No packages will be installed.")
        return "dry_run"

    if assume_yes:
        print_info("Proceeding without interactive confirmation (--yes).")
        return True
    
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
    force: bool = False,
    assume_yes: bool = False,
    dry_run: bool = False,
    config_source: Optional[str] = None,
    fail_fast: bool = False,
    apply_mode: bool = False,
):
    """Install or apply packages from configuration.

    Returns InstallRunResult. Interactive install still prompts on already-installed
    packages unless skip_installed/assume_yes. apply_mode always skips installed,
    verifies after successful install, and never prompts reinstall/update.

    Args:
        config: Configuration dict with packages to install
        skip_installed: If True, skip already installed packages without prompting
        show_summary: If True, show installation summary and prompt for confirmation
        prefer_manager: Optional manager name to prefer (overrides config preferences)
        force: If True, allow installation even if OS doesn't match target_os
        assume_yes: If True, skip interactive confirmation
        dry_run: If True, show plan and exit without installing
        config_source: Optional path/label for custom config trust warning
        fail_fast: If True, stop after the first install/update failure (default: continue)
        apply_mode: If True, ensure-state (skip installed, verify after install)
    """
    from blacksmith.config.preferences import PreferredManagerOrder
    from blacksmith.package_managers.results import InstallRunResult, PackageOutcome, PackageStatus
    from blacksmith.utils.identifiers import validate_package_id
    from blacksmith.utils.os_detector import detect_os
    from blacksmith.utils.tty import require_tty_or_yes

    tty_ok, tty_error = require_tty_or_yes(assume_yes, dry_run=dry_run)
    if not tty_ok:
        print_error(tty_error or "Non-interactive session requires --yes or --dry-run.")
        return InstallRunResult(ok=False)

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
                return InstallRunResult(ok=False)
            else:
                print_warning(f"Installing set for {', '.join(target_os_list)} on {current_os.capitalize()} (--force enabled)")
    
    available_managers = detect_available_managers()
    
    if not available_managers:
        print_error("No package managers detected on this system.")
        return InstallRunResult(ok=False)
    
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
        confirmation = show_installation_summary(
            config,
            available_managers,
            preferences,
            assume_yes=assume_yes,
            dry_run=dry_run,
            config_source=config_source,
        )
        if confirmation == "back":
            return InstallRunResult(ok=True, back=True)
        if confirmation == "dry_run":
            return InstallRunResult(ok=True)
        elif not confirmation:
            print_info("Installation cancelled.")
            return InstallRunResult(ok=False, cancelled=True)
    
    if dry_run:
        print_info("Dry-run only. No packages will be installed.")
        return InstallRunResult(ok=True)
    
    # Sudo: system PMs only. Flatpak is a first-class Linux PM but does not use sudo.
    sudo_managers = {"apt", "pacman", "yum", "snap"}
    requires_sudo = any(mgr.name in sudo_managers for mgr in available_managers)
    has_flatpak = any(mgr.name == "flatpak" for mgr in available_managers)

    if requires_sudo:
        print_warning("Some package managers require sudo privileges (apt, pacman, yum/dnf, snap).")
        print_info("You may be prompted for your password during installation.")
        if has_flatpak:
            print_info("Flatpak installs do not use that sudo path.")
        console.print()
    elif has_flatpak:
        print_info("Flatpak is available (no sudo required for Flatpak installs).")
        console.print()

    if fail_fast:
        print_info("Fail-fast enabled: stopping after the first install/update failure.")

    packages = config.get("packages", [])

    # Check each package and determine action
    packages_to_install = []  # (pkg_name, pkg_id, mgr, action)
    packages_to_skip = []
    not_found = []
    outcomes = []
    auto_skip = skip_installed or assume_yes or apply_mode

    console.print()
    print_info("Checking installed packages...")

    for pkg in packages:
        pkg_name = pkg.get("name", "Unknown")
        manager_info = find_manager_for_package(
            pkg,
            available_managers,
            preferred_order=preferences,
            managers_supported=managers_supported
        )

        if not manager_info:
            not_found.append(pkg_name)
            pkg_managers = pkg.get("managers", {})
            available_manager_names = [m.name.lower() for m in available_managers]
            pkg_manager_names = [m.lower() for m in pkg_managers.keys()]

            if pkg_manager_names:
                missing = [m for m in pkg_manager_names if m not in available_manager_names]
                if missing:
                    print_warning(f"{pkg_name}: Required managers not available: {', '.join(missing)}")
            if apply_mode:
                outcomes.append(PackageOutcome(
                    pkg_name, "", "none", "install", PackageStatus.FAILED,
                    message="no available manager",
                ))
            continue

        mgr, pkg_id = manager_info
        id_ok, id_error = validate_package_id(pkg_id)
        if not id_ok:
            print_error(f"{pkg_name}: refusing unsafe package ID for {mgr.name}: {id_error}")
            not_found.append(pkg_name)
            if apply_mode:
                outcomes.append(PackageOutcome(
                    pkg_name, pkg_id, mgr.name, "install", PackageStatus.FAILED,
                    message=id_error or "unsafe package ID",
                ))
            continue

        pkg_managers = pkg.get("managers", {})
        all_pkg_managers = [*pkg_managers]
        if len(all_pkg_managers) > 1:
            print_info(f"{pkg_name}: Using {mgr.name} (preferred from available: {', '.join(all_pkg_managers)})")

        if mgr.is_installed(pkg_id):
            if auto_skip:
                packages_to_skip.append(pkg_name)
                outcomes.append(PackageOutcome(
                    pkg_name, pkg_id, mgr.name, "skip", PackageStatus.SKIPPED,
                    message="already installed",
                ))
                print_info(f"⏭  Skipping {pkg_name} (already installed)")
            else:
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
                    outcomes.append(PackageOutcome(
                        pkg_name, pkg_id, mgr.name, "skip", PackageStatus.SKIPPED,
                    ))
                    print_info(f"⏭  Skipping {pkg_name}")
                elif action == "reinstall":
                    packages_to_install.append((pkg_name, pkg_id, mgr, "reinstall"))
                elif action == "update":
                    packages_to_install.append((pkg_name, pkg_id, mgr, "update"))
        else:
            packages_to_install.append((pkg_name, pkg_id, mgr, "install"))

    # Group by manager for progress labeling; still execute one package at a time.
    manager_packages = {}
    for pkg_name, pkg_id, mgr, action in packages_to_install:
        manager_packages.setdefault(mgr.name, []).append((pkg_name, pkg_id, mgr, action))

    stopped_early = False

    if packages_to_install:
        console.print()
        with create_progress() as progress:
            for manager_name, pkg_list in manager_packages.items():
                if stopped_early:
                    break
                task = progress.add_task(
                    f"Processing via {manager_name}...",
                    total=len(pkg_list),
                )
                for pkg_name, pkg_id, mgr, action in pkg_list:
                    if action == "update":
                        ok = mgr.update_package(pkg_id)
                        progress.update(task, advance=1)
                        if ok:
                            outcomes.append(PackageOutcome(
                                pkg_name, pkg_id, mgr.name, "update", PackageStatus.OK,
                            ))
                            print_success(f"Updated {pkg_name}")
                        else:
                            outcomes.append(PackageOutcome(
                                pkg_name, pkg_id, mgr.name, "update", PackageStatus.FAILED,
                            ))
                            print_error(f"Failed to update {pkg_name}")
                            if fail_fast:
                                stopped_early = True
                                print_warning("Fail-fast: stopping after update failure.")
                                break
                        continue

                    # install or reinstall — one ID at a time for honest reporting
                    ok = mgr.install([pkg_id])
                    progress.update(task, advance=1)
                    if ok and apply_mode and not mgr.is_installed(pkg_id):
                        outcomes.append(PackageOutcome(
                            pkg_name, pkg_id, mgr.name, action, PackageStatus.FAILED,
                            message="post-install verify failed",
                        ))
                        print_error(f"Installed {pkg_name} but verify failed (not detected as installed)")
                        if fail_fast:
                            stopped_early = True
                            print_warning("Fail-fast: stopping after verify failure.")
                            break
                        continue
                    if ok:
                        outcomes.append(PackageOutcome(
                            pkg_name, pkg_id, mgr.name, action, PackageStatus.OK,
                        ))
                        if action == "reinstall":
                            print_success(f"Reinstalled {pkg_name}")
                        else:
                            print_success(f"Installed {pkg_name}")
                    else:
                        outcomes.append(PackageOutcome(
                            pkg_name, pkg_id, mgr.name, action, PackageStatus.FAILED,
                        ))
                        print_error(f"Failed to {action} {pkg_name}")
                        if fail_fast:
                            stopped_early = True
                            print_warning("Fail-fast: stopping after install failure.")
                            break

    success_count = sum(
        1 for o in outcomes
        if o.status == PackageStatus.OK and o.action == "install"
    )
    reinstalled_count = sum(
        1 for o in outcomes
        if o.status == PackageStatus.OK and o.action == "reinstall"
    )
    updated_count = sum(
        1 for o in outcomes
        if o.status == PackageStatus.OK and o.action == "update"
    )
    fail_count = sum(1 for o in outcomes if o.status == PackageStatus.FAILED)
    skip_count = sum(1 for o in outcomes if o.status == PackageStatus.SKIPPED)
    changed_count = success_count + reinstalled_count + updated_count

    console.print()
    if packages_to_skip or skip_count:
        print_info(f"Skipped {max(len(packages_to_skip), skip_count)} already installed package(s)")
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
    if stopped_early:
        print_warning("Remaining packages were not attempted (--fail-fast).")

    return InstallRunResult(
        ok=fail_count == 0,
        outcomes=outcomes,
        changed=changed_count,
        skipped=skip_count,
        failed=fail_count,
    )



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
                if result.back:
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


@cli.command("list")
def list_sets():
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
                mgr_info = "-"
            
            rows.append([set_name, description, str(package_count), os_compat, mgr_info])
    
    print_table(
        "Available Sets",
        ["Name", "Description", "Packages", "OS", "Managers"],
        rows
    )
    
    console.print()
    from blacksmith.utils.ui import os_legend_text
    print_info(os_legend_text())


@cli.command()
@click.argument("set_name", required=False)
@click.option("--file", "-f", "config_file", help="Path to custom config file")
@click.option("--skip-installed", "-s", is_flag=True, help="Skip already installed packages")
@click.option("--prefer", "-p", "prefer_manager", help="Prefer specific package manager (overrides config)")
@click.option("--force", is_flag=True, help="Force installation even if OS doesn't match target_os")
@click.option("--yes", "-y", "assume_yes", is_flag=True, help="Skip confirmation prompts (required for non-interactive custom --file installs)")
@click.option("--dry-run", is_flag=True, help="Show what would be installed without making changes")
@click.option("--fail-fast", is_flag=True, help="Stop after the first install/update failure (default: continue best-effort)")
def install(
    set_name: Optional[str],
    config_file: Optional[str],
    skip_installed: bool,
    prefer_manager: Optional[str],
    force: bool,
    assume_yes: bool,
    dry_run: bool,
    fail_fast: bool,
):
    """Install tools from a pre-made set or custom config file."""
    config = None
    config_source = None
    
    if config_file:
        # Load custom config
        config = load_custom_config(config_file)
        if not config:
            print_error(f"Failed to load config file: {config_file}")
            sys.exit(1)
        config_source = str(config_file)
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
    result = install_packages(
        config,
        skip_installed=skip_installed,
        prefer_manager=prefer_manager,
        force=force,
        assume_yes=assume_yes,
        dry_run=dry_run,
        config_source=config_source,
        fail_fast=fail_fast,
    )
    sys.exit(result.exit_code_install())


@cli.command()
@click.argument("set_name", required=False)
@click.option("--file", "-f", "config_file", help="Path to custom config file")
@click.option("--prefer", "-p", "prefer_manager", help="Prefer specific package manager (overrides config)")
@click.option("--force", is_flag=True, help="Force apply even if OS doesn't match target_os")
@click.option("--yes", "-y", "assume_yes", is_flag=True, help="Skip confirmation prompts (required for non-interactive custom --file applies)")
@click.option("--dry-run", is_flag=True, help="Show what would change without making changes")
@click.option("--fail-fast", is_flag=True, help="Stop after the first install/verify failure (default: continue best-effort)")
def apply(
    set_name: Optional[str],
    config_file: Optional[str],
    prefer_manager: Optional[str],
    force: bool,
    assume_yes: bool,
    dry_run: bool,
    fail_fast: bool,
):
    """Ensure a set matches desired state (idempotent).

    Skips already-installed packages, installs missing ones, verifies after install.
    Exit codes: 0 already compliant, 2 changed with no failures, 1 failures.
    """
    config = None
    config_source = None

    if config_file:
        config = load_custom_config(config_file)
        if not config:
            print_error(f"Failed to load config file: {config_file}")
            sys.exit(1)
        config_source = str(config_file)
    elif set_name:
        config = load_set(set_name)
        if not config:
            print_error(f"Set '{set_name}' not found.")
            print_info("Use 'blacksmith list' to see available sets.")
            sys.exit(1)
    else:
        show_welcome()
        selected = show_sets_menu()
        if not selected:
            return
        config = load_set(selected)
        if not config:
            print_error(f"Failed to load set: {selected}")
            sys.exit(1)

    result = install_packages(
        config,
        skip_installed=True,
        prefer_manager=prefer_manager,
        force=force,
        assume_yes=assume_yes,
        dry_run=dry_run,
        config_source=config_source,
        fail_fast=fail_fast,
        apply_mode=True,
    )
    sys.exit(result.exit_code_apply())


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

    from blacksmith.utils.identifiers import validate_search_query

    query_ok, query_error = validate_search_query(query)
    if not query_ok:
        print_error(query_error or "Invalid search query")
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
            'flatpak': 'flatpak',
            'brew': 'brew',
            'homebrew': 'brew',
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
            macos_managers = ['brew', 'homebrew']
            current_os = detect_os().lower()
            
            if canonical_name in linux_managers and current_os != 'linux':
                print_error(f"Package manager '{manager}' is only available on Linux.")
                print_info(f"You are currently on {current_os.capitalize()}.")
            elif canonical_name in windows_managers and current_os != 'windows':
                print_error(f"Package manager '{manager}' is only available on Windows.")
                print_info(f"You are currently on {current_os.capitalize()}.")
            elif canonical_name in macos_managers and current_os != 'darwin':
                print_error(f"Package manager '{manager}' is only available on macOS.")
                print_info(f"You are currently on {current_os.capitalize()}.")
            else:
                print_error(f"Package manager '{manager}' not found.")
            
            print_info(f"Available managers on your system: {', '.join([m.name for m in detect_available_managers()])}")
            return
    
    print_info(f"Searching for '{query}'...")
    console.print()
    
    all_results = []
    searched_without_search = []
    for mgr in available_managers:
        results = mgr.search(query, limit=limit)
        if results:
            all_results.append((mgr.name, results))
        elif mgr.name in ("snap", "flatpak"):
            searched_without_search.append(mgr.name)

    if not all_results:
        print_warning(f"No packages found for '{query}'")
        if searched_without_search:
            print_info(
                "Note: Snap and Flatpak search are not implemented yet "
                f"(queried: {', '.join(searched_without_search)})."
            )
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

    if searched_without_search:
        print_info(
            "Note: Snap/Flatpak search is not implemented; "
            f"skipped meaningful results for: {', '.join(searched_without_search)}"
        )


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
            questionary.Choice("Windows", "windows"),
            questionary.Choice("Linux", "linux"),
            questionary.Choice("macOS", "macos"),
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
        elif target_os_selection == "macos":
            os_managers = ["brew"]
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
            questionary.Choice("Windows only", "windows"),
            questionary.Choice("Linux only", "linux"),
            questionary.Choice("macOS only", "macos"),
            questionary.Choice("Windows and Linux (cross-platform)", "both"),
            questionary.Choice("Windows, Linux, and macOS", "all"),
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
        elif target_os_selection == "all":
            target_os_list = ["windows", "linux", "macos"]
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
            elif os_name == "macos":
                os_managers = ["brew"]
            
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
def uninstall(yes):
    """Uninstall Blacksmith itself."""
    import os
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    from rich.prompt import Confirm

    from blacksmith.utils.deferred_delete import (
        remove_file_now,
        remove_venv_now,
        schedule_delete_file,
        schedule_delete_venv,
        schedule_pip_uninstall,
        sibling_pip_uninstall_cmds,
        try_unlock_windows_executable,
    )
    from blacksmith.utils.pipx import pipx_package_name, should_use_pipx_uninstall
    from blacksmith.utils.safe_paths import (
        assert_safe_blacksmith_executable,
        assert_safe_blacksmith_venv,
        expected_venv_path,
    )

    console.print("\n[bold red]Uninstalling Blacksmith[/bold red]\n")
    
    if not yes:
        if not Confirm.ask("Are you sure you want to uninstall Blacksmith?", default=False):
            console.print("[yellow]Uninstall cancelled.[/yellow]")
            return
    
    blacksmith_path = None
    try:
        blacksmith_path = shutil.which("blacksmith")
        if not blacksmith_path:
            try:
                import blacksmith
                module_file = Path(blacksmith.__file__).resolve()
                if module_file.exists():
                    bin_dirs = [
                        Path(sys.executable).parent,
                        Path.home() / ".local" / "bin",
                        Path("/usr/local/bin"),
                    ]
                    for bin_dir in bin_dirs:
                        potential = bin_dir / "blacksmith"
                        if potential.exists():
                            blacksmith_path = str(potential)
                            break
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Could not find blacksmith executable: {e}")
    
    python_exe = sys.executable
    is_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    
    if is_venv:
        try:
            import blacksmith
            module_file = Path(blacksmith.__file__).resolve()
            expected_venv = expected_venv_path()
            if (
                str(expected_venv) in str(module_file)
                or str(module_file).startswith(str(expected_venv))
            ):
                python_exe = str(expected_venv / ("Scripts" if os.name == "nt" else "bin") / "python")
                if not Path(python_exe).exists():
                    python_exe = sys.executable
        except Exception:
            pass
    
    console.print(f"[dim]Found Blacksmith at: {blacksmith_path or 'unknown'}[/dim]")
    console.print(f"[dim]Using Python: {python_exe}[/dim]\n")

    # Prefer pipx when this process or the resolved entry point is pipx-managed.
    if should_use_pipx_uninstall(prefix=sys.prefix, executable=blacksmith_path):
        pipx_bin = shutil.which("pipx")
        pkg = pipx_package_name(sys.prefix) or "jdi-blacksmith"
        if pipx_bin:
            console.print(f"[dim]Detected pipx install; trying: pipx uninstall {pkg}...[/dim]")
            try:
                result = subprocess.run(
                    [pipx_bin, "uninstall", pkg],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    console.print("[green][OK][/green] Successfully uninstalled via pipx")
                    console.print("\n[bold green]Blacksmith has been uninstalled.[/bold green]")
                    console.print(
                        "[dim]You may need to restart your terminal for PATH changes to take effect.[/dim]"
                    )
                    return
                # Retry canonical PyPI name if venv folder name differed
                if pkg != "jdi-blacksmith":
                    retry = subprocess.run(
                        [pipx_bin, "uninstall", "jdi-blacksmith"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    if retry.returncode == 0:
                        console.print("[green][OK][/green] Successfully uninstalled via pipx")
                        console.print("\n[bold green]Blacksmith has been uninstalled.[/bold green]")
                        console.print(
                            "[dim]You may need to restart your terminal for PATH changes to take effect.[/dim]"
                        )
                        return
                err = (result.stderr or result.stdout or "").strip()
                if err:
                    logger.debug(f"pipx uninstall failed: {err[:200]}")
                print_warning("pipx uninstall failed; falling back to pip methods.")
            except subprocess.TimeoutExpired:
                print_warning("pipx uninstall timed out; falling back to pip methods.")
            except Exception as e:
                logger.debug(f"pipx uninstall raised: {e}")
                print_warning("pipx uninstall failed; falling back to pip methods.")
        else:
            print_warning(
                "pipx install detected but `pipx` is not on PATH; "
                "falling back to pip methods (prefer: pipx uninstall jdi-blacksmith)."
            )

    # Windows: rename running blacksmith.exe so pip can remove/replace it.
    unlocked_backup = None
    if os.name == "nt" and blacksmith_path:
        unlocked_backup = try_unlock_windows_executable(blacksmith_path)
        if unlocked_backup is not None:
            print_info("Unlocked Windows entry point for uninstall (renamed temporarily).")
    
    uninstall_methods = []

    for cmd in sibling_pip_uninstall_cmds(blacksmith_path):
        uninstall_methods.append((f"sibling pip ({cmd[0]})", cmd))
    
    uninstall_methods.append((
        "pip uninstall jdi-blacksmith",
        [python_exe, "-m", "pip", "uninstall", "jdi-blacksmith", "-y"]
    ))
    
    uninstall_methods.append((
        "pip uninstall --user jdi-blacksmith",
        [python_exe, "-m", "pip", "uninstall", "--user", "jdi-blacksmith", "-y"]
    ))
    
    uninstall_methods.append((
        "pip uninstall blacksmith",
        [python_exe, "-m", "pip", "uninstall", "blacksmith", "-y"]
    ))
    
    if blacksmith_path:
        try:
            blacksmith_file = Path(blacksmith_path)
            # After unlock rename, original path may be gone; use backup parent Scripts
            probe = blacksmith_file if blacksmith_file.exists() else (
                unlocked_backup if unlocked_backup is not None else blacksmith_file
            )
            if probe is not None and Path(probe).exists():
                shebang_python = None
                try:
                    with open(probe, "r", encoding="utf-8", errors="ignore") as f:
                        first_line = f.readline().strip()
                        if first_line.startswith("#!"):
                            shebang_python = first_line[2:].strip()
                            if " " in shebang_python:
                                shebang_python = shebang_python.split()[0]
                except Exception:
                    pass
                
                if shebang_python and Path(shebang_python).exists():
                    uninstall_methods.insert(0, (
                        f"pip uninstall via shebang Python ({shebang_python})",
                        [shebang_python, "-m", "pip", "uninstall", "jdi-blacksmith", "-y"]
                    ))
                
                scripts_dir = Path(probe).parent
                if scripts_dir.name in ("Scripts", "bin"):
                    venv_python = scripts_dir / ("python.exe" if os.name == "nt" else "python")
                    if venv_python.exists():
                        uninstall_methods.insert(0, (
                            f"pip uninstall via venv Python ({venv_python})",
                            [str(venv_python), "-m", "pip", "uninstall", "jdi-blacksmith", "-y"]
                        ))
        except Exception as e:
            logger.debug(f"Could not analyze blacksmith executable: {e}")

    last_error = None
    for method_name, cmd in uninstall_methods:
        try:
            console.print(f"[dim]Trying: {method_name}...[/dim]")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                console.print(f"[green][OK][/green] Successfully uninstalled via {method_name}")
                if unlocked_backup is not None and unlocked_backup.exists():
                    try:
                        unlocked_backup.unlink()
                    except OSError:
                        schedule_delete_file(unlocked_backup)
                
                # Clean up known Blacksmith venv only after path safety checks.
                venv_path = expected_venv_path()
                try:
                    assert_safe_blacksmith_venv(venv_path)
                except ValueError as exc:
                    print_warning(f"Skipping venv cleanup: {exc}")
                    venv_path = None

                if venv_path is not None and venv_path.exists():
                    console.print(f"[dim]Removing virtual environment: {venv_path}[/dim]")
                    try:
                        remove_venv_now(venv_path)
                        console.print("[green][OK][/green] Virtual environment removed")
                    except Exception as e:
                        logger.debug(f"Could not remove venv immediately: {e}")
                        if schedule_delete_venv(venv_path):
                            console.print(
                                "[yellow]Virtual environment will be removed after process exits[/yellow]"
                            )
                        else:
                            print_warning(f"Could not remove virtual environment: {venv_path}")
                            print_info(f"You may need to manually delete: {venv_path}")
                
                # Remove executable only if it resolves under an approved parent.
                for candidate in (blacksmith_path, str(unlocked_backup) if unlocked_backup else None):
                    if not candidate:
                        continue
                    try:
                        blacksmith_file = assert_safe_blacksmith_executable(candidate)
                    except ValueError as exc:
                        print_warning(f"Skipping executable cleanup: {exc}")
                        continue

                    if blacksmith_file is not None and blacksmith_file.exists():
                        console.print(f"[dim]Removing executable: {blacksmith_file}[/dim]")
                        try:
                            remove_file_now(blacksmith_file)
                            console.print("[green][OK][/green] Executable removed")
                        except Exception as e:
                            logger.debug(f"Could not remove executable immediately: {e}")
                            if schedule_delete_file(blacksmith_file):
                                console.print(
                                    "[yellow]Executable will be removed after process exits[/yellow]"
                                )
                            else:
                                print_warning(f"Could not remove executable: {blacksmith_file}")
                                print_info(f"You may need to manually delete: {blacksmith_file}")
                
                console.print("\n[bold green]Blacksmith has been uninstalled.[/bold green]")
                console.print("[dim]You may need to restart your terminal for PATH changes to take effect.[/dim]")
                return
            else:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                if error_msg:
                    last_error = error_msg
                    logger.debug(f"Method {method_name} failed: {error_msg[:200]}")
                continue
                
        except subprocess.TimeoutExpired:
            print_warning(f"Uninstall method {method_name} timed out.")
            continue
        except Exception as e:
            logger.debug(f"Uninstall method {method_name} raised exception: {e}")
            continue

    # Last resort on Windows: finish uninstall after this process exits (file lock).
    deferred_cmd = None
    sibling_cmds = sibling_pip_uninstall_cmds(
        unlocked_backup or blacksmith_path
    )
    if sibling_cmds:
        deferred_cmd = sibling_cmds[0]
    else:
        deferred_cmd = [python_exe, "-m", "pip", "uninstall", "jdi-blacksmith", "-y"]
    if schedule_pip_uninstall(deferred_cmd):
        console.print(
            "[yellow]In-process uninstall failed (often because blacksmith.exe is locked).[/yellow]"
        )
        console.print(
            "[green]Scheduled pip uninstall to run after this process exits.[/green]"
        )
        console.print(
            "[dim]Close this terminal or wait a few seconds, then confirm with "
            "`blacksmith --version` (should be missing).[/dim]"
        )
        return

    if unlocked_backup is not None and unlocked_backup.exists() and blacksmith_path:
        # Restore entry point if we renamed but could not uninstall
        try:
            if not Path(blacksmith_path).exists():
                unlocked_backup.rename(blacksmith_path)
        except OSError:
            pass
    
    print_error("Could not automatically uninstall Blacksmith.")
    if last_error:
        print_info(f"Last pip error: {last_error[:300]}")
    print_info("You may need to manually remove it:")
    print_info(f"  - Remove the command: {blacksmith_path}")
    print_info("  - If installed with pipx: pipx uninstall jdi-blacksmith")
    print_info(f"  - Run: {python_exe} -m pip uninstall jdi-blacksmith")
    print_info("  - Or: pip uninstall jdi-blacksmith")
    print_info("  - Or: pip uninstall --user jdi-blacksmith")
    print_info("  - If installed from source: pip uninstall blacksmith")
    
    if blacksmith_path:
        print_info("\nTroubleshooting:")
        print_info(f"  - Python executable: {python_exe}")
        print_info(f"  - Blacksmith path: {blacksmith_path}")
        print_info("  - Try running the pip or pipx command from a new terminal (not via blacksmith uninstall)")



def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()

