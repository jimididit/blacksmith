# Blacksmith Installation Script for Windows
# This script installs Blacksmith from a GitHub repository

$ErrorActionPreference = "Stop"

Write-Host "🔨 Blacksmith Installation Script" -ForegroundColor Blue
Write-Host ""

# Check for Python
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
}

if (-not $pythonCmd) {
    Write-Host "✗ Python is not installed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Installation options:"
    Write-Host "  Windows (winget):    winget install Python.Python.3.12"
    Write-Host "  Windows (choco):      choco install python3 -y"
    Write-Host "  Windows (manual):     Download from https://www.python.org/downloads/"
    Write-Host "  Linux (Ubuntu/Debian): sudo apt install python3 python3-pip"
    Write-Host "  Linux (Fedora/RHEL):   sudo dnf install python3 python3-pip"
    Write-Host "  Linux (Arch):          sudo pacman -S python python-pip"
    Write-Host "  Mac:                   brew install python3"
    Write-Host ""
    $installPython = Read-Host "Would you like to attempt automatic installation? (y/N)"
    
    if ($installPython -eq "y" -or $installPython -eq "Y") {
        Write-Host "Attempting to install Python..." -ForegroundColor Blue
        
        $installed = $false
        
        # Try winget first (most common on modern Windows)
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "Detected winget. Installing Python..."
            try {
                winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    $installed = $true
                    # Refresh PATH
                    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
                    $pythonCmd = "python"
                }
            } catch {
                Write-Host "Winget installation failed, trying other methods..." -ForegroundColor Yellow
            }
        }
        
        # Try Chocolatey
        if (-not $installed -and (Get-Command choco -ErrorAction SilentlyContinue)) {
            Write-Host "Detected Chocolatey. Installing Python..."
            try {
                choco install python3 -y 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    $installed = $true
                    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
                    $pythonCmd = "python"
                }
            } catch {
                Write-Host "Chocolatey installation failed." -ForegroundColor Yellow
            }
        }
        
        # Try scoop
        if (-not $installed -and (Get-Command scoop -ErrorAction SilentlyContinue)) {
            Write-Host "Detected Scoop. Installing Python..."
            try {
                scoop install python 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    $installed = $true
                    $pythonCmd = "python"
                }
            } catch {
                Write-Host "Scoop installation failed." -ForegroundColor Yellow
            }
        }
        
        if (-not $installed) {
            Write-Host "✗ Could not automatically install Python." -ForegroundColor Red
            Write-Host "Please install Python manually using one of the methods above."
            exit 1
        }
        
        # Verify installation
        Start-Sleep -Seconds 2  # Give PATH time to update
        if (-not (Get-Command $pythonCmd -ErrorAction SilentlyContinue)) {
            Write-Host "⚠ Python installed but not found in PATH." -ForegroundColor Yellow
            Write-Host "You may need to restart your terminal or add Python to PATH manually."
            Write-Host "Please restart your terminal and run this script again."
            exit 1
        }
        
        Write-Host "✓ Python installed successfully" -ForegroundColor Green
    } else {
        Write-Host "Please install Python manually and run this script again."
        exit 1
    }
}

$pythonVersion = & $pythonCmd --version
Write-Host "✓ Found Python: $pythonVersion" -ForegroundColor Green

# Check Python version
$versionOutput = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$requiredVersion = "3.8"

if ([version]$versionOutput -lt [version]$requiredVersion) {
    Write-Host "✗ Python 3.8 or higher is required. Found: $versionOutput" -ForegroundColor Red
    exit 1
}

# Check for pip
$pipCmd = $null
if (Get-Command pip -ErrorAction SilentlyContinue) {
    $pipCmd = "pip"
} elseif (Get-Command pip3 -ErrorAction SilentlyContinue) {
    $pipCmd = "pip3"
} else {
    Write-Host "⚠ pip not found. Attempting to install..." -ForegroundColor Yellow
    & $pythonCmd -m ensurepip --upgrade
    if (Get-Command pip -ErrorAction SilentlyContinue) {
        $pipCmd = "pip"
    } else {
        Write-Host "✗ Could not install pip. Please install pip manually." -ForegroundColor Red
        exit 1
    }
}

$pipVersion = & $pipCmd --version
Write-Host "✓ Found pip: $pipVersion" -ForegroundColor Green

# Create temporary directory
$tempDir = Join-Path $env:TEMP "blacksmith-install-$(New-Guid)"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    Write-Host ""
    Write-Host "Downloading Blacksmith..." -ForegroundColor Blue

    # Check for git
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Host "Cloning repository..."
        $repoUrl = $env:BLACKSMITH_REPO
        if (-not $repoUrl) {
            $repoUrl = "https://github.com/jimididit/blacksmith.git"
        }
        $branch = $env:BLACKSMITH_BRANCH
        if (-not $branch) {
            $branch = "main"
        }
        
        & git clone --depth 1 --branch $branch $repoUrl "$tempDir\blacksmith" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Git clone failed"
        }
    } else {
        Write-Host "⚠ Git not found. Attempting direct download..." -ForegroundColor Yellow
        $repoUrl = $env:BLACKSMITH_REPO
        if (-not $repoUrl) {
            $repoUrl = "https://github.com/jimididit/blacksmith"
        }
        $branch = $env:BLACKSMITH_BRANCH
        if (-not $branch) {
            $branch = "main"
        }
        
        $repoName = $repoUrl -replace ".*github.com/", "" -replace "\.git$", ""
        $downloadUrl = "https://github.com/$repoName/archive/refs/heads/$branch.zip"
        $zipFile = Join-Path $tempDir "blacksmith.zip"
        
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipFile
        Expand-Archive -Path $zipFile -DestinationPath $tempDir -Force
        Move-Item "$tempDir\blacksmith-$branch" "$tempDir\blacksmith" -Force
    }

    $installDir = Join-Path $tempDir "blacksmith"
    if (-not (Test-Path $installDir)) {
        throw "Installation directory not found"
    }

    Write-Host "✓ Downloaded Blacksmith" -ForegroundColor Green

    # Determine install method
    $installMethod = $env:BLACKSMITH_INSTALL_METHOD
    if (-not $installMethod) {
        $installMethod = "user"  # Default to user install on Windows
    }

    Write-Host ""
    Write-Host "Installing Blacksmith (method: $installMethod)..." -ForegroundColor Blue

    switch ($installMethod) {
        "user" {
            Write-Host "Installing for current user..."
            & $pipCmd install --upgrade pip
            & $pipCmd install --user -e $installDir
            Write-Host "✓ Blacksmith installed for current user" -ForegroundColor Green
        }
        "global" {
            Write-Host "Installing globally (may require admin privileges)..."
            & $pipCmd install --upgrade pip
            & $pipCmd install -e $installDir
            Write-Host "✓ Blacksmith installed globally" -ForegroundColor Green
        }
        default {
            Write-Host "✗ Unknown install method: $installMethod" -ForegroundColor Red
            Write-Host "Valid methods: global, user"
            exit 1
        }
    }

    # Verify installation
    Write-Host ""
    if (Get-Command blacksmith -ErrorAction SilentlyContinue) {
        Write-Host "✓ Blacksmith is now installed!" -ForegroundColor Green
        Write-Host ""
        Write-Host "You can now use Blacksmith:"
        Write-Host "  blacksmith              # Interactive menu"
        Write-Host "  blacksmith list         # List available sets"
        Write-Host "  blacksmith install <set>  # Install a set"
        Write-Host ""
        Write-Host "To uninstall, run:"
        Write-Host "  blacksmith uninstall"
    } else {
        Write-Host "⚠ Blacksmith installed but command not found in PATH" -ForegroundColor Yellow
        if ($installMethod -eq "user") {
            Write-Host "You may need to add %USERPROFILE%\AppData\Local\Programs\Python\Python*\Scripts to your PATH"
        }
    }
} finally {
    # Cleanup
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

