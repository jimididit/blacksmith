# Blacksmith 🔨

> A cross-platform CLI tool that automates the installation of development and cybersecurity tools after a fresh OS install.

[![CI/CD Pipeline](https://github.com/jimididit/blacksmith/actions/workflows/ci.yml/badge.svg)](https://github.com/jimididit/blacksmith/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.2.2-blue.svg)](https://github.com/jimididit/blacksmith/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey.svg)](https://github.com/jimididit/blacksmith)
[![GitHub](https://img.shields.io/badge/GitHub-jimididit%2Fblacksmith-blue.svg)](https://github.com/jimididit/blacksmith)

## ✨ Features

- 🎯 **Pre-made tool sets** - Choose from curated sets of development or cybersecurity tools
- 🛠️ **Custom configurations** - Create your own sets or use custom config files
- 🔍 **Unified package search** - Search across all selected managers simultaneously with multi-select support
- 🌐 **Cross-platform sets** - Define sets that work on Windows, Linux, or both with OS-specific manager preferences
- 📦 **Multiple package managers** - Supports apt, yum, pacman, winget, chocolatey, scoop, snap, and flatpak
- 🎯 **Smart manager selection** - Automatically uses preferred package managers with intelligent fallback
- ✨ **Beautiful CLI** - Clean, intuitive interface with progress indicators and helpful feedback
- 🎨 **Custom color scheme** - Elegant purple and cyan theme
- ⚡ **Fast installation** - Automatically detects and uses the best package manager for each tool
- ✅ **Package validation** - Verify package names before installation
- 📤 **Export functionality** - Export sets to native package manager formats (Winget JSON, Chocolatey XML, etc.)
- 🔄 **Update support** - Check for installed packages and update them when available
- 📊 **Set information** - View detailed information about sets including OS compatibility and manager preferences

## 📋 Prerequisites

- Python 3.8 or higher
- One or more supported package managers installed on your system

## 🚀 Quick Start

### Linux - One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/jimididit/blacksmith/main/install.sh | bash
```

This creates an isolated virtual environment at `~/.blacksmith-venv` - the recommended method for better isolation and avoiding PATH issues.

### Windows

```powershell
irm https://raw.githubusercontent.com/jimididit/blacksmith/main/install.ps1 | iex
```

This creates an isolated virtual environment at `%USERPROFILE%\.blacksmith-venv` - the recommended method for better isolation and avoiding PATH issues.

**After Installation (Virtual Environment Method):**

To use Blacksmith, activate the virtual environment:

**Linux/macOS:**

```bash
source ~/.blacksmith-venv/bin/activate
```

**Windows (PowerShell):**

```powershell
~\.blacksmith-venv\Scripts\Activate.ps1
```

**Windows (CMD):**

```cmd
%USERPROFILE%\.blacksmith-venv\Scripts\activate.bat
```

**Optional:** Create an alias or add to your shell profile for automatic activation:

**Linux/macOS (~/.bashrc or ~/.zshrc):**

```bash
alias blacksmith="$HOME/.blacksmith-venv/bin/blacksmith"
# Or auto-activate:
export BLACKSMITH_VENV="$HOME/.blacksmith-venv"
[ -f "${BLACKSMITH_VENV}/bin/activate" ] && source "${BLACKSMITH_VENV}/bin/activate"
```

**Windows (PowerShell Profile):**

```powershell
Set-Alias blacksmith "$env:USERPROFILE\.blacksmith-venv\Scripts\blacksmith.exe"
# Or auto-activate:
$env:BLACKSMITH_VENV = "$env:USERPROFILE\.blacksmith-venv"
if (Test-Path "$env:BLACKSMITH_VENV\Scripts\Activate.ps1") { & "$env:BLACKSMITH_VENV\Scripts\Activate.ps1" }
```

### Alternative Installation Methods

**Install from PyPI:**

```bash
pip install jdi-blacksmith
```

**Manual Installation (from source):**

```bash
git clone https://github.com/jimididit/blacksmith.git
cd blacksmith
pip install -e .
```

> 💡 **Note:** For best results, we recommend using the one-liner installation scripts which automatically create a virtual environment. This avoids PATH issues and provides better isolation.

> 💡 **Having installation issues?** See the [Troubleshooting Installation](#-troubleshooting-installation) section below.

## 📖 Usage

### Quick Command Reference

```bash
# Interactive mode (shows menu)
blacksmith

# List available sets with OS compatibility
blacksmith list

# View detailed set information
blacksmith info <set_name>

# Install a set
blacksmith install <set_name>

# Create a custom set
blacksmith create

# Search for packages
blacksmith search <query> [--manager <name>]

# Export set to native format
blacksmith export <set_name> --format <format>

# Validate a config file
blacksmith validate <path>

# Uninstall Blacksmith
blacksmith uninstall
```

### Interactive Mode

The easiest way to use Blacksmith is through the interactive menu:

```bash
blacksmith
```

This will display a beautiful banner and an interactive menu to select and install tool sets.

### List Available Sets

View all available sets with OS compatibility indicators:

```bash
blacksmith list
```

The list shows:

- Set name and description
- OS compatibility badges (🪟 Windows, 🐧 Linux, 🍎 macOS)
- Preferred package managers
- Package count
- Compatibility status with your current OS

### Install Pre-made Sets

```bash
# List available sets
blacksmith list

# Install a specific set
blacksmith install development
blacksmith install cybersecurity
blacksmith install minimal
```

### Install from Custom Config

```bash
blacksmith install --file path/to/your-config.yaml
```

### Create Your Own Set

```bash
# Standard mode (cross-platform, multi-manager)
blacksmith create

# Advanced mode (single-OS, single-manager sets)
blacksmith create --advanced
```

This launches an interactive wizard to create a custom tool set configuration. The wizard includes:

- **OS selection**: Choose Windows, Linux, or both for cross-platform sets
- **Manager selection**: Select which package managers to target for each OS
- **Unified search**: Search across all selected managers simultaneously - see results from all managers at once
- **Multi-select**: Select packages from multiple managers in one go using checkboxes
- **Smart grouping**: Automatically groups the same package from different managers
- **Real-time validation**: Verify package names before adding them
- **Export ready**: Sets are saved with OS compatibility and manager preferences for optimal installation

### Search for Packages

Search for packages across all available package managers:

```bash
# Search across all managers
blacksmith search docker

# Search in a specific package manager (supports aliases)
blacksmith search git --manager winget
blacksmith search git --manager choco    # Alias for chocolatey

# Limit results
blacksmith search python --limit 5
```

**Features:**

- **Real-time results**: Queries each package manager directly for up-to-date results
- **Manager aliases**: Use `choco` for `chocolatey`, `dnf` for `yum`, etc.
- **OS-aware errors**: Clear messages when requesting OS-specific managers (e.g., `apt` on Windows)
- **Unified display**: Results grouped by manager with descriptions

This is especially useful when creating custom sets, as it ensures you use the correct package names for each package manager.

### View Set Information

Get detailed information about a set, including OS compatibility and manager preferences:

```bash
# View info about a pre-made set
blacksmith info development
blacksmith info cybersecurity

# View info about a custom config file
blacksmith info --file path/to/config.yaml
```

### Export Sets

Export sets to native package manager formats for use outside of Blacksmith:

```bash
# Export to Winget JSON format
blacksmith export development --format winget

# Export to Chocolatey packages.config
blacksmith export development --format chocolatey

# Export to Apt text list
blacksmith export development --format apt

# Export with custom output file
blacksmith export development --format winget --output my-packages.json
```

**Supported formats:**

- `winget` - JSON array of package IDs
- `chocolatey` / `choco` - XML packages.config format
- `apt` - Plain text list
- `pacman` - Plain text list
- `scoop` - JSON array

### Validate Configuration Files

```bash
blacksmith validate path/to/config.yaml
```

### Installation Options

```bash
# Skip already installed packages
blacksmith install development --skip-installed

# Prefer a specific package manager (overrides set preferences)
blacksmith install development --prefer winget

# Force installation even if OS doesn't match set's target_os
blacksmith install development --force
```

### Uninstall Blacksmith

```bash
# Using the CLI (removes package and virtual environment)
blacksmith uninstall

# Skip confirmation prompt
blacksmith uninstall --yes
```

The uninstall command will:

- Remove Blacksmith from your Python environment
- Remove the virtual environment (if installed via `venv` method)
- Clean up the `blacksmith` command executable

## 📝 Configuration Format

Blacksmith uses YAML configuration files with support for cross-platform sets. Here's an example:

### Basic Format (Backward Compatible)

```yaml
name: "My Custom Set"
description: "My favorite development tools"
packages:
  - name: git
    managers:
      apt: git
      pacman: git
      winget: Git.Git
      chocolatey: git
      scoop: git
  
  - name: docker
    managers:
      apt: docker.io
      pacman: docker
      yum: docker
      winget: Docker.DockerDesktop
```

### Advanced Format (Cross-Platform)

```yaml
name: "Cross-Platform Dev Tools"
description: "Development tools for Windows and Linux"
target_os: ["windows", "linux"]  # OS compatibility
preferred_managers:              # Manager preferences per OS
  windows: ["winget", "chocolatey"]
  linux: ["apt", "flatpak"]
managers_supported:              # Limit to specific managers
  - winget
  - chocolatey
  - apt
  - flatpak
packages:
  - name: git
    managers:
      winget: Git.Git
      chocolatey: git
      apt: git
      flatpak: org.gnome.gitg
```

**Configuration Fields:**

- `name` (required) - Set name
- `description` (optional) - Set description
- `target_os` (optional) - List of target OSes: `["windows"]`, `["linux"]`, or `["windows", "linux"]`
- `preferred_managers` (optional) - Dictionary mapping OS to preferred manager order
- `managers_supported` (optional) - List of managers to limit installation to
- `packages` (required) - List of packages with manager-specific IDs

## 📦 Supported Package Managers

### Linux

- **apt** - Debian/Ubuntu
- **yum/dnf** - RHEL/Fedora
- **pacman** - Arch Linux
- **snap** - Universal Linux packages
- **flatpak** - Application sandboxing

### Windows

- **winget** - Windows Package Manager
- **chocolatey** - Windows package manager
- **scoop** - Command-line installer

**Smart Manager Selection:**

Blacksmith automatically detects which package managers are available on your system and uses intelligent selection:

- **Preference-based**: Uses `preferred_managers` from the set configuration if specified
- **OS-specific defaults**: Falls back to sensible defaults (e.g., `winget` > `chocolatey` > `scoop` on Windows)
- **Fallback logic**: If preferred manager isn't available, tries the next one in order
- **OS compatibility**: Checks if the set is compatible with your OS (can be overridden with `--force`)
- **Manager filtering**: Respects `managers_supported` to limit which managers are considered

## 🍎 macOS Support (Future)

macOS support is planned for a future release. While the codebase includes some macOS compatibility (OS detection, install scripts), full support is not yet available.

**Planned features for macOS:**

- Homebrew package manager integration
- MacPorts support (optional)
- Native macOS package installation workflows
- Full compatibility with macOS-specific tool installations

If you're interested in contributing macOS support, please check out our [Contributing](#-contributing) section or open an issue to discuss!

## 🎨 Pre-made Sets

### Development

Essential development tools including Git, Docker, VS Code, Python, Node.js, and more.

### Cybersecurity

Security and penetration testing tools including Nmap, Wireshark, Metasploit, Burp Suite, and more.

### Minimal

Lightweight setup with just the essentials: Git, curl, and Vim.

## 🛠️ Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/jimididit/blacksmith.git
cd blacksmith

# Create a virtual environment
python -m venv venv

# Activate it
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies (for testing and code quality)
pip install pytest pytest-cov pytest-mock ruff black mypy yamllint
```

### Project Structure

```
blacksmith/
├── blacksmith/
│   ├── cli.py              # Main CLI interface
│   ├── config/             # Configuration system
│   │   ├── loader.py       # Config file loading
│   │   ├── parser.py       # YAML parsing
│   │   ├── preferences.py  # Manager preference system
│   │   └── validator.py    # Config validation
│   ├── export/             # Export functionality
│   │   ├── base.py         # Base exporter class
│   │   ├── winget.py       # Winget JSON exporter
│   │   ├── chocolatey.py   # Chocolatey XML exporter
│   │   ├── apt.py          # Apt list exporter
│   │   ├── pacman.py       # Pacman list exporter
│   │   └── scoop.py        # Scoop JSON exporter
│   ├── package_managers/   # Package manager implementations
│   ├── sets/               # Pre-made tool sets
│   └── utils/              # Utility modules
│       ├── os_detector.py  # OS detection
│       └── ui.py           # UI helpers (Rich)
├── tests/                  # Test suite
├── scripts/                # Helper scripts
│   └── bump_version.py     # Version bumping script
├── install.sh              # Installation script
├── install.ps1             # Windows installation script
└── README.md
```

### Version Management

Blacksmith uses [Semantic Versioning](https://semver.org/) (SemVer): `MAJOR.MINOR.PATCH`

- **PATCH** (0.1.0 → 0.1.1): Bug fixes, security patches
- **MINOR** (0.1.0 → 0.2.0): New features (backward compatible)
- **MAJOR** (0.2.0 → 1.0.0): Breaking changes, first stable release

**Quick version bump:**

```bash
# Bump patch version (0.1.0 -> 0.1.1)
python scripts/bump_version.py --patch

# Bump minor version (0.1.0 -> 0.2.0)
python scripts/bump_version.py --minor

# Bump major version (0.1.0 -> 1.0.0)
python scripts/bump_version.py --major

# Or set a specific version
python scripts/bump_version.py 0.1.1
```

**Manual version update:**
Update the version in both `pyproject.toml` and `blacksmith/__init__.py`, then:

```bash
git tag -a v0.1.1 -m "Release version 0.1.1"
git push origin v0.1.1
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/blacksmith.git`
3. Create a feature branch: `git checkout -b feature/AmazingFeature`
4. Set up your development environment (see the [Development](#️-development) section above)

### Development Workflow

1. Make your changes
2. Run tests locally (see [Testing](#testing) below)
3. Ensure code quality checks pass (see [Code Quality](#code-quality) below)
4. Commit your changes: `git commit -m 'Add some AmazingFeature'`
5. Push to your fork: `git push origin feature/AmazingFeature`
6. Open a Pull Request

### Testing

Before submitting a PR, please ensure all tests pass:

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=blacksmith --cov-report=term

# Run specific test file
pytest tests/test_cli.py -v
```

### Code Quality

We use several tools to maintain code quality. Please ensure your code passes these checks:

```bash
# Install development dependencies
pip install ruff black mypy yamllint

# Linting (check for errors)
ruff check blacksmith/

# Formatting (check if code is formatted)
ruff format --check blacksmith/

# Auto-fix linting issues
ruff check --fix blacksmith/

# Auto-format code
ruff format blacksmith/

# Type checking
mypy blacksmith/ --ignore-missing-imports

# YAML linting
yamllint blacksmith/sets/*.yaml
```

### Adding New Package Managers

To add support for a new package manager:

1. Create a new file in `blacksmith/package_managers/` (e.g., `brew.py`)
2. Inherit from `PackageManager` base class in `blacksmith/package_managers/base.py`
3. Implement required methods:
   - `is_available()` - Check if the package manager is installed
   - `install(packages)` - Install packages
   - `is_installed(package)` - Check if a package is installed
   - `search(query)` - Search for packages
   - `update_package(package)` - Update a single package (optional but recommended)
4. Register it in `blacksmith/package_managers/detector.py`
5. Add it to the default preferences in `blacksmith/config/preferences.py` if applicable
6. Add tests in `tests/test_package_managers.py`

### Adding New Tool Sets

To add a new pre-made tool set:

1. Create a new YAML file in `blacksmith/sets/` (e.g., `gaming.yaml`)
2. Follow the existing format (see `blacksmith/sets/development.yaml` for reference)
3. Include package names for all supported package managers
4. Optionally add cross-platform fields:
   - `target_os` - List of target OSes (e.g., `["windows", "linux"]`)
   - `preferred_managers` - OS-specific manager preferences
   - `managers_supported` - Limit to specific managers
5. Ensure YAML syntax is valid: `yamllint blacksmith/sets/gaming.yaml`
6. Test loading the set: `blacksmith list` should show your new set
7. Test the `info` command: `blacksmith info gaming` should display correctly

### Reporting Bugs

When reporting bugs, please include:

- Operating system and version
- Python version
- Blacksmith version (`blacksmith --version`)
- Steps to reproduce
- Expected vs actual behavior
- Error messages or logs (if applicable)

### Feature Requests

For feature requests, please:

- Open an issue describing the feature
- Explain the use case and benefits
- Discuss implementation approach (if you have ideas)
- Consider contributing the feature yourself!

### Code Style Guidelines

- Follow PEP 8 style guide
- Use type hints where possible
- Write docstrings for all functions and classes
- Keep functions focused and small
- Add comments for complex logic
- Use meaningful variable and function names

## 🔧 Troubleshooting Installation

### Command Not Found After Installation

If `blacksmith` is not recognized after installation, it's likely a PATH issue:

**Linux/macOS (with `--user` install):**

```bash
# Add to your ~/.bashrc, ~/.zshrc, or ~/.profile:
export PATH="$HOME/.local/bin:$PATH"

# Then reload your shell:
source ~/.bashrc  # or source ~/.zshrc
```

**Windows (with `--user` install):**

```powershell
# Find your user Scripts directory:
python -m site --user-base

# Add it to PATH (replace with your actual path):
# Typically: %USERPROFILE%\AppData\Roaming\Python\Python3X\Scripts
# Or: %LOCALAPPDATA%\Programs\Python\Python3X\Scripts

# Then restart your terminal
```

**Alternative: Use a Virtual Environment (Recommended)**

If you continue to have PATH issues, using a virtual environment is the most reliable option:

```bash
# Create and activate a virtual environment
python -m venv blacksmith-env

# Activate it:
# Linux/macOS:
source blacksmith-env/bin/activate
# Windows:
blacksmith-env\Scripts\activate

# Install blacksmith
pip install jdi-blacksmith

# Now blacksmith will work as long as the venv is activated
blacksmith --version
```

### Permission Errors (Global Installation)

If you get permission errors when installing globally:

**Linux/macOS:**

```bash
# Use sudo (not recommended for security):
sudo pip install jdi-blacksmith

# Better: Use --user flag (no sudo needed):
pip install --user jdi-blacksmith
```

**Windows:**

```powershell
# Run PowerShell as Administrator, then:
pip install jdi-blacksmith

# Better: Use --user flag (no admin needed):
pip install --user jdi-blacksmith
```

### Installation Works But Command Not Found

If installation succeeds but the command isn't found:

1. **Check if it's installed:**

   ```bash
   python -m blacksmith --version
   ```

2. **Find where pip installed the script:**

   ```bash
   # Linux/macOS:
   python -m site --user-base
   # Then check: <path>/bin/blacksmith
   
   # Windows:
   python -m site --user-base
   # Then check: <path>\Scripts\blacksmith.exe
   ```

3. **Verify the entry point:**

   ```bash
   pip show jdi-blacksmith
   # Look for "Location:" and "Entry-points:"
   ```

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**jimididit**

- GitHub: [@jimididit](https://github.com/jimididit)
- Instagram: [@jimididit](https://instagram.com/jimi.did.it)
- YouTube: [@jimididit](https://youtube.com/@jimididit)
- TikTok: [@jimididit](https://tiktok.com/@jimi.did.it)
- Website: [www.jimididit.com](https://jimididit.com)
- Discord: [NØKTURNAL COMMUNITY](https://jimididit.com/discord)

## 🙏 Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI framework
- Beautiful terminal output powered by [Rich](https://github.com/Textualize/rich)
- Interactive prompts with [Questionary](https://github.com/tmbo/questionary)

## 📚 Additional Resources

- **Repository**: [https://github.com/jimididit/blacksmith](https://github.com/jimididit/blacksmith)
- [Issue Tracker](https://github.com/jimididit/blacksmith/issues)
- [Discussions](https://github.com/jimididit/blacksmith/discussions)

---

⭐ If you find this project helpful, please consider giving it a star on [GitHub](https://github.com/jimididit/blacksmith)!
