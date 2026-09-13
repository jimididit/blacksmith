# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Homebrew (`brew`) package manager for macOS (formulas and casks)
- `SECURITY.md` with vulnerability reporting and shared-set threat model
- Manager subprocess mock tests for all package managers
- Slim README with centered navigation

### Changed

- macOS preferences default to `brew` only
- `minimal` set includes `brew:` package IDs
- Config validator allows `brew` as a manager name

## [0.3.0] - 2026-09-12

Security and install-reliability release (trust boundary + automation hardening).

### Added

- Package ID and search query allowlists (fail closed)
- Custom `--file` trust warning; `--yes` and `--dry-run`
- Non-interactive sessions require `--yes` or `--dry-run` (TTY fail-closed)
- Dry-run action plan (package, manager, id, action)
- Per-package install/update outcomes; optional `--fail-fast` (default: best-effort continue)
- `requirements.lock` with CI `pip-audit`
- PyPI publish via Trusted Publishing (OIDC, environment `release`)
- Safe uninstall path deletes (no shell-interpolated cleanup scripts)

### Changed

- Removed `shell=True` from Windows package-manager and uninstall pip paths
- Flatpak remains a first-class Linux PM; sudo warning only for apt/pacman/yum/snap
- Snap/Flatpak search documented as not implemented yet
- GitHub Actions runtimes bumped to Node 24–compatible actions

### Security

- Hard CI gates: trust boundary, tests, `pip-audit`, Bandit

## [0.2.3] - 2025-12-16

### Changed

- Uninstall prompts before deleting the managed virtualenv
- Active-venv uninstall schedules cleanup after process exit
- Installation docs favor manual virtualenv setup over one-liner scripts

### Removed

- `install.sh` / `install.ps1` one-liner install scripts

## [0.2.2] - 2025-12-15

### Fixed

- PyPI wheel missing subpackages (`config`, `export`, `package_managers`, `utils`) that caused `ModuleNotFoundError` after install
- `pyproject.toml` now explicitly includes all subpackages

## [0.2.1] - 2025-12-15

First public release.

### Added

- Cross-platform sets: `target_os`, `preferred_managers`, `managers_supported`
- Redesigned `create` wizard (unified search, multi-select, OS/manager selection)
- `info` and `export` commands
- Smart manager selection with OS defaults and fallback
- Search manager aliases and OS-aware errors
- Update support across package managers
- Enhanced `list` with OS compatibility

### Fixed

- `info` argument parsing; create defaults; skip-manager flow
- Winget search Unicode and older-client parsing

[Unreleased]: https://github.com/jimididit/blacksmith/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/jimididit/blacksmith/compare/v0.2.3...v0.3.0
[0.2.3]: https://github.com/jimididit/blacksmith/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/jimididit/blacksmith/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/jimididit/blacksmith/releases/tag/v0.2.1
