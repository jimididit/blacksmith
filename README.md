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

### Linux/Mac - One-Line Install

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

### Manual Installation

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
# Linux/Mac:
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

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**jimididit**

- GitHub: [@jimididit](https://github.com/jimididit)

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
