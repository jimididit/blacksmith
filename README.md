<h1 align="center">Blacksmith</h1>

<p align="center">
  Cross-platform CLI that installs curated development and cybersecurity<br>
  tool sets after a fresh OS install.
</p>

<p align="center">
  <a href="https://github.com/jimididit/blacksmith/actions/workflows/ci.yml"><img src="https://github.com/jimididit/blacksmith/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+"></a>
  <a href="https://github.com/jimididit/blacksmith/releases"><img src="https://img.shields.io/badge/version-0.4.1-blue.svg" alt="Version 0.4.1"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-green.svg" alt="Apache 2.0"></a>
  <a href="https://github.com/jimididit/blacksmith"><img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg" alt="Platform"></a>
</p>

<p align="center">
  <a href="#install">Install</a>
  &nbsp;&middot;&nbsp;
  <a href="#quick-start">Quick start</a>
  &nbsp;&middot;&nbsp;
  <a href="#commands">Commands</a>
  &nbsp;&middot;&nbsp;
  <a href="#configuration">Configuration</a>
  &nbsp;&middot;&nbsp;
  <a href="#package-managers">Package managers</a>
  &nbsp;&middot;&nbsp;
  <a href="#trust">Trust</a>
  &nbsp;&middot;&nbsp;
  <a href="#troubleshooting">Troubleshooting</a>
  &nbsp;&middot;&nbsp;
  <a href="#contributing">Contributing</a>
  &nbsp;&middot;&nbsp;
  <a href="SECURITY.md">Security</a>
</p>

## Features

- Pre-made sets: `development`, `cybersecurity`, `minimal` - see [Quick start](#quick-start)
- Custom YAML sets and a create wizard - see [Configuration](#configuration)
- Multiple package managers on Linux, Windows, and macOS - see [Package managers](#package-managers)
- Smart manager selection with OS preferences and fallback
- Automation flags: `--yes`, `--dry-run`, `--fail-fast` - see [Commands](#commands)
- Machine-readable output: global `--json` for scripting - see [Machine-readable output](#machine-readable-output)
- Package ID allowlist for argv safety (not upstream existence or content trust) - see [Trust](#trust)
- Export to native manager formats - see [Commands](#commands)

## Install

Requires Python 3.8+ and at least one [supported package manager](#package-managers).

Recommended (isolated CLI via [pipx](https://pipx.pypa.io/)):

```bash
pipx install jdi-blacksmith
blacksmith --version
```

Remove with `blacksmith uninstall` (detects pipx) or `pipx uninstall jdi-blacksmith`.

### pip / virtualenv (fallback)

```bash
pip install jdi-blacksmith
blacksmith --version
```

Dedicated venv (Linux / macOS):

```bash
python3 -m venv ~/.blacksmith-venv
source ~/.blacksmith-venv/bin/activate
pip install jdi-blacksmith
```

Windows (PowerShell):

```powershell
python -m venv $env:USERPROFILE\.blacksmith-venv
$env:USERPROFILE\.blacksmith-venv\Scripts\Activate.ps1
pip install jdi-blacksmith
```

From source: `git clone` the repo, then `pip install -e .`.

PATH or permission problems: [Troubleshooting](#troubleshooting).

## Quick start

```bash
blacksmith list
blacksmith install minimal --dry-run
blacksmith apply minimal --yes
```

| Set | Focus |
|-----|-------|
| `development` | Git, Docker, editors, language toolchains |
| `cybersecurity` | Security and pentest tooling |
| `minimal` | Essentials (includes `brew:` IDs for macOS) |

Custom YAML and create wizard: [Configuration](#configuration). Flags and policy: [Commands](#commands). Shared files: [Trust](#trust).

## Commands

| Command | Purpose |
|---------|---------|
| `blacksmith` | Interactive menu |
| `blacksmith list` | List sets |
| `blacksmith info <set>` | Set details |
| `blacksmith install <set>` | Install a set |
| `blacksmith install <set> --dry-run` | Preview plan only |
| `blacksmith install <set> --yes` | Non-interactive (required without a TTY) |
| `blacksmith install <set> --fail-fast` | Stop on first package failure |
| `blacksmith install --file path.yaml --yes` | Install custom YAML ([untrusted](#trust)) |
| `blacksmith install --file path.yaml --require-signature` | Require minisign verify before install |
| `blacksmith apply <set> --yes` | Ensure set state (idempotent; skip installed) |
| `blacksmith apply <set> --dry-run` | Preview apply plan only |
| `blacksmith apply --file path.yaml --yes` | Apply custom YAML ([untrusted](#trust)) |
| `blacksmith apply --file path.yaml --require-signature` | Require minisign verify before apply |
| `blacksmith create` / `create --advanced` | Create a set |
| `blacksmith search <query> [--manager name]` | Search managers |
| `blacksmith export <set> --format <fmt>` | Export (`winget`, `chocolatey`, `apt`, `pacman`, `scoop`) |
| `blacksmith validate <path>` | Schema + ID allowlist check |
| `blacksmith audit [--last N]` | Show recent local audit events (default 50) |
| `blacksmith uninstall [--yes]` | Remove Blacksmith (uses pipx when detected) |

Other install flags: `--skip-installed`, `--prefer <mgr>`, `--force` (ignore `target_os` mismatch).
Apply also supports `--prefer`, `--force`, and `--fail-fast`.
Signature flags (with `--file`): `--require-signature`, `--signature PATH`, `--pubkey PATH`.

**Apply exit codes:** `0` already compliant, `2` changed with no failures, `1` failures. Install stays `0`/`1`.

**Policy:** default is best-effort continue after failures (no rollback). Each package installs individually.

**Privileges:** on Linux, apt / pacman / yum|dnf / snap may prompt for sudo. Flatpak and Homebrew do not use that path.

**Search note:** Snap and Flatpak support install, but `search` does not query them yet.

### Machine-readable output

Pass `--json` on supported commands to emit a single JSON object on stdout. Human banners, tables, and prompts are suppressed; diagnostics may appear on stderr.

Supported commands: `list`, `info`, `search`, `install`, `apply`. All other commands (including the bare interactive menu) emit a failure envelope with `error.code` `json_unsupported` and exit `2`.

Every envelope includes `schema_version` (currently `1`). Consumers should ignore unknown fields.

Success envelope:

```json
{
  "schema_version": 1,
  "command": "list",
  "ok": true,
  "exit": 0,
  "data": { }
}
```

Failure envelope:

```json
{
  "schema_version": 1,
  "command": "install",
  "ok": false,
  "exit": 1,
  "error": { "code": "not_found", "message": "Set 'nope' not found." }
}
```

Install and apply failure envelopes may also include a `data` block with `summary` and `outcomes` so scripts can act on partial runs. Treat this as additive; other failure shapes omit `data`.

Examples:

```bash
blacksmith --json list | jq '.data.sets[].name'
blacksmith --json info minimal | jq '.data.packages | length'
blacksmith --json search git --limit 5 | jq '.data.results[].manager'
blacksmith --json install minimal --yes --dry-run | jq '.data.outcomes[] | select(.action=="install")'
blacksmith --json apply minimal --yes | jq '{ok, exit, changed: .data.summary.changed}'
```

Mutating commands under `--json` require `--yes` or `--dry-run` (prompts are disabled). A set name or `--file` is also required; the interactive set menu is unavailable.

```bash
blacksmith --json install --file path/to/set.yaml --yes
blacksmith --json apply --file path/to/set.yaml --dry-run
```

Apply exit codes in JSON mode match human mode: `0` already compliant, `2` changed with no failures, `1` failures. On exit `2`, the envelope has `ok: true` (the run succeeded; state changed).

Common `error.code` values: `json_unsupported`, `needs_args`, `not_found`, `invalid_query`, `no_managers`, `invalid_config`, `signature_failed`, `cancelled`, `install_failed`.

### Audit

```bash
blacksmith audit
blacksmith audit --last 20
```

Mutating `install` / `apply` (and self-`uninstall`) append events to a local JSONL file (`audit.jsonl`) under the platform config directory unless `--no-audit` or `BLACKSMITH_NO_AUDIT` (truthy: `1`, `true`, `yes`) is set. Dry-run and no-op runs are not logged.

Default path: `%APPDATA%\blacksmith\audit.jsonl` (Windows) or `~/.config/blacksmith/audit.jsonl` (Linux/macOS; honors `XDG_CONFIG_HOME`).

Use `--no-audit` on `install`, `apply`, and `uninstall`. The bare interactive menu (no subcommand) has no `--no-audit` flag; set `BLACKSMITH_NO_AUDIT=1` to disable audit there.

Privacy: the log may include OS username, set name, config path/hash, and package ids. It is local only; delete the file to clear history. Integrity and threat model: [SECURITY.md](SECURITY.md).

## Configuration

```yaml
name: "My Custom Set"
description: "My favorite tools"
target_os: ["windows", "linux", "macos"]
preferred_managers:
  windows: ["winget", "chocolatey"]
  linux: ["apt", "flatpak"]
  macos: ["brew"]
packages:
  - name: git
    managers:
      apt: git
      brew: git
      winget: Git.Git
      chocolatey: git
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | yes | Set name |
| `description` | no | Short summary |
| `target_os` | no | `windows`, `linux`, `macos` / `darwin` |
| `preferred_managers` | no | Per-OS manager order |
| `managers_supported` | no | Limit which managers are considered |
| `packages` | yes | Manager IDs must pass the [argv allowlist](#trust) |

Validate: `blacksmith validate path/to/config.yaml` (structure and allowlist only - not upstream existence).

## Package managers

| OS | Managers |
|----|----------|
| Linux | apt, yum/dnf, pacman, snap, flatpak |
| Windows | winget, chocolatey, scoop |
| macOS | brew (Homebrew formulas and casks) |

Selection uses set `preferred_managers` when present, otherwise OS defaults (winget then chocolatey then scoop on Windows; brew on macOS), then any other available managers.

macOS: Darwin is detected; Homebrew is registered when `brew` is on `PATH`. The `minimal` set includes `brew:` IDs. Broader brew coverage across other sets, MacPorts, and brew export are later work. Install Homebrew: https://brew.sh

## Trust

Treat set YAML like code you are willing to run. Package ID allowlists block shell metacharacters; they do not prove packages are safe or exist upstream. Third-party `--file` YAML is untrusted - review it, prefer `--dry-run`, then `--yes`.

### Version pins (inline)

Append `|version` to a manager package ID (the version segment must start with a digit):

```yaml
packages:
  - name: nmap
    managers:
      apt: "nmap|7.94"
  - name: git
    managers:
      chocolatey: "git|2.40.0"
```

Supported for pins: chocolatey, apt, yum/dnf, winget, brew. A pin on snap, flatpak, scoop, or pacman fails closed with `pin_unsupported` (no install is attempted).

**Version pin notes:**
- Pin syntax `name|version` excludes `:` and `~` characters (epochs and pre-release markers; L1.2 follow-up)
- apt and yum/dnf pins must match the manager's native version format exactly (e.g., full dpkg Version or rpm VERSION-RELEASE); short pins like `nmap|7.94` may not match installed `7.94-1`
- brew pins install versioned formulae (`go@1.21`), not specific Cellar patch versions
- winget pins parse the Version column from `winget list` output; ensure pin matches the reported version

On `apply`, an installed package must match the pin exactly or Blacksmith fails (`version_mismatch` or `version_unknown`); it does not auto-upgrade to satisfy a pin. Unpinned IDs still install the latest available from the manager. Companion lockfiles are not in this release.

Optional authenticity (minisign): authors sign with `minisign -Sm set.yaml` and distribute `set.yaml` + `set.yaml.minisig` + their `.pub`. Operators add the pubkey under `~/.config/blacksmith/trusted_keys/` (Linux/macOS), `%APPDATA%\blacksmith\trusted_keys\` (Windows), or pass `--pubkey`, then:

```bash
blacksmith install --file path/to/set.yaml --require-signature --yes
```

Without `--require-signature`, unsigned `--file` behavior is unchanged. Requires the `minisign` CLI on PATH.

Threat model, reporting vulnerabilities, and a safe review workflow: [SECURITY.md](SECURITY.md).

```bash
blacksmith validate path/to/set.yaml
blacksmith install --file path/to/set.yaml --dry-run
blacksmith install --file path/to/set.yaml --yes
```

## Troubleshooting

**Command not found after install**

- Prefer [pipx](#install) so `blacksmith` is on PATH without activating a venv.
- Or use a [virtualenv](#install) and activate it before running commands.
- Linux/macOS user install: add `$HOME/.local/bin` to `PATH`.
- Windows user install: add the user `Scripts` directory from `python -m site --user-base` to PATH.
- Fallback: `python -m blacksmith --version`

**Permission errors**

Prefer `pipx install jdi-blacksmith`, or `pip install --user jdi-blacksmith`, instead of `sudo pip` / admin installs.

## Contributing

Do not push directly to `main`. Use a feature branch and a PR; merge only when the required **CI** check is green.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow.

## License

Apache 2.0 - see [LICENSE](LICENSE).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Author

**jimididit**

- GitHub: [@jimididit](https://github.com/jimididit)
- Website: [www.jimididit.com](https://jimididit.com)
- Discord: [Nokturnal Community](https://jimididit.com/discord)
