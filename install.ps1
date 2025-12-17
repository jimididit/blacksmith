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

# Check for pip (use python -m pip to avoid launcher issues)
Write-Host "Checking pip..." -ForegroundColor Blue
try {
    $pipVersion = & $pythonCmd -m pip --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Found pip: $pipVersion" -ForegroundColor Green
    } else {
        Write-Host "⚠ pip not found. Attempting to install..." -ForegroundColor Yellow
        & $pythonCmd -m ensurepip --upgrade 2>&1 | Out-Null
        $pipVersion = & $pythonCmd -m pip --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Found pip: $pipVersion" -ForegroundColor Green
        } else {
            Write-Host "✗ Could not install pip. Please install pip manually." -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "✗ Error checking pip: $_" -ForegroundColor Red
    Write-Host "Attempting to install pip..." -ForegroundColor Yellow
    & $pythonCmd -m ensurepip --upgrade 2>&1 | Out-Null
    $pipVersion = & $pythonCmd -m pip --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Found pip: $pipVersion" -ForegroundColor Green
    } else {
        Write-Host "✗ Could not install pip. Please install pip manually." -ForegroundColor Red
        exit 1
    }
}

# Create temporary directory
$tempDir = Join-Path $env:TEMP "blacksmith-install-$(New-Guid)"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    Write-Host ""
    Write-Host "Downloading Blacksmith..." -ForegroundColor Blue

    $gitSuccess = $false
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
        
        # Suppress git progress output (it goes to stderr and confuses PowerShell)
        $null = & git clone --depth 1 --branch $branch --quiet $repoUrl "$tempDir\blacksmith" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $installDir = Join-Path $tempDir "blacksmith"
            if (Test-Path $installDir) {
                Write-Host "✓ Downloaded Blacksmith" -ForegroundColor Green
                $gitSuccess = $true
            }
        } else {
            Write-Host "⚠ Git clone failed, falling back to direct download..." -ForegroundColor Yellow
            # Fall through to direct download method
        }
    }
    
    # Fallback to direct download if git failed or not available
    if (-not $gitSuccess) {
        Write-Host "Downloading repository as ZIP..." -ForegroundColor Blue
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
        
        try {
            Invoke-WebRequest -Uri $downloadUrl -OutFile $zipFile -UseBasicParsing
            Expand-Archive -Path $zipFile -DestinationPath $tempDir -Force
            Move-Item "$tempDir\blacksmith-$branch" "$tempDir\blacksmith" -Force -ErrorAction Stop
            Write-Host "✓ Downloaded Blacksmith" -ForegroundColor Green
        } catch {
            Write-Host "✗ Failed to download Blacksmith: $_" -ForegroundColor Red
            throw "Download failed"
        }
    }

    $installDir = Join-Path $tempDir "blacksmith"
    if (-not (Test-Path $installDir)) {
        throw "Installation directory not found"
    }

    # Determine install method
    $installMethod = $env:BLACKSMITH_INSTALL_METHOD
    if (-not $installMethod) {
        $installMethod = "venv"  # Default to venv install for better isolation
    }

    Write-Host ""
    Write-Host "Installing Blacksmith (method: $installMethod)..." -ForegroundColor Blue

    switch ($installMethod) {
        "venv" {
            Write-Host "Creating virtual environment..."
            $venvPath = Join-Path $env:USERPROFILE ".blacksmith-venv"
            
            # Check if venv already exists
            if (Test-Path $venvPath) {
                Write-Host "Virtual environment already exists at $venvPath" -ForegroundColor Yellow
                Write-Host "Removing old virtual environment..." -ForegroundColor Yellow
                Remove-Item -Path $venvPath -Recurse -Force
            }
            
            # Create venv
            & $pythonCmd -m venv $venvPath
            if ($LASTEXITCODE -ne 0) {
                Write-Host "✗ Failed to create virtual environment" -ForegroundColor Red
                exit 1
            }
            
            # Activate venv and install
            $venvPython = Join-Path $venvPath "Scripts\python.exe"
            $venvPip = Join-Path $venvPath "Scripts\pip.exe"
            
            & $venvPython -m pip install --upgrade pip
            & $venvPython -m pip install -e $installDir
            
            Write-Host "✓ Blacksmith installed in virtual environment" -ForegroundColor Green
            Write-Host ""
            Write-Host "To use Blacksmith, activate the virtual environment:" -ForegroundColor Yellow
            Write-Host "  $venvPath\Scripts\Activate.ps1" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Or create an alias in your PowerShell profile:" -ForegroundColor Yellow
            Write-Host "  Set-Alias blacksmith `"$venvPath\Scripts\blacksmith.exe`"" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "To activate automatically, add this to your PowerShell profile:" -ForegroundColor Yellow
            Write-Host "  `$env:BLACKSMITH_VENV = `"$venvPath`"" -ForegroundColor Cyan
            Write-Host "  if (Test-Path `"`$env:BLACKSMITH_VENV\Scripts\Activate.ps1`") { & `"`$env:BLACKSMITH_VENV\Scripts\Activate.ps1`" }" -ForegroundColor Cyan
        }
        "user" {
            Write-Host "Installing for current user..."
            & $pythonCmd -m pip install --upgrade pip
            & $pythonCmd -m pip install --user -e $installDir
            Write-Host "✓ Blacksmith installed for current user" -ForegroundColor Green
        }
        "global" {
            Write-Host "Installing globally (may require admin privileges)..."
            & $pythonCmd -m pip install --upgrade pip
            & $pythonCmd -m pip install -e $installDir
            Write-Host "✓ Blacksmith installed globally" -ForegroundColor Green
        }
        default {
            Write-Host "✗ Unknown install method: $installMethod" -ForegroundColor Red
            Write-Host "Valid methods: venv, global, user"
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

