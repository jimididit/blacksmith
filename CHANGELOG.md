# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-09-18

Minor release: remote set URLs, offline trust scan, fuller `info` listing, and help Examples.

### Added

- `install` / `apply` / `validate --url https://…` for remote HTTPS set YAML (fetch to temp, existing `--file` trust path, REMOTE banner, content SHA-256; no persistent cache)
- HTTPS-only fetch with SSRF literal-host blocks, timeout, and max body size; optional `{url}.minisig` sidecar or `--signature` path/URL with `--require-signature`
- Offline trust scan on custom `--file` / remote `--url` sets (heuristics + optional/empty bundled denylist reserved for known-bad IDs); warn by default for local files; fail closed under `--strict-trust` or remote `--url` (`trust_scan_failed`); never claims "safe"
- `Examples:` sections on root `blacksmith --help` and every subcommand `--help`
- `info` shows the full package list by default, with optional `--limit`, `--pager` / `--no-pager`

## [0.5.0] - 2026-09-18

Minor release: version pins, JSON output, install audit log, minisign set verification, and ASCII CLI status tags.

### Added

- Inline package version pins: append `|version` to manager IDs (for example `apt: "nmap|7.94"`, `chocolatey: "git|2.40.0"`)
- Pin-aware install and apply for chocolatey, apt, yum/dnf, winget, and brew; unsupported managers fail with `pin_unsupported`
- Apply pin checks: exact match skips; mismatch or unknown version fails (`version_mismatch`, `version_unknown`) with no auto-upgrade
- Version pin notes:
  - Pin syntax `name|version` excludes `:` and `~` characters (epochs and pre-release markers; L1.2 follow-up)
  - apt and yum/dnf pins must match the manager's native version format exactly (e.g., full dpkg Version or rpm VERSION-RELEASE)
  - brew pins install versioned formulae (e.g., `go@1.21`), not specific Cellar patch versions
  - winget pins parse the Version column from `winget list` output
- Global `--json` for machine-readable output on `list`, `info`, `search`, `install`, and `apply`
- Stable JSON envelope (`schema_version` 1): `command`, `ok`, `exit`, and either `data` or `error`
- Unsupported commands and the bare interactive menu fail closed with `json_unsupported` (exit 2)
- Install/apply JSON payloads include per-package `outcomes` and `summary`; failure envelopes may also include `data` for partial runs
- Apply exit 2 reports `ok: true` in the JSON envelope (changed, no failures)
- Local install audit log (`audit.jsonl`): `blacksmith audit [--last N]`, `--no-audit`, `BLACKSMITH_NO_AUDIT`
- `--require-signature` for `install --file` / `apply --file` (minisign CLI verify)
- Trusted keys: packaged `blacksmith/keys/*.pub`, user `trusted_keys/`, optional `--pubkey`
- `--signature` override for detached `.minisig` path

### Changed

- CLI status lines use ASCII tags (`[OK]`, `[ERR]`, `[WARN]`, `[INFO]`) on all platforms; skip messages use `Skip:` word prefixes; OS badges are `Win` / `Lin` / `Mac` (no emoji)

## [0.4.1] - 2026-09-13

Patch release: uninstall reliability for pipx and Windows, plus the new `apply` command.

### Added

- `blacksmith apply`: idempotent ensure-state (skip installed, post-install verify)
- Apply exit codes: `0` compliant, `2` changed, `1` failed
- `blacksmith uninstall` detects pipx-managed installs and runs `pipx uninstall`
- Windows self-uninstall: prefer Scripts\\pip.exe, unlock locked .exe, deferred pip fallback
- Stronger pipx uninstall: shebang detect, `python -m pipx`, `~/.local/bin/pipx`, no raw-pip fallback for pipx installs

### Changed

- README recommends `pipx install jdi-blacksmith` as the primary install path
- `uninstall` requires `--yes` without a TTY

### Fixed

- `uninstall` `NameError: Confirm is not defined` on PyPI 0.4.0 (blocked all uninstalls)

## [0.4.0] - 2026-09-12

Platform and docs release: Homebrew on macOS, trust docs, and README cleanup.

### Added

- Homebrew (`brew`) package manager for macOS (formulas and casks)
- `SECURITY.md` with vulnerability reporting and shared-set threat model
- Manager subprocess mock tests for all package managers
- Slim README with centered navigation
- Single `CHANGELOG.md` (replaces per-version `release-notes/` files)

### Changed

- macOS preferences default to `brew` only
- `minimal` set includes `brew:` package IDs
- Config validator allows `brew` as a manager name
- Release workflow extracts GitHub Release body from `CHANGELOG.md`

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
- GitHub Actions runtimes bumped to Node 24â€“compatible actions

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


[Unreleased]: https://github.com/jimididit/blacksmith/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/jimididit/blacksmith/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/jimididit/blacksmith/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/jimididit/blacksmith/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/jimididit/blacksmith/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jimididit/blacksmith/compare/v0.2.3...v0.3.0
[0.2.3]: https://github.com/jimididit/blacksmith/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/jimididit/blacksmith/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/jimididit/blacksmith/releases/tag/v0.2.1
