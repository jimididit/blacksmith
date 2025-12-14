# Blacksmith 🔨

> A cross-platform CLI tool that automates the installation of development and cybersecurity tools after a fresh OS install.

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey.svg)](https://github.com/jimididit/blacksmith)
[![GitHub](https://img.shields.io/badge/GitHub-jimididit%2Fblacksmith-blue.svg)](https://github.com/jimididit/blacksmith)

## ✨ Features

- 🎯 **Pre-made tool sets** - Choose from curated sets of development or cybersecurity tools
- 🛠️ **Custom configurations** - Create your own sets or use custom config files
- 🔍 **Package search** - Search for packages across all package managers with real-time results
- 🌐 **Cross-platform** - Works seamlessly on Linux and Windows
- 📦 **Multiple package managers** - Supports apt, yum, pacman, winget, chocolatey, scoop, snap, and flatpak
- ✨ **Beautiful CLI** - Clean, intuitive interface with progress indicators and helpful feedback
- 🎨 **Custom color scheme** - Elegant purple and cyan theme
- ⚡ **Fast installation** - Automatically detects and uses the best package manager for each tool
- ✅ **Package validation** - Verify package names before installation

## 📋 Prerequisites

- Python 3.8 or higher
- One or more supported package managers installed on your system
- Administrator/sudo privileges (for system-wide installations)

## 🚀 Quick Start

### Linux - One-Line Install

```bash
# User installation (recommended, no sudo required)
curl -fsSL https://raw.githubusercontent.com/jimididit/blacksmith/main/install.sh | bash

# Global installation (requires sudo)
curl -fsSL https://raw.githubusercontent.com/jimididit/blacksmith/main/install.sh | sudo bash
```

### Windows

```powershell
# PowerShell one-liner
irm https://raw.githubusercontent.com/jimididit/blacksmith/main/install.ps1 | iex
```

### Install from PyPI

```bash
# Global installation
pip install jdi-blacksmith

# Or for current user only (no admin required)
pip install --user jdi-blacksmith
```

### Manual Installation (from source)

1. Clone the repository:

```bash
git clone https://github.com/jimididit/blacksmith.git
cd blacksmith
```

2. Install using pip:

```bash
# Global installation (recommended)
pip install -e .

# Or for current user only (no admin required)
pip install --user -e .
```

3. Verify installation:

```bash
blacksmith --version
```

## 📖 Usage

### Interactive Mode

The easiest way to use Blacksmith is through the interactive menu:

```bash
blacksmith
```

This will display a beautiful banner and an interactive menu to select and install tool sets.

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
blacksmith create
```

This launches an interactive wizard to create a custom tool set configuration. The wizard includes:

- **Package search**: Search for packages across all available package managers
- **Real-time validation**: Verify package names before adding them
- **Interactive selection**: Choose from search results with descriptions

### Search for Packages

Search for packages across all available package managers:

```bash
# Search across all managers
blacksmith search docker

# Search in a specific package manager
blacksmith search git --manager winget

# Limit results
blacksmith search python --limit 5
```

This is especially useful when creating custom sets, as it ensures you use the correct package names for each package manager. The search queries each package manager directly, so results are always up-to-date and accurate.

### Validate Configuration Files

```bash
blacksmith validate path/to/config.yaml
```

### Skip Already Installed Packages

```bash
blacksmith install development --skip-installed
```

### Uninstall Blacksmith

```bash
# Using the CLI
blacksmith uninstall

# Or using the uninstall script
# Linux:
curl -fsSL https://raw.githubusercontent.com/jimididit/blacksmith/main/uninstall.sh | bash

# Windows:
irm https://raw.githubusercontent.com/jimididit/blacksmith/main/uninstall.ps1 | iex
```

## 📝 Configuration Format

Blacksmith uses YAML configuration files. Here's an example:

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

Blacksmith automatically detects which package managers are available on your system and uses the appropriate one for each tool.

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
│   ├── package_managers/   # Package manager implementations
│   ├── sets/               # Pre-made tool sets
│   └── utils/              # Utility modules
├── tests/                  # Test suite
├── install.sh              # Installation script
├── uninstall.sh            # Uninstallation script
└── README.md
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
4. Register it in `blacksmith/package_managers/detector.py`
5. Add tests in `tests/test_package_managers.py`

### Adding New Tool Sets

To add a new pre-made tool set:

1. Create a new YAML file in `blacksmith/sets/` (e.g., `gaming.yaml`)
2. Follow the existing format (see `blacksmith/sets/development.yaml` for reference)
3. Include package names for all supported package managers
4. Ensure YAML syntax is valid: `yamllint blacksmith/sets/gaming.yaml`
5. Test loading the set: `blacksmith list` should show your new set

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
