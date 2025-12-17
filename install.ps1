# Blacksmith Installation Script for Windows
# This script installs Blacksmith from a GitHub repository

$ErrorActionPreference = "Stop"

Write-Host "🔨 Blacksmith Installation Script" -ForegroundColor Blue
Write-Host ""

# Check if we're already in a virtual environment
$inVenv = $false
$systemPython = $null

# First, try to find any Python command
$tempPythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $tempPythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $tempPythonCmd = "python3"
}

if ($tempPythonCmd) {
    try {
        # Check if current Python is in a venv and get system Python path
        $venvCheckScript = @"
import sys
import os

in_venv = False
if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
    in_venv = True
elif hasattr(sys, 'real_prefix'):
    in_venv = True

if in_venv:
    print('IN_VENV')
    print(sys.executable)
    base_prefix = sys.base_prefix if hasattr(sys, 'base_prefix') else sys.prefix
    print(base_prefix)
    # Try to find system Python
    if os.name == 'nt':  # Windows
        system_python = os.path.join(base_prefix, 'python.exe')
        if os.path.exists(system_python):
            print(system_python)
        else:
            system_python = os.path.join(base_prefix, 'Scripts', 'python.exe')
            if os.path.exists(system_python):
                print(system_python)
            else:
                print('NOT_FOUND')
    else:  # Unix
        system_python = os.path.join(base_prefix, 'bin', 'python3')
        if os.path.exists(system_python):
            print(system_python)
        else:
            system_python = os.path.join(base_prefix, 'bin', 'python')
            if os.path.exists(system_python):
                print(system_python)
            else:
                print('NOT_FOUND')
else:
    print('NOT_IN_VENV')
"@
        $venvCheck = & $tempPythonCmd -c $venvCheckScript 2>&1
        if ($venvCheck -match "IN_VENV") {
            $inVenv = $true
            $lines = $venvCheck -split "`n" | Where-Object { $_.Trim() -ne "" }
            if ($lines.Count -ge 4) {
                $currentPython = $lines[1].Trim()
                $basePrefix = $lines[2].Trim()
                $foundSystemPython = $lines[3].Trim()
                if ($foundSystemPython -ne "NOT_FOUND" -and (Test-Path $foundSystemPython)) {
                    $systemPython = $foundSystemPython
                }
                Write-Host "⚠ Detected that you're already in a virtual environment" -ForegroundColor Yellow
                Write-Host "  Current venv Python: $currentPython" -ForegroundColor Gray
                if ($systemPython) {
                    Write-Host "  Will use system Python to create Blacksmith's venv: $systemPython" -ForegroundColor Gray
                } else {
                    Write-Host "  Warning: Could not locate system Python, will try to use base Python" -ForegroundColor Yellow
                }
            }
        }
    } catch {
        # Python check might fail, continue with normal detection
    }
}

# Check for Python
$pythonCmd = $null
if ($systemPython -and (Test-Path $systemPython)) {
    # Use system Python if we detected we're in a venv
    $pythonCmd = $systemPython
} elseif ($tempPythonCmd) {
    $pythonCmd = $tempPythonCmd
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

# Determine install method early (before pip check)
$installMethod = $env:BLACKSMITH_INSTALL_METHOD
if (-not $installMethod) {
    $installMethod = "venv"  # Default to venv install for better isolation
}

# Check for pip only if not using venv (venv includes pip automatically)
if ($installMethod -ne "venv") {
    Write-Host "Checking pip..." -ForegroundColor Blue
    try {
        $pipVersion = & $pythonCmd -m pip --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Found pip: $pipVersion" -ForegroundColor Green
        } else {
            Write-Host "⚠ pip not found. Attempting to install..." -ForegroundColor Yellow
            # Try ensurepip, but handle externally-managed-environment gracefully
            $ensurepipResult = & $pythonCmd -m ensurepip --upgrade 2>&1
            if ($LASTEXITCODE -ne 0 -and $ensurepipResult -match "externally-managed-environment") {
                Write-Host "✗ System Python is externally managed. Please use venv method instead:" -ForegroundColor Red
                Write-Host "  `$env:BLACKSMITH_INSTALL_METHOD='venv'; irm https://raw.githubusercontent.com/jimididit/blacksmith/main/install.ps1 | iex" -ForegroundColor Yellow
                exit 1
            }
            $pipVersion = & $pythonCmd -m pip --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Found pip: $pipVersion" -ForegroundColor Green
            } else {
                Write-Host "✗ Could not install pip. Please install pip manually or use venv method." -ForegroundColor Red
                exit 1
            }
        }
    } catch {
        Write-Host "✗ Error checking pip: $_" -ForegroundColor Red
        if ($_ -match "externally-managed-environment") {
            Write-Host "System Python is externally managed. Please use venv method instead:" -ForegroundColor Yellow
            Write-Host "  `$env:BLACKSMITH_INSTALL_METHOD='venv'; irm https://raw.githubusercontent.com/jimididit/blacksmith/main/install.ps1 | iex" -ForegroundColor Yellow
        } else {
            Write-Host "Attempting to install pip..." -ForegroundColor Yellow
            & $pythonCmd -m ensurepip --upgrade 2>&1 | Out-Null
            $pipVersion = & $pythonCmd -m pip --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Found pip: $pipVersion" -ForegroundColor Green
            } else {
                Write-Host "✗ Could not install pip. Please install pip manually or use venv method." -ForegroundColor Red
                exit 1
            }
        }
    }
} else {
    Write-Host "Using virtual environment method - pip check skipped (venv includes pip)" -ForegroundColor Blue
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

    # Install method already determined earlier (before pip check)

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
            Write-Host "Creating virtual environment at $venvPath..." -ForegroundColor Blue
            if ($inVenv) {
                Write-Host "  (Using system Python to avoid nested venv issues)" -ForegroundColor Gray
            }
            & $pythonCmd -m venv $venvPath
            if ($LASTEXITCODE -ne 0) {
                Write-Host "✗ Failed to create virtual environment" -ForegroundColor Red
                exit 1
            }
            
            # Wait a moment for venv to be fully created
            Start-Sleep -Seconds 1
            
            # Verify venv was created correctly
            $venvPython = Join-Path $venvPath "Scripts\python.exe"
            $venvPip = Join-Path $venvPath "Scripts\pip.exe"
            
            if (-not (Test-Path $venvPython)) {
                Write-Host "✗ Virtual environment Python executable not found at $venvPython" -ForegroundColor Red
                exit 1
            }
            
            if (-not (Test-Path $venvPip)) {
                Write-Host "✗ Virtual environment pip not found at $venvPip" -ForegroundColor Red
                exit 1
            }
            
            # Verify we're using the venv's Python
            $venvPythonVersion = & $venvPython --version 2>&1
            Write-Host "✓ Virtual environment created successfully" -ForegroundColor Green
            Write-Host "  Using Python: $venvPythonVersion" -ForegroundColor Gray
            
            # Verify venv is working by checking if it's actually a venv
            $venvCheck = & $venvPython -c "import sys; result = 'VENV_OK' if (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or hasattr(sys, 'real_prefix') else 'VENV_FAIL'; print(result)" 2>&1
            if ($venvCheck -ne "VENV_OK") {
                Write-Host "⚠ Warning: Virtual environment verification check failed - continuing anyway" -ForegroundColor Yellow
            } else {
                Write-Host "✓ Virtual environment verified" -ForegroundColor Green
            }
            
            # Install using venv's Python/pip
            Write-Host "Upgrading pip in virtual environment..." -ForegroundColor Blue
            & $venvPython -m pip install --upgrade pip --quiet
            if ($LASTEXITCODE -ne 0) {
                Write-Host "✗ Failed to upgrade pip in virtual environment" -ForegroundColor Red
                exit 1
            }
            
            Write-Host "Installing Blacksmith in virtual environment..." -ForegroundColor Blue
            & $venvPython -m pip install -e $installDir
            if ($LASTEXITCODE -ne 0) {
                Write-Host "✗ Failed to install Blacksmith in virtual environment" -ForegroundColor Red
                exit 1
            }
            
            # Verify installation by checking if blacksmith module can be imported
            Write-Host "Verifying installation..." -ForegroundColor Blue
            $verifyResult = & $venvPython -c "import blacksmith; print('INSTALL_OK')" 2>&1
            if ($verifyResult -ne "INSTALL_OK") {
                Write-Host "⚠ Warning: Could not verify Blacksmith installation: $verifyResult" -ForegroundColor Yellow
            } else {
                Write-Host "✓ Installation verified successfully" -ForegroundColor Green
            }
            
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

