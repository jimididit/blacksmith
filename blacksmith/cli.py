"""Main CLI interface for Blacksmith."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

import click
import questionary
from rich.console import Console
from rich.table import Table

from blacksmith import __version__
from blacksmith.audit.log import record_audit
from blacksmith.config.loader import load_custom_config, load_set, list_available_sets
from blacksmith.config.validator import validate_and_report
from blacksmith.json_out import (
    JSON_COMMANDS,
    emit_error,
    emit_ok,
    is_json_mode,
    run_result_data,
)
from blacksmith.package_managers.detector import detect_available_managers, find_manager_for_package
from blacksmith.utils.cli_examples import examples_epilog
from blacksmith.package_managers.results import (
    InstallRunResult,
    PackageOutcome,
    PackageStatus,
)
from blacksmith.trust.fetch import FetchError, cleanup_fetched, fetch_set_url
from blacksmith.trust.scan import scan_set
from blacksmith.trust.sign import sign_set
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
    
    # Lame asf ASCII art for blacksmith (lowercase)
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


@dataclass
class PlanEntry:
    """One package as the runner intends to handle it."""

    package_name: str
    package_id: str
    manager: Optional[Any]
    action: str  # install | skip | unavailable
    manager_options: int = 0
    message: Optional[str] = None


def build_install_plan(
    config: dict,
    available_managers: List[Any],
    preferences: Optional[object] = None,
    check_installed: bool = True,
) -> List[PlanEntry]:
    """Resolve each package to a manager and the action it would get.

    ``check_installed`` calls into the managers, so leave it off when the caller
    only needs the manager mapping.
    """
    from blacksmith.utils.identifiers import validate_package_id
    from blacksmith.utils.package_ref import parse_package_ref, versions_equal

    managers_supported = config.get("managers_supported")
    plan: List[PlanEntry] = []

    for pkg in config.get("packages", []):
        pkg_name = pkg.get("name", "Unknown")
        options = len(pkg.get("managers", {}))
        manager_info = find_manager_for_package(
            pkg,
            available_managers,
            preferred_order=preferences,
            managers_supported=managers_supported,
        )
        if not manager_info:
            plan.append(
                PlanEntry(pkg_name, "", None, "unavailable", options, "no compatible manager")
            )
            continue

        mgr, pkg_id = manager_info
        id_ok, id_error = validate_package_id(pkg_id)
        if not id_ok:
            plan.append(
                PlanEntry(
                    pkg_name, pkg_id, mgr, "unavailable", options,
                    id_error or "unsafe package ID",
                )
            )
            continue

        name, version = parse_package_ref(pkg_id)

        if version and not mgr.supports_version_pins():
            plan.append(
                PlanEntry(pkg_name, pkg_id, mgr, "unavailable", options, "pin_unsupported")
            )
            continue

        if check_installed:
            if version:
                try:
                    installed_ver = mgr.get_installed_version(name)
                except Exception:
                    installed_ver = None
                if installed_ver is None:
                    # Distinguish not installed vs unknown
                    try:
                        present = mgr.is_installed(name)
                    except Exception:
                        present = False
                    if present:
                        plan.append(
                            PlanEntry(pkg_name, pkg_id, mgr, "unavailable", options, "version_unknown")
                        )
                    else:
                        plan.append(PlanEntry(pkg_name, pkg_id, mgr, "install", options))
                elif versions_equal(installed_ver, version):
                    plan.append(
                        PlanEntry(pkg_name, pkg_id, mgr, "skip", options, "already installed")
                    )
                else:
                    plan.append(
                        PlanEntry(pkg_name, pkg_id, mgr, "unavailable", options, "version_mismatch")
                    )
            else:
                # Unpinned: existing is_installed(name) path
                try:
                    already = mgr.is_installed(name)
                except Exception:
                    already = False
                if already:
                    plan.append(
                        PlanEntry(pkg_name, pkg_id, mgr, "skip", options, "already installed")
                    )
                else:
                    plan.append(PlanEntry(pkg_name, pkg_id, mgr, "install", options))
        else:
            plan.append(PlanEntry(pkg_name, pkg_id, mgr, "install", options))

    return plan


def dry_run_result(plan: List[PlanEntry]) -> InstallRunResult:
    """Turn a plan into the run result a dry run reports."""
    status_for = {
        "install": PackageStatus.OK,
        "skip": PackageStatus.SKIPPED,
        "unavailable": PackageStatus.FAILED,
    }
    outcomes = [
        PackageOutcome(
            entry.package_name,
            entry.package_id,
            entry.manager.name if entry.manager else "none",
            entry.action,
            status_for[entry.action],
            message=entry.message or "planned",
        )
        for entry in plan
    ]
    return InstallRunResult(
        ok=all(entry.action != "unavailable" for entry in plan),
        outcomes=outcomes,
        changed=sum(1 for entry in plan if entry.action == "install"),
        skipped=sum(1 for entry in plan if entry.action == "skip"),
        failed=sum(1 for entry in plan if entry.action == "unavailable"),
        dry_run=True,
    )


def show_installation_summary(
    config: dict,
    available_managers: List[Any],
    preferences: Optional[object] = None,
    assume_yes: bool = False,
    dry_run: bool = False,
    config_source: Optional[str] = None,
    plan: Optional[List[PlanEntry]] = None,
):
    """Show what will be installed before confirmation."""
    if config_source:
        if config_source.startswith("https://"):
            print_warning(
                "REMOTE set. Installing from a URL. Treat third-party YAML as untrusted "
                "until you have reviewed every package ID below."
            )
        else:
            print_warning(
                "Installing from a custom config file. Treat third-party YAML as untrusted "
                "until you have reviewed every package ID below."
            )
        print_info(f"Config source: {config_source}")
        console.print()
    
    if plan is None:
        plan = build_install_plan(
            config, available_managers, preferences, check_installed=dry_run
        )

    rows = []
    plan_lines = []
    for entry in plan:
        pkg_name = entry.package_name
        if entry.manager and entry.action != "unavailable":
            manager_display = f"[bold #44FFD1]{entry.manager.name}[/bold #44FFD1]: {entry.package_id}"
            if entry.manager_options > 1:
                manager_display += f" [dim](selected from {entry.manager_options} options)[/dim]"

            if dry_run:
                action = "skip (already installed)" if entry.action == "skip" else "install"
                rows.append([pkg_name, manager_display, action])
                plan_lines.append(
                    f"{action}: {pkg_name} via {entry.manager.name} ({entry.package_id})"
                )
            else:
                rows.append([pkg_name, manager_display])
        else:
            reason = entry.message or "no compatible manager"
            if dry_run:
                rows.append([pkg_name, f"[bold red]{reason}[/bold red]", "unavailable"])
                plan_lines.append(f"unavailable: {pkg_name} ({reason})")
            else:
                rows.append([pkg_name, "[bold red][ERR] No compatible manager found[/bold red]"])
    
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
    from blacksmith.utils.identifiers import validate_package_id
    from blacksmith.utils.os_detector import detect_os
    from blacksmith.utils.package_ref import parse_package_ref, versions_equal
    from blacksmith.utils.tty import require_tty_or_yes

    tty_ok, tty_error = require_tty_or_yes(assume_yes, dry_run=dry_run)
    if not tty_ok:
        message = tty_error or "Non-interactive session requires --yes or --dry-run."
        print_error(message)
        return InstallRunResult(ok=False, message=message)

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
                return InstallRunResult(
                    ok=False,
                    message=(
                        f"OS mismatch: set targets {', '.join(target_os_list)}, "
                        f"current OS is {current_os}. Use --force to install anyway."
                    ),
                )
            else:
                print_warning(f"Installing set for {', '.join(target_os_list)} on {current_os.capitalize()} (--force enabled)")
    
    available_managers = detect_available_managers()
    
    if not available_managers:
        message = "No package managers detected on this system."
        print_error(message)
        return InstallRunResult(ok=False, message=message)
    
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
    
    # A dry run resolves the same plan the summary table renders, so build it once.
    plan = (
        build_install_plan(config, available_managers, preferences)
        if dry_run
        else None
    )

    # Show summary and get confirmation (if requested)
    if show_summary:
        confirmation = show_installation_summary(
            config,
            available_managers,
            preferences,
            assume_yes=assume_yes,
            dry_run=dry_run,
            config_source=config_source,
            plan=plan,
        )
        if confirmation == "back":
            return InstallRunResult(ok=True, back=True)
        if confirmation != "dry_run" and not confirmation:
            print_info("Installation cancelled.")
            return InstallRunResult(ok=False, cancelled=True)
    
    if dry_run:
        if not show_summary:
            print_info("Dry-run only. No packages will be installed.")
        return dry_run_result(plan)
    
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
            outcomes.append(PackageOutcome(
                pkg_name, pkg_id, mgr.name, "install", PackageStatus.FAILED,
                message=id_error or "unsafe package ID",
            ))
            continue

        pkg_managers = pkg.get("managers", {})
        all_pkg_managers = [*pkg_managers]
        if len(all_pkg_managers) > 1:
            print_info(f"{pkg_name}: Using {mgr.name} (preferred from available: {', '.join(all_pkg_managers)})")

        name, version = parse_package_ref(pkg_id)

        # Check for pin support
        if version and not mgr.supports_version_pins():
            print_error(f"{pkg_name}: {mgr.name} does not support version pins")
            not_found.append(pkg_name)
            outcomes.append(PackageOutcome(
                pkg_name, pkg_id, mgr.name, "install", PackageStatus.FAILED,
                message="pin_unsupported",
            ))
            continue

        # Handle pinned packages
        if version:
            try:
                # For brew, query versioned formula if pin is set
                query_id = name
                if mgr.name.lower() == "brew":
                    query_id = f"{name}@{version}"
                installed_ver = mgr.get_installed_version(query_id)
            except Exception:
                installed_ver = None

            if installed_ver is None:
                # Distinguish not installed vs unknown
                try:
                    present = mgr.is_installed(name)
                except Exception:
                    present = False
                if present:
                    print_error(f"{pkg_name}: installed but version unknown")
                    not_found.append(pkg_name)
                    outcomes.append(PackageOutcome(
                        pkg_name, pkg_id, mgr.name, "install", PackageStatus.FAILED,
                        message="version_unknown",
                    ))
                    continue
                else:
                    # Not installed, proceed with install
                    packages_to_install.append((pkg_name, pkg_id, mgr, "install"))
            elif versions_equal(installed_ver, version):
                # Version matches, skip
                packages_to_skip.append(pkg_name)
                outcomes.append(PackageOutcome(
                    pkg_name, pkg_id, mgr.name, "skip", PackageStatus.SKIPPED,
                    message="already installed",
                ))
                print_info(f"Skip: {pkg_name} (version {version} already installed)")
            else:
                # Version mismatch
                print_error(f"{pkg_name}: version mismatch (installed: {installed_ver}, required: {version})")
                not_found.append(pkg_name)
                outcomes.append(PackageOutcome(
                    pkg_name, pkg_id, mgr.name, "install", PackageStatus.FAILED,
                    message="version_mismatch",
                ))
                continue
        # Unpinned packages: existing logic
        elif mgr.is_installed(name):
            if auto_skip:
                packages_to_skip.append(pkg_name)
                outcomes.append(PackageOutcome(
                    pkg_name, pkg_id, mgr.name, "skip", PackageStatus.SKIPPED,
                    message="already installed",
                ))
                print_info(f"Skip: {pkg_name} (already installed)")
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
                    print_info(f"Skip: {pkg_name}")
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
                    
                    # Post-install verification
                    if ok:
                        name, version = parse_package_ref(pkg_id)
                        verify_failed = False
                        verify_message = "post-install verify failed"
                        
                        # Apply mode or pins: verify after install (intentional fail-closed)
                        if apply_mode or version:
                            # For pinned packages, verify version match
                            if version:
                                try:
                                    # For brew, query versioned formula if pin is set
                                    query_id = name
                                    if mgr.name.lower() == "brew":
                                        query_id = f"{name}@{version}"
                                    installed_ver = mgr.get_installed_version(query_id)
                                except Exception:
                                    installed_ver = None
                                
                                if installed_ver is None:
                                    verify_failed = True
                                    verify_message = "version_unknown"
                                elif not versions_equal(installed_ver, version):
                                    verify_failed = True
                                    verify_message = "version_mismatch"
                            # For apply_mode on unpinned, check basic presence
                            elif apply_mode and not mgr.is_installed(name):
                                verify_failed = True
                        
                        if verify_failed:
                            outcomes.append(PackageOutcome(
                                pkg_name, pkg_id, mgr.name, action, PackageStatus.FAILED,
                                message=verify_message,
                            ))
                            print_error(f"Installed {pkg_name} but verify failed: {verify_message}")
                            if fail_fast:
                                stopped_early = True
                                print_warning("Fail-fast: stopping after verify failure.")
                                break
                            continue
                        
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


def _record_audit_fail_open(**kwargs) -> None:
    """Audit writes must never change the exit code of a mutate command."""
    try:
        record_audit(warn=print_warning, **kwargs)
    except Exception as exc:
        print_warning(f"Audit log write failed: {exc}")


def maybe_record_install_audit(
    *,
    command: str,
    result: InstallRunResult,
    exit_code: int,
    config: Optional[dict],
    config_source: Optional[str],
    dry_run: bool,
    no_audit: bool,
    config_hash: Optional[str] = None,
) -> None:
    """Append audit lines for a finished install/apply run."""
    _record_audit_fail_open(
        command=command,
        outcomes=result.outcomes,
        exit_code=exit_code,
        set_name=config.get("name") if config else None,
        config_path=config_source,
        config_hash=config_hash,
        dry_run=dry_run,
        no_audit=no_audit,
    )


def record_self_uninstall_audit(
    *,
    manager: str,
    status: PackageStatus,
    exit_code: int,
    no_audit: bool,
    package: str = "jdi-blacksmith",
) -> None:
    """Append audit lines for an attempted self-uninstall."""
    _record_audit_fail_open(
        command="uninstall",
        outcomes=[
            PackageOutcome(
                package,
                package,
                manager,
                "uninstall",
                status,
            )
        ],
        exit_code=exit_code,
        no_audit=no_audit,
    )


def reject_json_if_unsupported(ctx: click.Context, command_name: str) -> None:
    """Exit with a stable JSON error when a command lacks JSON support."""
    if not is_json_mode(ctx) or command_name in JSON_COMMANDS:
        return
    emit_error(
        command=command_name,
        exit_code=2,
        code="json_unsupported",
        message=f"JSON output is not supported for '{command_name}' in this version.",
    )
    sys.exit(2)


def emit_json_run_error(
    command: str,
    exit_code: int,
    code: str,
    message: str,
    data: Optional[dict] = None,
) -> None:
    """Emit a JSON error envelope for install/apply, then exit."""
    emit_error(
        command=command, exit_code=exit_code, code=code, message=message, data=data
    )
    sys.exit(exit_code)


def require_managers_for_json(command: str) -> None:
    """No detected manager is a diagnosable state, like it is for search."""
    if detect_available_managers():
        return
    emit_json_run_error(
        command,
        1,
        "no_managers",
        "No package managers detected on this system.",
    )


def require_yes_for_json(command: str, assume_yes: bool, dry_run: bool) -> None:
    """--json never prompts, so a mutate run needs --yes (or --dry-run)."""
    if assume_yes or dry_run:
        return
    emit_json_run_error(
        command,
        2,
        "needs_args",
        f"'{command} --json' requires --yes (or --dry-run); prompts are disabled.",
    )


def apply_trust_scan(
    config: dict,
    *,
    command: str,
    json_mode: bool,
    strict_trust: bool,
    remote: bool,
) -> None:
    """Run offline trust heuristics on custom/remote sets.

    Always prints findings as warnings (never claims the set is safe). Fail closed
    when there are findings and ``strict_trust`` or ``remote`` is set.
    """
    result = scan_set(config)
    if result.ok:
        return

    from rich.markup import escape

    # Human mode: print findings. JSON mode: keep stdout clean (findings land in
    # the error envelope when escalate; warn-only JSON omits them by design).
    if not json_mode:
        for finding in result.findings:
            # Escape attacker-controlled strings and bracketed codes so rich does
            # not treat them as markup (MarkupError / stripped finding codes).
            print_warning(
                f"Trust scan {escape(f'[{finding.code}]')}: {escape(finding.message)}"
            )

    if not (strict_trust or remote):
        return

    reason = "--strict-trust" if strict_trust else "remote --url"
    message = (
        f"Trust scan failed with {len(result.findings)} finding(s); "
        f"refusing to proceed ({reason})."
    )
    findings_data = {
        "findings": [
            {"code": f.code, "message": f.message} for f in result.findings
        ]
    }
    if json_mode:
        emit_json_run_error(
            command, 1, "trust_scan_failed", message, data=findings_data
        )
    print_error(message)
    sys.exit(1)


def load_run_config(
    *,
    command: str,
    json_mode: bool,
    set_name: Optional[str],
    config_file: Optional[str],
    require_signature: bool,
    signature_file: Optional[str],
    pubkey_file: Optional[str],
    config_url: Optional[str] = None,
    strict_trust: bool = False,
):
    """Resolve the config for an install/apply run.

    Returns (config, config_source, config_hash, fetched), or None when the user
    leaves the set menu. ``fetched`` is a FetchedSet for --url (caller must
    cleanup_fetched). Exits the process on load, signature, or missing-argument
    failures.
    """
    from blacksmith.trust.verify import verify_set_signature

    if config_url:
        fetched = None
        try:
            fetched = fetch_set_url(
                config_url,
                signature_url_or_path=signature_file,
                fetch_sidecar=require_signature and not signature_file,
            )
        except FetchError as exc:
            code = getattr(exc, "code", None) or "fetch_failed"
            err_code = "invalid_url" if code == "invalid_url" else "fetch_failed"
            message = str(exc)
            if json_mode:
                emit_json_run_error(command, 1, err_code, message)
            print_error(message)
            sys.exit(1)

        if require_signature:
            extras = [Path(pubkey_file)] if pubkey_file else None
            verified = verify_set_signature(
                fetched.path,
                signature_path=fetched.signature_path,
                extra_pubkeys=extras,
            )
            if not verified.ok:
                cleanup_fetched(fetched)
                if json_mode:
                    emit_json_run_error(
                        command, 1, "signature_failed", verified.message
                    )
                print_error(verified.message)
                sys.exit(1)
            print_info(verified.message)

        config = load_custom_config(str(fetched.path))
        if not config:
            cleanup_fetched(fetched)
            message = f"Failed to load config from URL: {fetched.final_url}"
            if json_mode:
                emit_json_run_error(command, 1, "invalid_config", message)
            print_error(message)
            sys.exit(1)

        try:
            apply_trust_scan(
                config,
                command=command,
                json_mode=json_mode,
                strict_trust=strict_trust,
                remote=True,
            )
        except SystemExit:
            cleanup_fetched(fetched)
            raise

        source_label = f"{fetched.final_url} (sha256:{fetched.sha256[:12]}…)"
        return config, source_label, fetched.sha256, fetched

    if config_file:
        if require_signature:
            extras = [Path(pubkey_file)] if pubkey_file else None
            sig = Path(signature_file) if signature_file else None
            verified = verify_set_signature(
                Path(config_file),
                signature_path=sig,
                extra_pubkeys=extras,
            )
            if not verified.ok:
                if json_mode:
                    emit_json_run_error(command, 1, "signature_failed", verified.message)
                print_error(verified.message)
                sys.exit(1)
            print_info(verified.message)
        config = load_custom_config(config_file)
        if not config:
            message = f"Failed to load config file: {config_file}"
            if json_mode:
                emit_json_run_error(command, 1, "invalid_config", message)
            print_error(message)
            sys.exit(1)
        apply_trust_scan(
            config,
            command=command,
            json_mode=json_mode,
            strict_trust=strict_trust,
            remote=False,
        )
        return config, str(config_file), None, None

    if set_name:
        config = load_set(set_name)
        if not config:
            message = f"Set '{set_name}' not found."
            if json_mode:
                emit_json_run_error(command, 1, "not_found", message)
            print_error(message)
            print_info("Use 'blacksmith list' to see available sets.")
            sys.exit(1)
        return config, None, None, None

    if json_mode:
        emit_json_run_error(
            command,
            2,
            "needs_args",
            f"'{command} --json' needs a set name, --file, or --url; "
            "the set menu is disabled.",
        )
    show_welcome()
    selected = show_sets_menu()
    if not selected:
        return None
    config = load_set(selected)
    if not config:
        print_error(f"Failed to load set: {selected}")
        sys.exit(1)
    return config, None, None, None


def emit_json_run_result(
    *,
    command: str,
    result: InstallRunResult,
    exit_code: int,
    config: Optional[dict],
    config_source: Optional[str],
    dry_run: bool,
    apply_ok_exits: bool = False,
) -> None:
    """Emit the JSON envelope for a finished install/apply run, then exit."""
    data = run_result_data(
        dry_run=dry_run,
        set_name=config.get("name") if config else None,
        config_path=config_source,
        result=result,
    )

    if exit_code == 0 or (apply_ok_exits and exit_code == 2):
        emit_ok(
            command=command,
            exit_code=exit_code,
            data=data,
            apply_ok_exits=apply_ok_exits,
        )
        sys.exit(exit_code)

    if result.cancelled:
        emit_json_run_error(
            command,
            exit_code,
            "cancelled",
            f"{command} was cancelled before any package changed.",
            data=data,
        )

    failed_names = [
        outcome.package_name
        for outcome in result.outcomes
        if outcome.status == PackageStatus.FAILED
    ]
    if failed_names:
        message = (
            f"{command} failed for {len(failed_names)} package(s): "
            f"{', '.join(failed_names)}"
        )
    elif result.message:
        message = f"{command} did not run: {result.message}"
    else:
        message = (
            f"{command} did not run; re-run without --json to see the reason "
            "(stderr carries the human-readable diagnostics)."
        )
    emit_json_run_error(command, exit_code, "install_failed", message, data=data)


@click.group(
    invoke_without_command=True,
    epilog=examples_epilog(
        "blacksmith list",
        "blacksmith install minimal --yes",
        "blacksmith install --url https://example.com/set.yaml --dry-run",
        "blacksmith create",
    ),
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    help="Emit machine-readable JSON on stdout",
)
@click.version_option(version=__version__, prog_name="Blacksmith")
@click.pass_context
def cli(ctx: click.Context, json_mode: bool):
    """Blacksmith - Cross-platform development tool installer."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_mode
    # stdout carries the envelope only, so silence Rich for the whole run.
    console.quiet = json_mode

    # If no subcommand, show interactive menu
    if ctx.invoked_subcommand is None:
        if json_mode:
            emit_error(
                command="interactive",
                exit_code=2,
                code="json_unsupported",
                message=(
                    "Interactive menu is not available with --json; "
                    "pass a command such as list or install."
                ),
            )
            sys.exit(2)
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

                maybe_record_install_audit(
                    command="install",
                    result=result,
                    exit_code=result.exit_code_install(),
                    config=config,
                    config_source=None,
                    dry_run=False,
                    no_audit=False,
                )

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
        if not json_mode:
            show_banner()


@cli.command(
    "list",
    epilog=examples_epilog(
        "blacksmith list",
        "blacksmith --json list",
    ),
)
@click.pass_context
def list_sets(ctx: click.Context):
    """List available pre-made sets."""
    sets = list_available_sets()
    
    if not sets:
        if is_json_mode(ctx):
            emit_error(
                command="list",
                exit_code=1,
                code="not_found",
                message="No pre-made sets found.",
            )
            sys.exit(1)
        print_error("No pre-made sets found.")
        return

    if is_json_mode(ctx):
        set_data = []
        for set_name in sets:
            config = load_set(set_name)
            if config:
                set_data.append(
                    {
                        "name": set_name,
                        "description": config.get("description"),
                        "package_count": len(config.get("packages", [])),
                        "target_os": config.get("target_os") or [],
                        "managers_supported": config.get("managers_supported") or [],
                    }
                )
        emit_ok(command="list", exit_code=0, data={"sets": set_data})
        return

    from blacksmith.utils.os_detector import detect_os
    
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


@cli.command(
    "audit",
    epilog=examples_epilog(
        "blacksmith audit",
        "blacksmith audit --last 20",
    ),
)
@click.option(
    "--last",
    "last_n",
    default=50,
    show_default=True,
    type=int,
    help="Show last N events",
)
@click.pass_context
def audit_cmd(ctx: click.Context, last_n: int):
    """Show recent local audit log events."""
    reject_json_if_unsupported(ctx, "audit")
    from blacksmith.audit.read import default_audit_log_path, load_events

    log_path = default_audit_log_path()
    events, corrupt = load_events(path=log_path, last=last_n)
    if not events:
        console.print("[dim]No audit events yet.[/dim]")
        console.print(f"[dim]Log path: {log_path}[/dim]")
        if corrupt:
            print_warning(f"Skipped {corrupt} corrupt line(s).")
        return

    table = Table(title="Audit log")
    table.add_column("ts")
    table.add_column("type")
    table.add_column("command/action")
    table.add_column("name")
    table.add_column("manager")
    table.add_column("status/exit")
    table.add_column("user/set")
    for event in events:
        if event.get("type") == "run":
            table.add_row(
                str(event.get("ts", "")),
                "run",
                str(event.get("command", "")),
                "",
                "",
                str(event.get("exit", "")),
                f"{event.get('user') or ''}/{event.get('set') or ''}",
            )
        else:
            table.add_row(
                str(event.get("ts", "")),
                "package",
                str(event.get("action", "")),
                str(event.get("name") or event.get("id") or ""),
                str(event.get("manager", "")),
                str(event.get("status", "")),
                "",
            )
    console.print(table)
    console.print(f"[dim]Log path: {log_path}[/dim]")
    if corrupt:
        print_warning(f"Skipped {corrupt} corrupt line(s).")


@cli.command(
    epilog=examples_epilog(
        "blacksmith install minimal --yes",
        "blacksmith install --file ./my-set.yaml --yes --dry-run",
        "blacksmith install --url https://example.com/set.yaml --dry-run",
        "blacksmith install --file ./my-set.yaml --require-signature --yes",
    ),
)
@click.argument("set_name", required=False)
@click.option("--file", "-f", "config_file", help="Path to custom config file")
@click.option("--url", "config_url", help="HTTPS URL of a remote set YAML")
@click.option("--skip-installed", "-s", is_flag=True, help="Skip already installed packages")
@click.option("--prefer", "-p", "prefer_manager", help="Prefer specific package manager (overrides config)")
@click.option("--force", is_flag=True, help="Force installation even if OS doesn't match target_os")
@click.option("--yes", "-y", "assume_yes", is_flag=True, help="Skip confirmation prompts (required for non-interactive custom --file installs)")
@click.option("--dry-run", is_flag=True, help="Show what would be installed without making changes")
@click.option("--fail-fast", is_flag=True, help="Stop after the first install/update failure (default: continue best-effort)")
@click.option("--require-signature", is_flag=True, help="Require a valid minisign signature for --file or --url (fail closed)")
@click.option("--signature", "signature_file", type=click.Path(exists=False), help="Detached signature path or HTTPS URL (default: <file>.minisig or {url}.minisig)")
@click.option("--pubkey", "pubkey_file", type=click.Path(exists=True), help="Extra minisign public key for this run")
@click.option("--strict-trust", is_flag=True, help="Fail closed when trust-scan findings are present (default: warn for local --file)")
@click.option("--no-audit", is_flag=True, help="Do not write to the local audit log")
@click.pass_context
def install(
    ctx: click.Context,
    set_name: Optional[str],
    config_file: Optional[str],
    config_url: Optional[str],
    skip_installed: bool,
    prefer_manager: Optional[str],
    force: bool,
    assume_yes: bool,
    dry_run: bool,
    fail_fast: bool,
    require_signature: bool,
    signature_file: Optional[str],
    pubkey_file: Optional[str],
    strict_trust: bool,
    no_audit: bool,
):
    """Install tools from a pre-made set or custom config file."""
    json_mode = is_json_mode(ctx)

    source_count = sum(bool(x) for x in (set_name, config_file, config_url))
    if source_count > 1:
        message = "Provide exactly one of: set name, --file, or --url."
        if json_mode:
            emit_json_run_error("install", 2, "needs_args", message)
        print_error(message)
        sys.exit(2)

    if require_signature and not config_file and not config_url:
        message = "--require-signature only applies with --file or --url."
        if json_mode:
            emit_json_run_error("install", 2, "needs_args", message)
        print_error(message)
        sys.exit(1)

    fetched = None
    try:
        resolved = load_run_config(
            command="install",
            json_mode=json_mode,
            set_name=set_name,
            config_file=config_file,
            require_signature=require_signature,
            signature_file=signature_file,
            pubkey_file=pubkey_file,
            config_url=config_url,
            strict_trust=strict_trust,
        )
        if resolved is None:
            return
        config, config_source, config_hash, fetched = resolved

        if json_mode:
            require_yes_for_json("install", assume_yes, dry_run)
            require_managers_for_json("install")

        # Install packages
        result = install_packages(
            config,
            skip_installed=skip_installed,
            show_summary=not json_mode,
            prefer_manager=prefer_manager,
            force=force,
            assume_yes=assume_yes,
            dry_run=dry_run,
            config_source=config_source,
            fail_fast=fail_fast,
        )
        exit_code = result.exit_code_install()
        audit_path = fetched.final_url if fetched is not None else config_source
        maybe_record_install_audit(
            command="install",
            result=result,
            exit_code=exit_code,
            config=config,
            config_source=audit_path,
            dry_run=dry_run,
            no_audit=no_audit,
            config_hash=config_hash,
        )
        if json_mode:
            emit_json_run_result(
                command="install",
                result=result,
                exit_code=exit_code,
                config=config,
                config_source=config_source,
                dry_run=dry_run,
            )
        sys.exit(exit_code)
    finally:
        if fetched is not None:
            cleanup_fetched(fetched)


@cli.command(
    epilog=examples_epilog(
        "blacksmith apply minimal --yes",
        "blacksmith apply --file ./my-set.yaml --yes --dry-run",
        "blacksmith apply --url https://example.com/set.yaml --dry-run",
        "blacksmith apply --file ./my-set.yaml --strict-trust --yes",
    ),
)
@click.argument("set_name", required=False)
@click.option("--file", "-f", "config_file", help="Path to custom config file")
@click.option("--url", "config_url", help="HTTPS URL of a remote set YAML")
@click.option("--prefer", "-p", "prefer_manager", help="Prefer specific package manager (overrides config)")
@click.option("--force", is_flag=True, help="Force apply even if OS doesn't match target_os")
@click.option("--yes", "-y", "assume_yes", is_flag=True, help="Skip confirmation prompts (required for non-interactive custom --file applies)")
@click.option("--dry-run", is_flag=True, help="Show what would change without making changes")
@click.option("--fail-fast", is_flag=True, help="Stop after the first install/verify failure (default: continue best-effort)")
@click.option("--require-signature", is_flag=True, help="Require a valid minisign signature for --file or --url (fail closed)")
@click.option("--signature", "signature_file", type=click.Path(exists=False), help="Detached signature path or HTTPS URL (default: <file>.minisig or {url}.minisig)")
@click.option("--pubkey", "pubkey_file", type=click.Path(exists=True), help="Extra minisign public key for this run")
@click.option("--strict-trust", is_flag=True, help="Fail closed when trust-scan findings are present (default: warn for local --file)")
@click.option("--no-audit", is_flag=True, help="Do not write to the local audit log")
@click.pass_context
def apply(
    ctx: click.Context,
    set_name: Optional[str],
    config_file: Optional[str],
    config_url: Optional[str],
    prefer_manager: Optional[str],
    force: bool,
    assume_yes: bool,
    dry_run: bool,
    fail_fast: bool,
    require_signature: bool,
    signature_file: Optional[str],
    pubkey_file: Optional[str],
    strict_trust: bool,
    no_audit: bool,
):
    """Ensure a set matches desired state (idempotent).

    Skips already-installed packages, installs missing ones, verifies after install.
    Exit codes: 0 already compliant, 2 changed with no failures, 1 failures.
    """
    json_mode = is_json_mode(ctx)

    source_count = sum(bool(x) for x in (set_name, config_file, config_url))
    if source_count > 1:
        message = "Provide exactly one of: set name, --file, or --url."
        if json_mode:
            emit_json_run_error("apply", 2, "needs_args", message)
        print_error(message)
        sys.exit(2)

    if require_signature and not config_file and not config_url:
        message = "--require-signature only applies with --file or --url."
        if json_mode:
            emit_json_run_error("apply", 2, "needs_args", message)
        print_error(message)
        sys.exit(1)

    fetched = None
    try:
        resolved = load_run_config(
            command="apply",
            json_mode=json_mode,
            set_name=set_name,
            config_file=config_file,
            require_signature=require_signature,
            signature_file=signature_file,
            pubkey_file=pubkey_file,
            config_url=config_url,
            strict_trust=strict_trust,
        )
        if resolved is None:
            return
        config, config_source, config_hash, fetched = resolved

        if json_mode:
            require_yes_for_json("apply", assume_yes, dry_run)
            require_managers_for_json("apply")

        result = install_packages(
            config,
            skip_installed=True,
            show_summary=not json_mode,
            prefer_manager=prefer_manager,
            force=force,
            assume_yes=assume_yes,
            dry_run=dry_run,
            config_source=config_source,
            fail_fast=fail_fast,
            apply_mode=True,
        )
        exit_code = result.exit_code_apply()
        audit_path = fetched.final_url if fetched is not None else config_source
        maybe_record_install_audit(
            command="apply",
            result=result,
            exit_code=exit_code,
            config=config,
            config_source=audit_path,
            dry_run=dry_run,
            no_audit=no_audit,
            config_hash=config_hash,
        )
        if json_mode:
            emit_json_run_result(
                command="apply",
                result=result,
                exit_code=exit_code,
                config=config,
                config_source=config_source,
                dry_run=dry_run,
                apply_ok_exits=True,
            )
        sys.exit(exit_code)
    finally:
        if fetched is not None:
            cleanup_fetched(fetched)


@cli.command(
    epilog=examples_epilog(
        "blacksmith export minimal --format winget -o packages.json",
        "blacksmith export --file ./my-set.yaml --format apt -o packages.txt",
    ),
)
@click.argument("set_name", required=False)
@click.option("--file", "-f", "config_file", type=click.Path(exists=True), help="Path to custom config file")
@click.option("--format", "-F", "export_format", 
              type=click.Choice(["winget", "choco", "chocolatey", "apt", "pacman", "scoop"], case_sensitive=False),
              help="Export format: winget, choco/chocolatey, apt, pacman, or scoop")
@click.option("--output", "-o", "output_file", help="Output file path")
@click.pass_context
def export(ctx: click.Context, set_name: Optional[str], config_file: Optional[str], export_format: Optional[str], output_file: Optional[str]):
    """Export a set to native package manager format."""
    reject_json_if_unsupported(ctx, "export")
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


@cli.command(
    epilog=examples_epilog(
        "blacksmith info minimal",
        "blacksmith info --file ./my-set.yaml --limit 20 --no-pager",
        "blacksmith --json info development",
    ),
)
@click.argument("set_name", required=False)
@click.option("--file", "-f", "config_file", type=click.Path(exists=True), help="Path to custom config file")
@click.option(
    "--limit",
    "-l",
    "package_limit",
    type=int,
    default=0,
    show_default=True,
    help="Max packages to list in human output (0 = all). Ignored for --json.",
)
@click.option(
    "--pager/--no-pager",
    default=True,
    show_default=True,
    help="Page long package lists in a TTY (human mode only).",
)
@click.pass_context
def info(
    ctx: click.Context,
    set_name: Optional[str],
    config_file: Optional[str],
    package_limit: int,
    pager: bool,
):
    """Show detailed information about a set."""
    from blacksmith.config.loader import load_set, load_custom_config
    from blacksmith.utils.os_detector import detect_os

    json_mode = is_json_mode(ctx)
    if json_mode and not set_name and not config_file:
        emit_error(
            command="info",
            exit_code=2,
            code="needs_args",
            message="Provide a set name or --file.",
        )
        sys.exit(2)
    
    # Load config
    config = None
    if config_file:
        config = load_custom_config(config_file)
        if not config:
            if json_mode:
                emit_error(
                    command="info",
                    exit_code=1,
                    code="not_found",
                    message=f"Failed to load config file: {config_file}",
                )
                sys.exit(1)
            print_error(f"Failed to load config file: {config_file}")
            sys.exit(1)
    elif set_name:
        config = load_set(set_name)
        if not config:
            if json_mode:
                emit_error(
                    command="info",
                    exit_code=1,
                    code="not_found",
                    message=f"Set '{set_name}' not found.",
                )
                sys.exit(1)
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

    if json_mode:
        packages = [
            {
                "name": package.get("name"),
                "managers": package.get("managers") or {},
            }
            for package in config.get("packages", [])
        ]
        emit_ok(
            command="info",
            exit_code=0,
            data={
                "name": config.get("name"),
                "description": config.get("description"),
                "config_path": (
                    str(Path(config_file).resolve()) if config_file else None
                ),
                "target_os": config.get("target_os") or [],
                "preferred_managers": config.get("preferred_managers") or {},
                "managers_supported": config.get("managers_supported") or [],
                "packages": packages,
            },
        )
        return
    
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
    
    # Package list (full by default; --limit N truncates human output)
    packages = config.get("packages", [])
    total = len(packages)
    console.print(f"\n[bold]Packages:[/bold] {total}")

    if packages:
        if package_limit and package_limit > 0:
            shown = packages[:package_limit]
            truncated = total > len(shown)
        else:
            shown = packages
            truncated = False

        def _print_package_rows() -> None:
            console.print(f"\n[bold]Package list:[/bold]")
            for pkg in shown:
                pkg_name = pkg.get("name", "Unknown")
                managers_dict = pkg.get("managers", {}) or {}
                if managers_dict:
                    manager_names = [str(m) for m in managers_dict.keys()]
                    manager_display = manager_names[:3]
                    manager_str = ", ".join(manager_display)
                    if len(manager_names) > 3:
                        manager_str += "..."
                    console.print(f"  - {pkg_name} [dim]({manager_str})[/dim]")
                else:
                    console.print(f"  - {pkg_name} [dim](no managers)[/dim]")
            if truncated:
                remaining = total - len(shown)
                console.print(
                    f"  ... and {remaining} more "
                    f"(omit --limit or use --limit 0 for the full list; "
                    f"or blacksmith --json info)"
                )

        use_pager = (
            pager
            and not truncated
            and total > 20
            and getattr(console, "is_terminal", True)
        )
        try:
            if use_pager:
                with console.pager(styles=True):
                    _print_package_rows()
            else:
                _print_package_rows()
        except Exception as e:
            print_warning(f"Could not display packages: {e}")
    
    return


@cli.command(
    epilog=examples_epilog(
        "blacksmith validate ./my-set.yaml",
        "blacksmith validate ./my-set.yaml --strict-trust",
        "blacksmith validate --url https://example.com/set.yaml",
    ),
)
@click.argument("config_path", required=False, type=click.Path(exists=True))
@click.option("--url", "config_url", help="HTTPS URL of a remote set YAML")
@click.option("--strict-trust", is_flag=True, help="Fail closed when trust-scan findings are present (default: warn for local file)")
@click.pass_context
def validate(
    ctx: click.Context,
    config_path: Optional[str],
    config_url: Optional[str],
    strict_trust: bool,
):
    """Validate a configuration file or remote HTTPS set YAML."""
    reject_json_if_unsupported(ctx, "validate")
    from blacksmith.config.parser import load_yaml

    source_count = sum(bool(x) for x in (config_path, config_url))
    if source_count != 1:
        print_error("Provide exactly one of: config path, or --url.")
        sys.exit(2)

    if config_url:
        fetched = None
        try:
            try:
                fetched = fetch_set_url(config_url, fetch_sidecar=False)
            except FetchError as exc:
                print_error(str(exc))
                sys.exit(1)
            data = load_yaml(str(fetched.path))
            label = f"{fetched.final_url} (sha256:{fetched.sha256[:12]}…)"
            if validate_and_report(data):
                apply_trust_scan(
                    data,
                    command="validate",
                    json_mode=False,
                    strict_trust=strict_trust,
                    remote=True,
                )
                print_success(f"Configuration file is valid: {label}")
                print_info(f"Name: {data.get('name', 'Unnamed')}")
                print_info(f"Packages: {len(data.get('packages', []))}")
            else:
                sys.exit(1)
        except SystemExit:
            raise
        except Exception as e:
            print_error(f"Failed to validate config: {e}")
            sys.exit(1)
        finally:
            if fetched is not None:
                cleanup_fetched(fetched)
        return

    try:
        data = load_yaml(config_path)
        if validate_and_report(data):
            apply_trust_scan(
                data,
                command="validate",
                json_mode=False,
                strict_trust=strict_trust,
                remote=False,
            )
            print_success(f"Configuration file is valid: {config_path}")
            print_info(f"Name: {data.get('name', 'Unnamed')}")
            print_info(f"Packages: {len(data.get('packages', []))}")
        else:
            sys.exit(1)
    except Exception as e:
        print_error(f"Failed to validate config: {e}")
        sys.exit(1)


@cli.command(
    epilog=examples_epilog(
        "blacksmith search git",
        "blacksmith search nmap --manager apt --limit 5",
        "blacksmith --json search git --limit 5",
    ),
)
@click.argument("query", required=False)
@click.option("--manager", "-m", help="Filter by specific package manager")
@click.option("--limit", "-l", default=10, help="Maximum number of results")
@click.pass_context
def search(
    ctx: click.Context, query: Optional[str], manager: Optional[str], limit: int
):
    """Search for packages across available package managers."""
    if is_json_mode(ctx):
        if not query:
            emit_error(
                command="search",
                exit_code=2,
                code="needs_args",
                message="Search query is required with --json.",
            )
            sys.exit(2)

        from blacksmith.utils.identifiers import validate_search_query

        query_ok, query_error = validate_search_query(query)
        if not query_ok:
            emit_error(
                command="search",
                exit_code=2,
                code="invalid_query",
                message=query_error or "Invalid search query",
            )
            sys.exit(2)

        available_managers = detect_available_managers()
        if manager:
            manager_aliases = {
                "choco": "chocolatey",
                "dnf": "yum",
                "homebrew": "brew",
            }
            canonical_name = manager_aliases.get(manager.lower(), manager.lower())
            available_managers = [
                mgr
                for mgr in available_managers
                if mgr.name.lower() == canonical_name
            ]

        if not available_managers:
            emit_error(
                command="search",
                exit_code=1,
                code="no_managers",
                message="No matching package managers detected on this system.",
            )
            sys.exit(1)

        result_groups = []
        notes = []
        for mgr in available_managers:
            packages = mgr.search(query, limit=limit)
            if packages:
                result_groups.append(
                    {
                        "manager": mgr.name,
                        "packages": [
                            {
                                "name": package.get("name"),
                                "id": package.get("id"),
                                "description": package.get("description"),
                            }
                            for package in packages
                        ],
                    }
                )
            elif mgr.name in ("snap", "flatpak"):
                notes.append(f"{mgr.name} search is not implemented")

        emit_ok(
            command="search",
            exit_code=0,
            data={
                "query": query,
                "limit": limit,
                "results": result_groups,
                "notes": notes,
            },
        )
        return

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


@cli.command(
    epilog=examples_epilog(
        "blacksmith sign ./my-set.yaml",
        "blacksmith sign ./my-set.yaml --secret-key ~/.minisign/minisign.key",
        "blacksmith sign ./my-set.yaml -x ./my-set.yaml.minisig",
    ),
)
@click.argument("config_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--secret-key",
    "secret_key",
    type=click.Path(exists=True, dir_okay=False),
    help="minisign secret key path (default: minisign's default key file)",
)
@click.option(
    "-x",
    "--output",
    "signature_file",
    type=click.Path(dir_okay=False),
    help="Detached signature output path (default: <file>.minisig)",
)
@click.pass_context
def sign(
    ctx: click.Context,
    config_path: str,
    secret_key: Optional[str],
    signature_file: Optional[str],
):
    """Create a detached minisign signature for a set YAML file."""
    reject_json_if_unsupported(ctx, "sign")
    result = sign_set(
        Path(config_path),
        signature_path=Path(signature_file) if signature_file else None,
        secret_key=Path(secret_key) if secret_key else None,
    )
    if not result.ok:
        print_error(result.message)
        sys.exit(1)
    print_success(result.message)


@cli.command(
    epilog=examples_epilog(
        "blacksmith create",
        "blacksmith create --advanced",
    ),
)
@click.option("--advanced", is_flag=True, help="Advanced mode: single-manager sets only")
@click.pass_context
def create(ctx: click.Context, advanced: bool):
    """Interactively create a new tool set."""
    reject_json_if_unsupported(ctx, "create")
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
                questionary.Choice("Search for a package", "search"),
                questionary.Choice("Enter package manually", "manual"),
                questionary.Choice("Finish and save set", "finish"),
                questionary.Choice("Cancel and exit (don't save)", "cancel")
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


@cli.command(
    epilog=examples_epilog(
        "blacksmith uninstall",
        "blacksmith uninstall --yes",
    ),
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--no-audit", is_flag=True, help="Do not write to the local audit log")
@click.pass_context
def uninstall(ctx: click.Context, yes, no_audit):
    """Uninstall Blacksmith itself."""
    reject_json_if_unsupported(ctx, "uninstall")
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
    from blacksmith.utils.pipx import (
        pipx_package_name,
        pipx_uninstall_commands,
        should_use_pipx_uninstall,
    )
    from blacksmith.utils.safe_paths import (
        assert_safe_blacksmith_executable,
        assert_safe_blacksmith_venv,
        expected_venv_path,
    )
    from blacksmith.utils.tty import require_tty_or_yes

    console.print("\n[bold red]Uninstalling Blacksmith[/bold red]\n")

    tty_ok, tty_error = require_tty_or_yes(yes, dry_run=False)
    if not tty_ok:
        print_error(tty_error or "Non-interactive session requires --yes.")
        sys.exit(1)
    
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
    # Do not fall through to raw pip for pipx installs (leaves orphaned pipx metadata).
    if should_use_pipx_uninstall(prefix=sys.prefix, executable=blacksmith_path):
        pkg = pipx_package_name(prefix=sys.prefix, executable=blacksmith_path) or "jdi-blacksmith"
        console.print(f"[dim]Detected pipx install; trying pipx uninstall ({pkg})...[/dim]")
        last_pipx_error = None
        for cmd in pipx_uninstall_commands(pkg, extra_packages=["jdi-blacksmith", "blacksmith"]):
            try:
                console.print(f"[dim]Trying: {' '.join(cmd)}...[/dim]")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    console.print("[green][OK][/green] Successfully uninstalled via pipx")
                    console.print("\n[bold green]Blacksmith has been uninstalled.[/bold green]")
                    console.print(
                        "[dim]You may need to restart your terminal for PATH changes to take effect.[/dim]"
                    )
                    record_self_uninstall_audit(
                        manager="pipx",
                        status=PackageStatus.OK,
                        exit_code=0,
                        no_audit=no_audit,
                        package=pkg,
                    )
                    return
                err = (result.stderr or result.stdout or "").strip()
                if err:
                    last_pipx_error = err
                    logger.debug(f"pipx uninstall failed: {err[:200]}")
            except subprocess.TimeoutExpired:
                print_warning(f"pipx uninstall timed out: {' '.join(cmd)}")
            except Exception as e:
                logger.debug(f"pipx uninstall raised: {e}")

        # Deferred pipx after this process exits (helps when the shim is busy).
        for cmd in pipx_uninstall_commands(pkg, extra_packages=["jdi-blacksmith"]):
            if schedule_pip_uninstall(cmd):
                console.print(
                    "[yellow]Could not uninstall via pipx in-process; scheduled after exit.[/yellow]"
                )
                if last_pipx_error:
                    print_info(f"Last pipx error: {last_pipx_error[:300]}")
                console.print(
                    "[dim]Wait a few seconds, then confirm with `blacksmith --version` "
                    "or run: pipx uninstall jdi-blacksmith[/dim]"
                )
                record_self_uninstall_audit(
                    manager="pipx",
                    status=PackageStatus.FAILED,
                    exit_code=0,
                    no_audit=no_audit,
                    package=pkg,
                )
                return

        print_error("pipx install detected but automatic pipx uninstall failed.")
        if last_pipx_error:
            print_info(f"Last pipx error: {last_pipx_error[:300]}")
        print_info("Run manually: pipx uninstall jdi-blacksmith")
        record_self_uninstall_audit(
            manager="pipx",
            status=PackageStatus.FAILED,
            exit_code=1,
            no_audit=no_audit,
            package=pkg,
        )
        sys.exit(1)

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
                record_self_uninstall_audit(
                    manager="pip",
                    status=PackageStatus.OK,
                    exit_code=0,
                    no_audit=no_audit,
                )
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

    # Last resort: finish uninstall after this process exits (file lock / busy entry point).
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
            "[yellow]In-process uninstall failed (often because the entry point is locked).[/yellow]"
        )
        console.print(
            "[green]Scheduled pip uninstall to run after this process exits.[/green]"
        )
        console.print(
            "[dim]Close this terminal or wait a few seconds, then confirm with "
            "`blacksmith --version` (should be missing).[/dim]"
        )
        record_self_uninstall_audit(
            manager="pip",
            status=PackageStatus.FAILED,
            exit_code=0,
            no_audit=no_audit,
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

    record_self_uninstall_audit(
        manager="pip",
        status=PackageStatus.FAILED,
        exit_code=0,
        no_audit=no_audit,
    )



def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()

